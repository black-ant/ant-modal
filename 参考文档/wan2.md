我来帮你搜索在 Modal 上部署视频生成工具的完整方案。
根据搜索结果，我为你整理一个在 Modal 上部署视频生成工具的完整方案。以下是基于官方示例和最佳实践的完整实现：

完整视频生成方案
方案一：基于 Wan2.1 的文生视频（推荐）
这是 Modal 官方推荐的文生视频方案，使用阿里巴巴的 Wan2.1 模型。
文件结构：
video-generator/
├── video_gen.py          # 主要的 Modal 应用
├── deploy.py             # 部署脚本
└── requirements.txt      # 本地依赖

video_gen.py - 主应用文件：
pythonDownloadCopy codeimport modal

# 定义 Modal 应用
app = modal.App("video-generator")

# 构建容器镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch>=2.0.0",
        "torchvision",
        "diffusers>=0.32.0",
        "transformers>=4.49.0",
        "accelerate",
        "sentencepiece",
        "imageio[ffmpeg]",
        "imageio-ffmpeg",
        "huggingface_hub",
    )
)

# 模型存储卷
volume = modal.Volume.from_name("video-models", create_if_missing=True)
MODEL_DIR = "/models"

# 模型下载函数
@app.function(
    image=image,
    volumes={MODEL_DIR: volume},
    timeout=3600,
)
def download_models():
    """下载模型到持久化存储"""
    from huggingface_hub import snapshot_download
    import os
    
    model_path = os.path.join(MODEL_DIR, "Wan2.1-T2V-1.3B")
    
    if not os.path.exists(model_path):
        print("正在下载 Wan2.1-T2V-1.3B 模型...")
        snapshot_download(
            repo_id="Wan-AI/Wan2.1-T2V-1.3B",
            local_dir=model_path,
            local_dir_use_symlinks=False,
        )
        volume.commit()
        print("模型下载完成！")
    else:
        print("模型已存在，跳过下载。")
    
    return model_path


# 视频生成类
@app.cls(
    image=image,
    gpu="A100",  # 或 "A10G", "H100"
    volumes={MODEL_DIR: volume},
    timeout=1800,
    container_idle_timeout=300,
)
class VideoGenerator:
    @modal.enter()
    def load_model(self):
        """容器启动时加载模型"""
        import torch
        from diffusers import AutoencoderKLWan, WanPipeline
        from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler
        import os
        
        model_path = os.path.join(MODEL_DIR, "Wan2.1-T2V-1.3B")
        
        print("正在加载 VAE...")
        vae = AutoencoderKLWan.from_pretrained(
            model_path,
            subfolder="vae",
            torch_dtype=torch.float32,
        )
        
        print("正在加载管道...")
        self.pipe = WanPipeline.from_pretrained(
            model_path,
            vae=vae,
            torch_dtype=torch.bfloat16,
        )
        
        self.pipe.scheduler = UniPCMultistepScheduler.from_config(
            self.pipe.scheduler.config,
            flow_shift=5.0,
        )
        
        self.pipe.to("cuda")
        print("模型加载完成！")

    @modal.method()
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 33,
        height: int = 480,
        width: int = 832,
        num_inference_steps: int = 30,
        guidance_scale: float = 5.0,
        seed: int = -1,
    ) -> bytes:
        """生成视频"""
        import torch
        import imageio
        import io
        
        if seed == -1:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        
        generator = torch.Generator(device="cuda").manual_seed(seed)
        
        print(f"正在生成视频: {prompt}")
        print(f"参数: frames={num_frames}, size={width}x{height}, steps={num_inference_steps}")
        
        output = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=height,
            width=width,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )
        
        frames = output.frames[0]
        
        # 导出为 MP4
        buffer = io.BytesIO()
        imageio.mimwrite(buffer, frames, format="mp4", fps=16, codec="libx264")
        buffer.seek(0)
        
        print(f"视频生成完成！Seed: {seed}")
        return buffer.read()

    @modal.method()
    def generate_with_options(
        self,
        prompt: str,
        options: dict = None,
    ) -> dict:
        """带选项的视频生成，返回更多信息"""
        import base64
        import torch
        
        options = options or {}
        
        video_bytes = self.generate(
            prompt=prompt,
            negative_prompt=options.get("negative_prompt", ""),
            num_frames=options.get("num_frames", 33),
            height=options.get("height", 480),
            width=options.get("width", 832),
            num_inference_steps=options.get("num_inference_steps", 30),
            guidance_scale=options.get("guidance_scale", 5.0),
            seed=options.get("seed", -1),
        )
        
        return {
            "video_base64": base64.b64encode(video_bytes).decode(),
            "prompt": prompt,
            "options": options,
        }


