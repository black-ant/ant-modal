"""
批量图像生成工具
支持并行处理多个提示词，提高效率
参考 Modal 的 map/starmap 并行处理模式
"""

import modal
import json
from pathlib import Path
from config import *
from model_download import download_all_models
from api_service import start_comfy_background, handle_api_request

# 构建镜像（与主应用相同）
image = build_base_image()
image = install_custom_nodes(image)

hf_secret = get_hf_secret()
vol = get_volume()

image = (
    image.pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_all_models,
        volumes={"/cache": vol},
        secrets=[hf_secret]
    )
    .add_local_file(
        Path(__file__).parent / "workflow_api.json",
        "/root/workflow_api.json"
    )
)

app = modal.App("comfyui-batch-processor", image=image)


@app.cls(
    gpu=GPU_TYPE,
    volumes={"/cache": vol},
    timeout=3600,  # 1小时超时
    container_idle_timeout=600  # 容器空闲10分钟后回收
)
class BatchImageGenerator:
    """批量图像生成器类"""
    
    @modal.enter()
    def startup(self):
        """容器启动时初始化"""
        print("🚀 启动批量图像生成器...")
        start_comfy_background(API_PORT)
        print("✅ ComfyUI 后台服务已就绪")
    
    @modal.method()
    def generate_single(
        self, 
        prompt: str, 
        workflow_path: str = "/root/workflow_api.json",
        **kwargs
    ) -> bytes:
        """
        生成单张图片
        
        Args:
            prompt: 提示词
            workflow_path: 工作流模板路径
            **kwargs: 其他参数（width, height, steps等）
        
        Returns:
            bytes: 图片字节数据
        """
        print(f"📸 生成图片: {prompt[:50]}...")
        
        # 处理自定义参数
        workflow_data = json.loads(Path(workflow_path).read_text())
        
        # 应用自定义参数
        if 'width' in kwargs or 'height' in kwargs:
            width = kwargs.get('width', 832)
            height = kwargs.get('height', 1216)
            workflow_data["27"]["inputs"]["width"] = width
            workflow_data["27"]["inputs"]["height"] = height
        
        if 'steps' in kwargs:
            workflow_data["31"]["inputs"]["steps"] = kwargs['steps']
        
        if 'cfg' in kwargs:
            workflow_data["31"]["inputs"]["cfg"] = kwargs['cfg']
        
        # 生成图片
        img_bytes = handle_api_request(prompt, Path(workflow_path))
        
        return img_bytes
    
    @modal.method()
    def generate_batch(
        self, 
        prompts: list[str],
        workflow_path: str = "/root/workflow_api.json",
        **kwargs
    ) -> list[dict]:
        """
        批量生成图片（单个容器内串行处理）
        
        Args:
            prompts: 提示词列表
            workflow_path: 工作流模板路径
            **kwargs: 其他参数
        
        Returns:
            list[dict]: 结果列表
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                print(f"\n[{i+1}/{len(prompts)}] 处理: {prompt[:50]}...")
                img_bytes = self.generate_single.local(prompt, workflow_path, **kwargs)
                
                results.append({
                    "success": True,
                    "prompt": prompt,
                    "image_size": len(img_bytes),
                    "index": i
                })
                
                print(f"✅ 完成 [{i+1}/{len(prompts)}]")
                
            except Exception as e:
                print(f"❌ 失败 [{i+1}/{len(prompts)}]: {e}")
                results.append({
                    "success": False,
                    "prompt": prompt,
                    "error": str(e),
                    "index": i
                })
        
        return results


@app.function(
    gpu=GPU_TYPE,
    volumes={"/cache": vol},
    timeout=1800
)
def generate_image_parallel(
    prompt: str,
    width: int = 832,
    height: int = 1216,
    steps: int = 20,
    cfg: float = 1.0
) -> dict:
    """
    并行图像生成函数（用于 map）
    
    Args:
        prompt: 提示词
        width: 图片宽度
        height: 图片高度
        steps: 采样步数
        cfg: CFG 强度
    
    Returns:
        dict: 生成结果
    """
    try:
        # 启动 ComfyUI
        start_comfy_background(API_PORT)
        
        # 准备工作流
        workflow_data = json.loads(Path("/root/workflow_api.json").read_text())
        workflow_data["27"]["inputs"]["width"] = width
        workflow_data["27"]["inputs"]["height"] = height
        workflow_data["31"]["inputs"]["steps"] = steps
        workflow_data["31"]["inputs"]["cfg"] = cfg
        
        # 生成图片
        img_bytes = handle_api_request(prompt, Path("/root/workflow_api.json"))
        
        return {
            "success": True,
            "prompt": prompt,
            "image_size": len(img_bytes),
            "parameters": {
                "width": width,
                "height": height,
                "steps": steps,
                "cfg": cfg
            }
        }
    except Exception as e:
        return {
            "success": False,
            "prompt": prompt,
            "error": str(e)
        }


@app.local_entrypoint()
def main(
    prompts_file: str = "",
    prompt: str = "",
    parallel: bool = False,
    width: int = 832,
    height: int = 1216,
    steps: int = 20,
    cfg: float = 1.0
):
    """
    批量生成图片入口
    
    使用示例:
    # 单个提示词
    modal run batch_inference.py --prompt "A beautiful landscape"
    
    # 从文件读取多个提示词（每行一个）
    modal run batch_inference.py --prompts-file prompts.txt
    
    # 并行模式（每个提示词独立容器）
    modal run batch_inference.py --prompts-file prompts.txt --parallel
    
    # 自定义参数
    modal run batch_inference.py --prompt "A cat" --width 1024 --height 1024 --steps 30
    """
    
    # 准备提示词列表
    prompts = []
    if prompts_file:
        with open(prompts_file, 'r', encoding='utf-8') as f:
            prompts = [line.strip() for line in f if line.strip()]
        print(f"📋 从文件读取 {len(prompts)} 个提示词")
    elif prompt:
        prompts = [prompt]
    else:
        print("❌ 错误: 需要提供 --prompt 或 --prompts-file 参数")
        return
    
    print(f"\n{'='*60}")
    print(f"批量图像生成")
    print(f"模式: {'并行' if parallel else '串行'}")
    print(f"提示词数量: {len(prompts)}")
    print(f"参数: {width}x{height}, steps={steps}, cfg={cfg}")
    print(f"{'='*60}\n")
    
    if parallel:
        # 并行模式 - 使用 map，每个提示词独立容器
        print("🚀 使用并行模式（每个提示词独立容器）")
        
        # 构造参数元组
        tasks = [
            (p, width, height, steps, cfg) 
            for p in prompts
        ]
        
        # 并行执行
        results = list(generate_image_parallel.starmap(tasks))
        
    else:
        # 串行模式 - 单容器处理所有提示词
        print("🚀 使用串行模式（单容器处理所有）")
        
        generator = BatchImageGenerator()
        results = generator.generate_batch.remote(
            prompts,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg
        )
    
    # 统计结果
    successful = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])
    
    print(f"\n{'='*60}")
    print(f"批量生成完成")
    print(f"{'='*60}")
    print(f"✅ 成功: {successful}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {len(results)}")
    
    # 显示失败的任务
    if failed > 0:
        print(f"\n失败的任务:")
        for r in results:
            if not r['success']:
                print(f"  - {r['prompt'][:50]}: {r['error']}")
    
    # 保存结果摘要
    summary = {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "mode": "parallel" if parallel else "serial",
        "parameters": {
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg
        },
        "results": results
    }
    
    with open("batch_results.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 结果已保存到 batch_results.json")
