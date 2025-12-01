"""
=============================================================================
Z-Image-Turbo 诊断工具
=============================================================================
检查项目共享 Volume 和服务状态

使用方法:
    modal run diagnose.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-diagnose", image=image)


@app.function(volumes={"/models": vol})
def diagnose():
    """诊断系统状态"""
    print("=" * 60)
    print(f"🔍 Z-Image-Turbo 诊断报告")
    print("=" * 60)
    
    print(f"\n📦 项目配置:")
    print(f"   APP_NAME: {APP_NAME}")
    print(f"   VOLUME_NAME: {VOLUME_NAME}")
    
    print(f"\n📦 Volume 检查:")
    volume_models = Path("/models")
    if volume_models.exists():
        total_size = 0
        total_files = 0
        for f in volume_models.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
                total_files += 1
        print(f"   文件数: {total_files}")
        print(f"   总大小: {total_size / (1024*1024*1024):.2f} GB")
    else:
        print("   ℹ️ Volume 为空")
    
    print("\n📊 模型统计:")
    model_types = ["checkpoints", "loras", "vae", "clip", "text_encoders",
                   "diffusion_models", "controlnet", "upscale_models", "embeddings"]
    
    has_models = False
    for model_type in model_types:
        type_dir = volume_models / model_type
        if type_dir.exists():
            count = len([f for f in type_dir.iterdir() if not f.name.startswith('.')])
            if count > 0:
                print(f"   {model_type}: {count} 个")
                has_models = True
    
    if not has_models:
        print("   ℹ️ 暂无模型")
    
    print(f"\n🌐 服务访问地址:")
    print(f"   UI: https://[workspace]--{APP_NAME}-ui.modal.run")
    print(f"   API: https://[workspace]--{APP_NAME}-zimageapi-*.modal.run")
    
    print("\n" + "=" * 60)
    print("✅ 诊断完成")
    
    return {"success": True}


@app.local_entrypoint()
def main():
    print("\n🔍 开始诊断 Z-Image-Turbo...")
    diagnose.remote()