# Web API 端点
@app.function(
    image=image,
    timeout=1800,
)
@modal.web_endpoint(method="POST")
def generate_video_api(request: dict):
    """HTTP API 端点"""
    import base64
    
    prompt = request.get("prompt", "A cat walking in the garden")
    options = request.get("options", {})
    
    generator = VideoGenerator()
    video_bytes = generator.generate.remote(
        prompt=prompt,
        negative_prompt=options.get("negative_prompt", ""),
        num_frames=options.get("num_frames", 33),
        height=options.get("height", 480),
        width=options.get("width", 832),
        num_inference_steps=options.get("num_inference_steps", 30),
        guidance_scale=options.get("guidance_scale", 5.0),
        seed=options.get("seed", -1),
    )
    
    return {
        "status": "success",
        "video_base64": base64.b64encode(video_bytes).decode(),
        "prompt": prompt,
    }


# 本地入口
@app.local_entrypoint()
def main(
    prompt: str = "A golden retriever playing in the snow, cinematic lighting",
    output: str = "output.mp4",
):
    """本地调用入口"""
    print("确保模型已下载...")
    download_models.remote()
    
    print(f"生成视频: {prompt}")
    generator = VideoGenerator()
    video_bytes = generator.generate.remote(prompt=prompt)
    
    with open(output, "wb") as f:
        f.write(video_bytes)
    
    print(f"视频已保存到: {output}")

方案二：基于 CogVideoX 的视频生成
cogvideo_gen.py：
pythonDownloadCopy codeimport modal

app = modal.App("cogvideo-generator")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "torch>=2.0.0",
        "diffusers>=0.30.0",
        "transformers>=4.44.0",
        "accelerate",
        "sentencepiece",
        "imageio[ffmpeg]",
        "imageio-ffmpeg",
    )
)

volume = modal.Volume.from_name("cogvideo-models", create_if_missing=True)
MODEL_DIR = "/models"


@app.cls(
    image=image,
    gpu="A100",
    volumes={MODEL_DIR: volume},
    timeout=1800,
    container_idle_timeout=300,
)
class CogVideoGenerator:
    model_id: str = "THUDM/CogVideoX-2b"
    
    @modal.enter()
    def load_model(self):
        import torch
        from diffusers import CogVideoXPipeline
        
        print(f"加载模型: {self.model_id}")
        self.pipe = CogVideoXPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
            cache_dir=MODEL_DIR,
        )
        self.pipe.to("cuda")
        self.pipe.enable_model_cpu_offload()
        self.pipe.vae.enable_tiling()
        print("模型加载完成！")

    @modal.method()
    def generate(
        self,
        prompt: str,
        num_frames: int = 49,
        num_inference_steps: int = 50,
        guidance_scale: float = 6.0,
        seed: int = -1,
    ) -> bytes:
        import torch
        import imageio
        import io
        
        if seed == -1:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        
        generator = torch.Generator(device="cuda").manual_seed(seed)
        
        print(f"生成视频: {prompt}")
        
        video_frames = self.pipe(
            prompt=prompt,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        ).frames[0]
        
        buffer = io.BytesIO()
        imageio.mimwrite(buffer, video_frames, format="mp4", fps=8, codec="libx264")
        buffer.seek(0)
        
        return buffer.read()


@app.local_entrypoint()
def main(prompt: str = "A cute puppy playing with a ball"):
    generator = CogVideoGenerator()
    video_bytes = generator.generate.remote(prompt=prompt)
    
    with open("cogvideo_output.mp4", "wb") as f:
        f.write(video_bytes)
    
    print("视频已保存到 cogvideo_output.mp4")

