"""
=============================================================================
Z-Image-Turbo 模型管理
=============================================================================
管理项目共享 Volume 中的模型：列出、删除

使用方法:
    modal run manage_models.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-manager", image=image)


@app.function(volumes={"/models": vol})
def list_models():
    """列出所有模型"""
    print("=" * 60)
    print(f"📋 模型列表 (Volume: {VOLUME_NAME})")
    print("=" * 60)
    
    models = {}
    total = 0
    
    for model_type in MODEL_TYPES:
        type_dir = Path(f"/models/{model_type}")
        if type_dir.exists():
            files = []
            for f in type_dir.iterdir():
                if not f.name.startswith('.'):
                    try:
                        size = f.stat().st_size / (1024*1024)
                        files.append({"name": f.name, "size_mb": size})
                    except:
                        files.append({"name": f.name, "size_mb": 0})
            
            if files:
                models[model_type] = files
                total += len(files)
                print(f"\n📁 {model_type}:")
                for f in files:
                    print(f"   - {f['name']} ({f['size_mb']:.1f} MB)")
    
    if not models:
        print("\nℹ️ 暂无模型")
        print("\n💡 使用'添加模型'脚本下载模型")
    
    print(f"\n{'='*60}")
    print(f"📊 共 {total} 个模型")
    
    return {"models": models, "total": total}


@app.local_entrypoint()
def main():
    print(f"\n{'='*60}")
    print(f"Z-Image-Turbo 模型管理 ({APP_NAME})")
    print(f"{'='*60}")
    list_models.remote()

