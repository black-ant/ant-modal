"""
=============================================================================
ComfyUI 完整应用服务
=============================================================================
S1: 环境准备 - 构建基础镜像，安装 ComfyUI 和依赖
S2: Custom Nodes - 安装自定义节点扩展
S3: 模型下载 - 从 HuggingFace 和 URL 下载模型
S4: 服务配置 - 创建 Modal 应用和存储卷
S5: UI 服务 - 提供 Web 界面
S6: API 服务 - 提供 REST API 接口
=============================================================================
部署命令: modal deploy comfyui_app.py
=============================================================================
"""
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Dict

import modal

# =============================================================================
# S1: 环境准备阶段
# =============================================================================

# S1.1: 构建基础 Docker 镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl")
    .pip_install("fastapi[standard]==0.115.4")
    .pip_install("comfy-cli==1.5.1")
    .pip_install("requests==2.32.3")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4")
    # S1.2: 安装 ComfyUI
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
)

# =============================================================================
# S2: Custom Nodes 安装阶段
# =============================================================================

# S2.1: 使用 comfy node install 安装常用节点
image = image.run_commands(
    # ComfyUI Manager - 节点管理器
    "comfy node install --fast-deps was-node-suite-comfyui@1.0.2",
)

# S2.2: 通过 git clone 安装特殊节点
# 取消注释以安装更多节点
# image = image.run_commands(
#     "git clone https://github.com/ltdrdata/ComfyUI-Manager.git /root/comfy/ComfyUI/custom_nodes/ComfyUI-Manager",
#     "git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git /root/comfy/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus",
# )

# =============================================================================
# S3: 模型下载阶段
# =============================================================================

# S3.1: 配置 HuggingFace Secret (可选)
# 如果需要下载私有模型，请先创建 Secret:
# modal secret create huggingface-secret HF_TOKEN=hf_xxxxx
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None


def download_models():
    """
    S3: 下载所需的 AI 模型文件
    - 从 HuggingFace 下载基础模型
    - 从 URL 下载额外模型
    """
    from huggingface_hub import hf_hub_download
    
    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 S3.0: HuggingFace Token 状态: {'已配置' if hf_token else '未配置'}")
    
    # S3.1: 下载 Flux 基础模型
    print("📥 S3.1: 下载 Flux 基础模型...")
    try:
        flux_model = hf_hub_download(
            repo_id="Comfy-Org/flux1-dev",
            filename="flux1-dev-fp8.safetensors",
            cache_dir="/cache",
        )
        subprocess.run(
            f"ln -s {flux_model} /root/comfy/ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors",
            shell=True,
            check=True,
        )
        print("✅ Flux 模型下载成功")
    except Exception as e:
        print(f"⚠️ Flux 模型下载失败: {e}")
    
    # S3.2: 下载 Clip 模型
    print("📥 S3.2: 下载 Clip 模型...")
    clip_models = [
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/clip_g.safetensors",
            "local_name": "clip_g.safetensors"
        },
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/clip_l.safetensors",
            "local_name": "clip_l.safetensors"
        },
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/t5xxl_fp8_e4m3fn.safetensors",
            "local_name": "t5xxl_fp8_e4m3fn.safetensors"
        }
    ]
    
    clip_dir = "/root/comfy/ComfyUI/models/clip"
    os.makedirs(clip_dir, exist_ok=True)
    
    for clip_model in clip_models:
        try:
            print(f"  📦 下载: {clip_model['filename']}")
            clip_path = hf_hub_download(
                repo_id=clip_model["repo_id"],
                filename=clip_model["filename"],
                cache_dir="/cache",
                token=hf_token
            )
            subprocess.run(
                f"ln -s {clip_path} {clip_dir}/{clip_model['local_name']}",
                shell=True,
                check=True
            )
        except Exception as e:
            print(f"  ⚠️ 下载失败: {e}")
    
    # S3.3: 下载 VAE 模型
    print("📥 S3.3: 下载 VAE 模型...")
    try:
        vae_model = hf_hub_download(
            repo_id="black-forest-labs/FLUX.1-dev",
            filename="ae.safetensors",
            cache_dir="/cache",
            token=hf_token
        )
        subprocess.run(
            f"ln -s {vae_model} /root/comfy/ComfyUI/models/vae/ae.safetensors",
            shell=True,
            check=True,
        )
        print("✅ VAE 模型下载成功")
    except Exception as e:
        print(f"⚠️ VAE 模型下载失败: {e}")
    
    # S3.4: 下载 LoRA 模型
    print("📥 S3.4: 下载 LoRA 模型...")
    lora_models = [
        {
            "repo_id": "UmeAiRT/FLUX.1-dev-LoRA-Ume_Sky",
            "filename": "ume_sky_v2.safetensors",
            "local_name": "ume_sky_v2.safetensors"
        },
        {
            "repo_id": "Shakker-Labs/FLUX.1-dev-LoRA-Dark-Fantasy",
            "filename": "FLUX.1-dev-lora-Dark-Fantasy.safetensors",
            "local_name": "FLUX.1-dev-lora-Dark-Fantasy.safetensors"
        },
    ]
    
    lora_dir = "/root/comfy/ComfyUI/models/loras"
    os.makedirs(lora_dir, exist_ok=True)
    
    for lora in lora_models:
        try:
            print(f"  📦 下载 LoRA: {lora['repo_id']}")
            lora_path = hf_hub_download(
                repo_id=lora["repo_id"],
                filename=lora["filename"],
                cache_dir="/cache",
            )
            subprocess.run(
                f"ln -s {lora_path} {lora_dir}/{lora['local_name']}",
                shell=True,
                check=True
            )
        except Exception as e:
            print(f"  ⚠️ LoRA 下载失败: {e}")