部署和使用脚本
deploy.py - 部署脚本：
pythonDownloadCopy code#!/usr/bin/env python3
"""
Modal 视频生成工具部署脚本
使用方法:
    python deploy.py setup      # 首次设置（下载模型）
    python deploy.py deploy     # 部署服务
    python deploy.py generate   # 生成测试视频
    python deploy.py serve      # 启动本地开发服务器
"""

import subprocess
import sys
import argparse


def run_command(cmd: list[str]):
    """运行命令并打印输出"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def setup():
    """首次设置 - 下载模型"""
    print("=" * 50)
    print("步骤 1: 检查 Modal 配置")
    print("=" * 50)
    
    # 检查 Modal 是否已配置
    result = run_command(["modal", "token", "show"])
    if result != 0:
        print("\n请先运行 'modal token new' 配置您的 Modal 账户")
        return
    
    print("\n" + "=" * 50)
    print("步骤 2: 下载模型")
    print("=" * 50)
    run_command(["modal", "run", "video_gen.py::download_models"])
    
    print("\n设置完成！现在可以运行 'python deploy.py generate' 生成视频")


def deploy():
    """部署服务到 Modal"""
    print("部署视频生成服务...")
    run_command(["modal", "deploy", "video_gen.py"])
    print("\n部署完成！")
    print("Web API 端点已创建，可以通过 HTTP POST 请求调用")


def generate(prompt: str = None, output: str = "output.mp4"):
    """生成视频"""
    prompt = prompt or "A golden retriever playing in the snow, cinematic lighting, 4K"
    print(f"生成视频: {prompt}")
    run_command([
        "modal", "run", "video_gen.py",
        "--prompt", prompt,
        "--output", output,
    ])


def serve():
    """启动本地开发服务器"""
    print("启动本地开发服务器...")
    run_command(["modal", "serve", "video_gen.py"])


def main():
    parser = argparse.ArgumentParser(description="Modal 视频生成工具")
    parser.add_argument(
        "command",
        choices=["setup", "deploy", "generate", "serve"],
        help="要执行的命令",
    )
    parser.add_argument("--prompt", type=str, help="视频生成提示词")
    parser.add_argument("--output", type=str, default="output.mp4", help="输出文件名")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup()
    elif args.command == "deploy":
        deploy()
    elif args.command == "generate":
        generate(args.prompt, args.output)
    elif args.command == "serve":
        serve()


if __name__ == "__main__":
    main()

客户端调用脚本
client.py - Python 客户端：
pythonDownloadCopy code#!/usr/bin/env python3
"""
视频生成客户端
支持本地调用和 HTTP API 调用两种方式
"""

import modal
import requests
import base64
import argparse
from pathlib import Path


class VideoGeneratorClient:
    """视频生成客户端"""
    
    def __init__(self, api_url: str = None):
        """
        初始化客户端
        
        Args:
            api_url: HTTP API URL，如果为 None 则使用 Modal 直接调用
        """
        self.api_url = api_url
    
    def generate_via_modal(
        self,
        prompt: str,
        output_path: str = "output.mp4",
        **options,
    ) -> str:
        """通过 Modal 直接调用生成视频"""
        # 动态导入 Modal 应用
        video_gen = modal.Function.lookup("video-generator", "VideoGenerator.generate")
        
        print(f"生成视频: {prompt}")
        video_bytes = video_gen.remote(
            prompt=prompt,
            negative_prompt=options.get("negative_prompt", ""),
            num_frames=options.get("num_frames", 33),
            height=options.get("height", 480),
            width=options.get("width", 832),
            num_inference_steps=options.get("num_inference_steps", 30),
            guidance_scale=options.get("guidance_scale", 5.0),
            seed=options.get("seed", -1),
        )
        
        with open(output_path, "wb") as f:
            f.write(video_bytes)
        
        print(f"视频已保存到: {output_path}")
        return output_path
    
    def generate_via_api(
        self,
        prompt: str,
        output_path: str = "output.mp4",
        **options,
    ) -> str:
        """通过 HTTP API 调用生成视频"""
        if not self.api_url:
            raise ValueError("需要提供 API URL")
        
        payload = {
            "prompt": prompt,
            "options": options,
        }
        
        print(f"调用 API: {self.api_url}")
        print(f"生成视频: {prompt}")
        
        response = requests.post(self.api_url, json=payload, timeout=600)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("status") == "success":
            video_bytes = base64.b64decode(result["video_base64"])
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print(f"视频已保存到: {output_path}")
            return output_path
        else:
            raise Exception(f"生成失败: {result}")
    
    def generate(
        self,
        prompt: str,
        output_path: str = "output.mp4",
        **options,
    ) -> str:
        """生成视频（自动选择调用方式）"""
        if self.api_url:
            return self.generate_via_api(prompt, output_path, **options)
        else:
            return self.generate_via_modal(prompt, output_path, **options)


def batch_generate(prompts: list[str], output_dir: str = "outputs"):
    """批量生成视频"""
    Path(output_dir).mkdir(exist_ok=True)
    client = VideoGeneratorClient()
    
    results = []
    for i, prompt in enumerate(prompts):
        output_path = f"{output_dir}/video_{i:03d}.mp4"
        try:
            client.generate(prompt, output_path)
            results.append({"prompt": prompt, "output": output_path, "status": "success"})
        except Exception as e:
            results.append({"prompt": prompt, "error": str(e), "status": "failed"})
    
    return results


def main():
    parser = argparse.ArgumentParser(description="视频生成客户端")
    parser.add_argument("prompt", type=str, help="视频生成提示词")
    parser.add_argument("--output", "-o", type=str, default="output.mp4", help="输出文件路径")
    parser.add_argument("--api-url", type=str, help="HTTP API URL（可选）")
    parser.add_argument("--num-frames", type=int, default=33, help="帧数")
    parser.add_argument("--width", type=int, default=832, help="宽度")
    parser.add_argument("--height", type=int, default=480, help="高度")
    parser.add_argument("--steps", type=int, default=30, help="推理步数")
    parser.add_argument("--guidance", type=float, default=5.0, help="引导系数")
    parser.add_argument("--seed", type=int, default=-1, help="随机种子")
    
    args = parser.parse_args()
    
    client = VideoGeneratorClient(api_url=args.api_url)
    
    client.generate(
        prompt=args.prompt,
        output_path=args.output,
        num_frames=args.num_frames,
        width=args.width,
        height=args.height,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

本地依赖文件
requirements.txt：
modal>=0.64.0
requests>=2.28.0


使用流程
1. 环境准备
bashDownloadCopy code# 安装依赖
pip install modal requests

# 配置 Modal（首次使用）
modal token new
2. 首次设置
bashDownloadCopy code# 下载模型到 Modal 存储
python deploy.py setup
3. 生成视频
bashDownloadCopy code# 方式 1: 使用部署脚本
python deploy.py generate --prompt "A cat walking in the garden, 4K, cinematic"

# 方式 2: 直接使用 Modal CLI
modal run video_gen.py --prompt "A beautiful sunset over the ocean"

# 方式 3: 使用客户端脚本
python client.py "A robot dancing in a futuristic city" --output robot.mp4
4. 部署为服务
bashDownloadCopy code# 部署到 Modal（获得 HTTP API 端点）
python deploy.py deploy

# 或者启动本地开发服务器
python deploy.py serve
5. 通过 API 调用
pythonDownloadCopy codeimport requests
import base64

# 部署后获得的 API URL
api_url = "https://your-username--video-generator-generate-video-api.modal.run"

response = requests.post(api_url, json={
    "prompt": "A dragon flying over mountains",
    "options": {
        "num_frames": 33,
        "width": 832,
        "height": 480,
    }
})

result = response.json()
video_bytes = base64.b64decode(result["video_base64"])

with open("dragon.mp4", "wb") as f:
    f.write(video_bytes)

费用估算
GPU 类型每小时费用单个视频生成时间单个视频成本A10G~$1.10/hr~2-3 分钟~$0.05A100 40GB~$3.00/hr~1-2 分钟~$0.08H100~$4.50/hr~30-60 秒~$0.06

如需更多帮助或有其他定制需求，请告诉我！