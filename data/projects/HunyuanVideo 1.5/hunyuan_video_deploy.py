"""
=============================================================================
HunyuanVideo 1.5 ComfyUI 视频生成服务
=============================================================================
腾讯混元视频 1.5 - 8.3B 参数轻量级视频生成模型

⚠️ 首次使用请先配置项目变量（点击项目标题旁的齿轮图标）:
  - VOLUME_NAME: 模型存储 Volume 名称 (默认: hunyuan-video-cache)
  - APP_NAME: Modal 应用名称 (默认: hunyuan-video-app)
  - GPU_TYPE: GPU 类型 (推荐: H100, A100-80GB)

特点：
- 8.3B 参数，消费级 GPU 可运行 (16GB+ VRAM)
- 支持 480p/720p/1080p 多分辨率
- 支持文生视频 (T2V) 和图生视频 (I2V)
- 内置 ComfyUI 原生支持

使用方法:
    1. 配置项目变量
    2. 先运行 download_models.py 下载模型
    3. 部署应用: modal deploy hunyuan_video_deploy.py
=============================================================================
"""
import os
import subprocess
from pathlib import Path

import modal

# =============================================================================
# 项目变量 - 在项目变量管理中配置
# =============================================================================
VOLUME_NAME = "hunyuan-video-cache"
APP_NAME = "hunyuan-video-app"
GPU_TYPE = "H100"  # 推荐 H100 或 A100-80GB

# =============================================================================
# Volume 和镜像配置
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl", "ffmpeg")
    .pip_install(
        "fastapi[standard]==0.115.4",
        "comfy-cli==1.5.3",
        "requests==2.32.3",
        "huggingface_hub[hf_transfer]==0.34.4",
        "torch>=2.1.0",
        "accelerate",
        "xformers",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_commands(
        "comfy --skip-prompt install --fast-deps --nvidia --version 0.3.75",
        # 安装 HunyuanVideo ComfyUI 原生支持节点
        "comfy node install ComfyUI-HunyuanVideoWrapper || true",
    )
)

try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

app = modal.App(name=APP_NAME, image=image)


def link_models_from_volume():
    """从 Volume 链接模型到 ComfyUI"""
    print("🔗 链接 Volume 中的模型...")
    
    volume_models = Path("/models")
    comfy_models = Path("/root/comfy/ComfyUI/models")
    
    if not volume_models.exists():
        print("   ℹ️ Volume 中暂无模型，请先运行 download_models.py")
        return 0
    
    linked = 0
    # HunyuanVideo 需要的模型目录
    model_types = [
        "diffusion_models",  # 主模型
        "text_encoders",     # 文本编码器 (clip_l, llava_llama3)
        "vae",               # VAE 模型
        "checkpoints",       # 可选的 checkpoint
        "loras",             # LoRA 模型
    ]
    
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
    timeout=86400,
    secrets=[hf_secret] if hf_secret else [],
)
@modal.concurrent(max_inputs=5)
@modal.web_server(8000, startup_timeout=120)
def ui():
    """HunyuanVideo ComfyUI Web 界面"""
    print("🌐 启动 HunyuanVideo 1.5 Web 界面...")
    link_models_from_volume()
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)


@app.cls(
    scaledown_window=300,
    gpu=GPU_TYPE,
    volumes={"/models": vol},
    secrets=[hf_secret] if hf_secret else [],
)
@modal.concurrent(max_inputs=3)
class HunyuanVideoAPI:
    """HunyuanVideo 1.5 API 服务"""
    
    @modal.enter()
    def startup(self):
        print("🚀 启动 HunyuanVideo 1.5 API 服务...")
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
    
    @modal.fastapi_endpoint(method="GET")
    def health(self):
        """健康检查"""
        return {"status": "healthy", "model": "HunyuanVideo 1.5", "gpu": GPU_TYPE}


@app.local_entrypoint()
def main():
    print("=" * 60)
    print(f"HunyuanVideo 1.5 ComfyUI ({APP_NAME})")
    print("=" * 60)
    print(f"\n📦 Volume: {VOLUME_NAME}")
    print(f"🖥️ GPU: {GPU_TYPE}")
    print("\n📌 使用方法:")
    print("   1. 先运行 download_models.py 下载模型")
    print("   2. 部署: modal deploy hunyuan_video_deploy.py")
    print(f"   3. 访问 UI: https://[workspace]--{APP_NAME}-ui.modal.run")
