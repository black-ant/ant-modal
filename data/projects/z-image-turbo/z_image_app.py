"""
=============================================================================
Z-Image-Turbo ComfyUI 应用服务
=============================================================================
⚠️ 首次使用请先配置项目变量（点击项目标题旁的齿轮图标）:
  - VOLUME_NAME: 模型存储 Volume 名称
  - APP_NAME: Modal 应用名称（所有脚本共用）
  - GPU_TYPE: GPU 类型

特点：
- 启动后可随时添加模型，无需重启
- 内置热加载 API，下载模型后自动生效
- 支持中英文双语输入

使用方法:
    1. 配置项目变量
    2. 部署应用: modal deploy z_image_app.py
    3. 添加模型: 使用"添加模型"脚本
=============================================================================
"""
import os
import subprocess
from pathlib import Path

import modal

# =============================================================================
# 项目变量 - 在项目变量管理中配置
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"
GPU_TYPE = "{{GPU_TYPE:GPU 类型:L40S}}"

# =============================================================================
# Volume 和镜像配置
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl")
    .pip_install(
        "fastapi[standard]==0.115.4",
        "comfy-cli==1.5.3",
        "requests==2.32.3",
        "huggingface_hub[hf_transfer]==0.34.4"
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia")
)

try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# 使用项目变量中的 APP_NAME
app = modal.App(name=APP_NAME, image=image)


def link_models_from_volume():
    """从 Volume 链接模型到 ComfyUI"""
    print("🔗 链接 Volume 中的模型...")
    
    volume_models = Path("/models")
    comfy_models = Path("/root/comfy/ComfyUI/models")
    
    if not volume_models.exists():
        print("   ℹ️ Volume 中暂无模型")
        return 0
    
    linked = 0
    model_types = ["checkpoints", "loras", "vae", "clip", "text_encoders", 
                   "diffusion_models", "controlnet", "upscale_models", "embeddings"]
    
    for model_type in model_types:
        src_dir = volume_models / model_type
        if not src_dir.exists():
            continue
        
        dst_dir = comfy_models / model_type
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        for model_file in src_dir.iterdir():
            if model_file.name.startswith('.'):
                continue
            dst_path = dst_dir / model_file.name
            if not dst_path.exists() and not dst_path.is_symlink():
                os.symlink(str(model_file), str(dst_path))
                linked += 1
                print(f"   ✅ {model_type}/{model_file.name}")
    
    print(f"   📊 共链接 {linked} 个模型")
    return linked


@app.function(
    max_containers=1,
    gpu=GPU_TYPE,
    volumes={"/models": vol},
    timeout=86400
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """ComfyUI Web 界面"""
    print("🌐 启动 Z-Image-Turbo Web 界面...")
    link_models_from_volume()
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)


@app.cls(
    scaledown_window=300,
    gpu=GPU_TYPE,
    volumes={"/models": vol}
)
@modal.concurrent(max_inputs=5)
class ZImageAPI:
    """Z-Image-Turbo API 服务"""
    
    @modal.enter()
    def startup(self):
        print("🚀 启动 Z-Image-Turbo API 服务...")
        link_models_from_volume()
        subprocess.run("comfy launch --background -- --port 8000", shell=True, check=True)
    
    @modal.fastapi_endpoint(method="POST")
    def reload(self):
        """热加载模型 - 下载新模型后调用"""
        print("🔄 热加载请求...")
        try:
            vol.reload()
            count = link_models_from_volume()
            return {"success": True, "message": f"热加载完成，链接了 {count} 个新模型"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @modal.fastapi_endpoint(method="GET")
    def models(self):
        """列出所有可用模型"""
        vol.reload()
        models = {}
        volume_models = Path("/models")
        if volume_models.exists():
            for type_dir in volume_models.iterdir():
                if type_dir.is_dir():
                    files = [f.name for f in type_dir.iterdir() if not f.name.startswith('.')]
                    if files:
                        models[type_dir.name] = files
        return {"models": models, "total": sum(len(v) for v in models.values())}


@app.local_entrypoint()
def main():
    print("=" * 60)
    print(f"Z-Image-Turbo ComfyUI ({APP_NAME})")
    print("=" * 60)
    print(f"\n📦 Volume: {VOLUME_NAME}")
    print(f"🖥️ GPU: {GPU_TYPE}")
    print("\n📌 使用方法:")
    print("   1. 部署: modal deploy z_image_app.py")
    print("   2. 添加模型: 使用'添加模型'脚本")
    print(f"   3. 访问 UI: https://[workspace]--{APP_NAME}-ui.modal.run")