# =============================================================================
# S4: 服务配置阶段
# =============================================================================

print("🔧 S4: 配置 Modal 服务...")

# S4.1: 创建持久化存储卷
vol = modal.Volume.from_name("comfyui-cache", create_if_missing=True)

# S4.2: 完成镜像构建，执行模型下载
image = (
    image
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_models,
        volumes={"/cache": vol},
        secrets=[hf_secret] if hf_secret else []
    )
)

# S4.3: 创建 Modal 应用实例
app = modal.App(name="comfyui-app", image=image)


# =============================================================================
# S5: UI 服务阶段
# =============================================================================

@app.function(
    max_containers=1,
    gpu="L40S",
    volumes={"/cache": vol},
    timeout=86400
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """
    S5: 提供 ComfyUI 交互式 Web 界面服务
    - 启动 ComfyUI Web 服务器
    - 监听 0.0.0.0:8000 端口
    - 支持最多 10 个并发用户
    """
    print("🌐 S5: 启动 ComfyUI 交互式 Web 界面...")
    
    # 链接 Volume 中的所有资源（模型和节点）
    _link_resources_from_volume()
    
    subprocess.Popen(
        "comfy launch -- --listen 0.0.0.0 --port 8000",
        shell=True
    )


# =============================================================================
# S6: API 服务阶段
# =============================================================================

@app.cls(
    scaledown_window=300,
    gpu="L40S",
    volumes={"/cache": vol}
)
@modal.concurrent(max_inputs=5)
class ComfyUI:
    """
    S6: ComfyUI API 服务类
    提供图像生成的 RESTful API 接口
    """
    port: int = 8000
    
    @modal.enter()
    def launch_comfy_background(self):
        """S6.1: 容器启动时初始化 ComfyUI 后台服务"""
        print(f"🚀 S6.1: 启动 ComfyUI 后台服务，端口: {self.port}")
        
        # 链接 Volume 中的所有资源（模型和节点）
        _link_resources_from_volume()
        
        cmd = f"comfy launch --background -- --port {self.port}"
        subprocess.run(cmd, shell=True, check=True)
    
    @modal.method()
    def infer(self, workflow_path: str = "/root/workflow_api.json"):
        """S6.2: 执行图像生成推理"""
        print("🎨 S6.2: 开始执行图像生成推理...")
        
        # 检查服务健康状态
        self.poll_server_health()
        
        # 执行工作流
        cmd = f"comfy run --workflow {workflow_path} --wait --timeout 1200 --verbose"
        subprocess.run(cmd, shell=True, check=True)
        
        # 获取生成的图像
        output_dir = "/root/comfy/ComfyUI/output"
        workflow = json.loads(Path(workflow_path).read_text())
        file_prefix = [
            node.get("inputs")
            for node in workflow.values()
            if node.get("class_type") == "SaveImage"
        ][0]["filename_prefix"]
        
        for f in Path(output_dir).iterdir():
            if f.name.startswith(file_prefix):
                return f.read_bytes()
    
    @modal.fastapi_endpoint(method="POST")
    def api(self, item: Dict):
        """S6.3: FastAPI 端点 - 处理图像生成请求"""
        from fastapi import Response
        
        print("📡 S6.3: 处理 API 请求...")
        
        # 加载工作流模板（需要先上传 workflow_api.json）
        workflow_path = Path("/root/workflow_api.json")
        if not workflow_path.exists():
            return {"error": "workflow_api.json 不存在，请先上传工作流文件"}
        
        workflow_data = json.loads(workflow_path.read_text())
        
        # 设置用户提示词
        workflow_data["6"]["inputs"]["text"] = item.get("prompt", "a beautiful landscape")
        
        # 生成唯一 ID
        client_id = uuid.uuid4().hex
        workflow_data["9"]["inputs"]["filename_prefix"] = client_id
        
        # 保存并执行
        new_workflow_file = f"{client_id}.json"
        json.dump(workflow_data, Path(new_workflow_file).open("w"))
        
        img_bytes = self.infer.local(new_workflow_file)
        return Response(img_bytes, media_type="image/jpeg")
    
    def poll_server_health(self) -> Dict:
        """S6.4: 健康检查"""
        import socket
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/system_stats")
            urllib.request.urlopen(req, timeout=5)
            print("✅ ComfyUI 服务健康检查通过")
        except (socket.timeout, urllib.error.URLError) as e:
            print(f"❌ ComfyUI 服务健康检查失败: {e}")
            raise Exception("ComfyUI server is not healthy")


# =============================================================================
# 辅助函数
# =============================================================================

def _link_resources_from_volume():
    """
    链接 Volume 中所有持久化资源到 ComfyUI 目录
    - 链接模型文件
    - 链接自定义节点
    - 安装节点依赖
    """
    print("🔗 开始链接 Volume 中的持久化资源...")
    
    # 1. 链接模型
    _link_models_from_volume()
    
    # 2. 链接自定义节点并安装依赖
    _link_custom_nodes_from_volume()
    
    print("✅ 资源链接完成")


def _link_models_from_volume():
    """链接 Volume 中的模型文件"""
    print("📦 链接持久化的模型...")
    
    cache_models = Path("/cache/models")
    comfy_models = Path("/root/comfy/ComfyUI/models")
    
    if not cache_models.exists():
        print("   ℹ️ 无持久化模型")
        return
    
    linked_count = 0
    for model_type_dir in cache_models.iterdir():
        if not model_type_dir.is_dir():
            continue
        
        target_dir = comfy_models / model_type_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for model_file in model_type_dir.iterdir():
            link_path = target_dir / model_file.name
            if not link_path.exists() and not link_path.is_symlink():
                subprocess.run(
                    f"ln -s {model_file} {link_path}",
                    shell=True,
                    check=False
                )
                linked_count += 1
                print(f"   ✅ 已链接模型: {model_type_dir.name}/{model_file.name}")
    
    if linked_count == 0:
        print("   ℹ️ 无新模型需要链接")
    else:
        print(f"   📊 共链接 {linked_count} 个模型")


def _link_custom_nodes_from_volume():
    """链接 Volume 中持久化的自定义节点并安装依赖"""
    print("🧩 链接持久化的自定义节点...")
    
    cache_custom_nodes = Path("/cache/custom_nodes")
    comfy_custom_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    
    if not cache_custom_nodes.exists():
        print("   ℹ️ 无持久化节点")
        return
    
    linked_count = 0
    for node_dir in cache_custom_nodes.iterdir():
        if not node_dir.is_dir():
            continue
        
        link_path = comfy_custom_nodes / node_dir.name
        
        # 1. 创建符号链接
        if not link_path.exists() and not link_path.is_symlink():
            subprocess.run(
                f"ln -s {node_dir} {link_path}",
                shell=True,
                check=False
            )
            linked_count += 1
            print(f"   ✅ 已链接节点: {node_dir.name}")
        
        # 2. 安装节点依赖（关键修复！）
        req_file = node_dir / "requirements.txt"
        if req_file.exists():
            print(f"   📦 安装依赖: {node_dir.name}/requirements.txt")
            result = subprocess.run(
                f"pip install -r {req_file} --quiet",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"   ⚠️ 依赖安装警告: {result.stderr[:200]}")
    
    if linked_count == 0:
        print("   ℹ️ 无新节点需要链接")
    else:
        print(f"   📊 共链接 {linked_count} 个节点")


# =============================================================================
# S7: 管理服务阶段 - 诊断和热加载
# =============================================================================

@app.function(volumes={"/cache": vol})
def diagnose():
    """
    S7.1: 诊断 Volume 内容
    检查 Volume 中存储的模型和节点
    """
    print("=" * 60)
    print("🔍 ComfyUI Volume 诊断报告")
    print("=" * 60)
    
    result = {
        "models": {},
        "custom_nodes": [],
        "summary": {}
    }
    
    # 检查模型
    print("\n📦 模型检查:")
    cache_models = Path("/cache/models")
    if cache_models.exists():
        for model_type_dir in cache_models.iterdir():
            if model_type_dir.is_dir():
                files = list(model_type_dir.iterdir())
                result["models"][model_type_dir.name] = [f.name for f in files]
                print(f"   {model_type_dir.name}: {len(files)} 个")
                for f in files:
                    size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
                    print(f"      - {f.name} ({size_mb:.1f} MB)")
    else:
        print("   ℹ️ 无持久化模型目录")
    
    # 检查节点
    print("\n🧩 节点检查:")
    cache_nodes = Path("/cache/custom_nodes")
    if cache_nodes.exists():
        for node_dir in cache_nodes.iterdir():
            if node_dir.is_dir():
                has_req = (node_dir / "requirements.txt").exists()
                has_init = (node_dir / "__init__.py").exists()
                info = {
                    "name": node_dir.name,
                    "has_requirements": has_req,
                    "has_init": has_init
                }
                result["custom_nodes"].append(info)
                status = "✅" if has_init else "⚠️"
                print(f"   {status} {node_dir.name}")
                print(f"      requirements.txt: {'有' if has_req else '无'}")
                print(f"      __init__.py: {'有' if has_init else '无'}")
    else:
        print("   ℹ️ 无持久化节点目录")
    
    # 检查 ComfyUI 中已链接的节点
    print("\n🔗 ComfyUI 已链接节点:")
    comfy_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    if comfy_nodes.exists():
        for node in comfy_nodes.iterdir():
            if node.is_symlink():
                target = os.readlink(node)
                print(f"   🔗 {node.name} -> {target}")
            elif node.is_dir():
                print(f"   📁 {node.name} (内置)")
    
    # 汇总
    result["summary"] = {
        "total_models": sum(len(v) for v in result["models"].values()),
        "total_nodes": len(result["custom_nodes"]),
        "nodes_with_requirements": sum(1 for n in result["custom_nodes"] if n["has_requirements"])
    }
    
    print("\n" + "=" * 60)
    print(f"📊 汇总: {result['summary']['total_models']} 个模型, {result['summary']['total_nodes']} 个节点")
    print("=" * 60)
    
    return result


@app.function(volumes={"/cache": vol})
def verify_nodes():
    """
    S7.2: 验证节点安装
    检查 Volume 中的节点是否能被正确识别
    
    使用方法: modal run comfyui_app.py::verify_nodes
    
    注意: 此函数只是验证，不会影响正在运行的服务
    要使新节点生效，请运行: modal app stop comfyui-app
    """
    print("=" * 60)
    print("🔍 验证节点安装")
    print("=" * 60)
    
    cache_nodes = Path("/cache/custom_nodes")
    
    if not cache_nodes.exists():
        print("ℹ️ Volume 中无节点")
        return {"success": True, "nodes": []}
    
    nodes = []
    for node_dir in cache_nodes.iterdir():
        if not node_dir.is_dir():
            continue
        
        has_init = (node_dir / "__init__.py").exists()
        has_req = (node_dir / "requirements.txt").exists()
        
        status = "✅" if has_init else "⚠️ (缺少 __init__.py)"
        print(f"{status} {node_dir.name}")
        
        nodes.append({
            "name": node_dir.name,
            "valid": has_init,
            "has_requirements": has_req
        })
    
    valid_count = sum(1 for n in nodes if n["valid"])
    print(f"\n📊 共 {len(nodes)} 个节点，{valid_count} 个有效")
    
    if valid_count > 0:
        print("\n📌 要使节点生效，请运行:")
        print("   modal app stop comfyui-app")
        print("   然后访问 ComfyUI URL，服务会自动重启并加载节点")
    
    return {"success": True, "nodes": nodes, "valid_count": valid_count}


@app.function(volumes={"/cache": vol})
def list_available_nodes():
    """
    S7.3: 列出可用的自定义节点
    
    使用方法: modal run comfyui_app.py::list_available_nodes
    """
    print("=" * 60)
    print("📋 可用的自定义节点")
    print("=" * 60)
    
    cache_nodes = Path("/cache/custom_nodes")
    nodes = []
    
    if cache_nodes.exists():
        for node_dir in cache_nodes.iterdir():
            if node_dir.is_dir():
                # 尝试读取安装信息
                info_file = node_dir / ".install_info.json"
                if info_file.exists():
                    info = json.loads(info_file.read_text())
                else:
                    info = {"node_name": node_dir.name}
                
                nodes.append(info)
                print(f"\n📦 {info.get('node_name', node_dir.name)}")
                if info.get('repo_url'):
                    print(f"   仓库: {info['repo_url']}")
                if info.get('installed_at'):
                    print(f"   安装时间: {info['installed_at']}")
    else:
        print("ℹ️ 暂无自定义节点")
    
    print(f"\n{'='*60}")
    print(f"总计: {len(nodes)} 个节点")
    
    return nodes


# =============================================================================
# 本地入口
# =============================================================================

@app.local_entrypoint()
def main():
    """
    本地入口
    
    使用方法:
        modal deploy comfyui_app.py      # 部署应用
        modal run comfyui_app.py         # 本地测试
    """
    print("=" * 60)
    print("ComfyUI 应用配置完成")
    print("=" * 60)
    print("\n使用 'modal deploy comfyui_app.py' 部署服务")
    print("\n部署后访问:")
    print("  - Web UI: https://[your-workspace]--comfyui-app-ui.modal.run")
    print("  - API: https://[your-workspace]--comfyui-app-comfyui-api.modal.run")


