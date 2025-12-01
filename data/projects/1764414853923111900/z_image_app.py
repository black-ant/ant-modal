"""
=============================================================================
Z-Image-Turbo ComfyUI 应用服务 (简化版)
=============================================================================
特点：
- 启动后可随时添加模型，无需重启
- 内置热加载 API，下载模型后自动生效
- 支持中英文双语输入

使用方法:
    1. 部署应用:  modal deploy z_image_app.py
    2. 添加模型:  modal run download_models.py --repo-id=xxx --filename=xxx
    3. 模型自动热加载，无需重启！
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
# Volume 配置 - 所有模型存储在这里
# =============================================================================
vol = modal.Volume.from_name("z-image-models", create_if_missing=True)

# =============================================================================
# 镜像配置
# =============================================================================
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

# HuggingFace Secret (可选)
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# =============================================================================
# Modal App
# =============================================================================
app = modal.App(name="z-image-turbo", image=image)


# =============================================================================
# 辅助函数
# =============================================================================

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


# =============================================================================
# Web UI 服务
# =============================================================================

@app.function(
    max_containers=1,
    gpu="L40S",
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


# =============================================================================
# API 服务 (含热加载)
# =============================================================================

@app.cls(
    scaledown_window=300,
    gpu="L40S",
    volumes={"/models": vol}
)
@modal.concurrent(max_inputs=5)
class ZImageAPI:
    """Z-Image-Turbo API 服务"""
    
    @modal.enter()
    def startup(self):
        """容器启动时初始化"""
        print("🚀 启动 Z-Image-Turbo API 服务...")
        link_models_from_volume()
        subprocess.run("comfy launch --background -- --port 8000", shell=True, check=True)
    
    # =========================================================================
    # 🔥 热加载 API - 核心功能
    # =========================================================================
    
    @modal.fastapi_endpoint(method="POST")
    def reload(self):
        """
        热加载模型 - 下载新模型后调用此接口
        
        调用方式:
            curl -X POST https://[workspace]--z-image-turbo-zimageapi-reload.modal.run
        """
        print("🔄 热加载请求...")
        
        try:
            # 1. 刷新 Volume 视图
            vol.reload()
            print("   ✅ Volume 已刷新")
            
            # 2. 重新链接模型
            count = link_models_from_volume()
            
            return {
                "success": True,
                "message": f"热加载完成，链接了 {count} 个新模型",
                "linked_count": count
            }
        except Exception as e:
            print(f"   ❌ 热加载失败: {e}")
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
                    files = [f.name for f in type_dir.iterdir() 
                             if not f.name.startswith('.')]
                    if files:
                        models[type_dir.name] = files
        
        return {"models": models, "total": sum(len(v) for v in models.values())}
    
    @modal.fastapi_endpoint(method="POST")
    def generate(self, item: Dict):
        """生成图像 API"""
        from fastapi import Response
        
        prompt = item.get("prompt", "一位美丽的女性，照片级真实")
        
        # 简化的生成逻辑
        print(f"🎨 生成图像: {prompt[:50]}...")
        
        # TODO: 实现实际的图像生成逻辑
        return {"status": "received", "prompt": prompt}


# =============================================================================
# 管理命令
# =============================================================================

@app.function(volumes={"/models": vol})
def list_models():
    """列出 Volume 中的所有模型"""
    print("=" * 60)
    print("📋 Z-Image-Turbo 模型列表")
    print("=" * 60)
    
    models = {}
    volume_models = Path("/models")
    
    if not volume_models.exists():
        print("\nℹ️ 暂无模型，使用以下命令添加:")
        print("   modal run download_models.py --help")
        return models
    
    total = 0
    for type_dir in volume_models.iterdir():
        if type_dir.is_dir():
            files = []
            for f in type_dir.iterdir():
                if not f.name.startswith('.'):
                    try:
                        size = f.stat().st_size / (1024*1024)
                        files.append((f.name, size))
                    except:
                        files.append((f.name, 0))
            
            if files:
                models[type_dir.name] = files
                total += len(files)
                print(f"\n📁 {type_dir.name}:")
                for name, size in files:
                    print(f"   - {name} ({size:.1f} MB)")
    
    print(f"\n{'='*60}")
    print(f"📊 共 {total} 个模型")
    
    return models


@app.function(volumes={"/models": vol})
def diagnose():
    """诊断 Volume 和 ComfyUI 状态"""
    print("=" * 60)
    print("🔍 系统诊断")
    print("=" * 60)
    
    # 检查 Volume
    print("\n📦 Volume 检查:")
    volume_models = Path("/models")
    if volume_models.exists():
        total_size = 0
        for f in volume_models.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
        print(f"   总大小: {total_size / (1024*1024*1024):.2f} GB")
    else:
        print("   ℹ️ Volume 为空")
    
    # 检查 ComfyUI
    print("\n🖥️ ComfyUI 检查:")
    comfy_path = Path("/root/comfy/ComfyUI")
    if comfy_path.exists():
        print(f"   ✅ ComfyUI 已安装")
    else:
        print(f"   ❌ ComfyUI 未安装")
    
    print("\n" + "=" * 60)


# =============================================================================
# 本地入口
# =============================================================================

@app.local_entrypoint()
def main(action: str = "info"):
    """
    本地入口
    
    参数:
        action: info, list, diagnose
    """
    if action == "list":
        list_models.remote()
    elif action == "diagnose":
        diagnose.remote()
    else:
        print("=" * 60)
        print("Z-Image-Turbo ComfyUI")
        print("=" * 60)
        print("\n📌 使用方法:")
        print("   1. 部署: modal deploy z_image_app.py")
        print("   2. 添加模型: modal run download_models.py --action=hf --repo-id=xxx --filename=xxx")
        print("   3. 查看模型: modal run z_image_app.py --action=list")
        print("\n🌐 访问地址:")
        print("   - UI: https://[workspace]--z-image-turbo-ui.modal.run")
        print("   - API: https://[workspace]--z-image-turbo-zimageapi-*.modal.run")
