"""
=============================================================================
Z-Image-Turbo 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到项目共享的 Volume

使用方法:
    modal run add_model_hf.py
=============================================================================
"""
import modal
import os
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
HF_REPO_ID = "{{HF_REPO_ID:HuggingFace 仓库 ID:Comfy-Org/z_image_turbo}}"
HF_FILENAME = "{{HF_FILENAME:文件名:z_image_turbo.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:diffusion_models}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]", "requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# 使用项目的 APP_NAME 作为前缀
app = modal.App(f"{APP_NAME}-downloader", image=image)


@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else []
)
def download_model():
    """从 HuggingFace 下载模型"""
    from huggingface_hub import hf_hub_download
    
    repo_id = HF_REPO_ID
    filename = HF_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 只取文件名，忽略 HuggingFace 仓库中的子目录路径
    local_name = Path(filename).name
    
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / local_name
    
    if target_file.exists():
        print(f"\n⚠️ 模型已存在: {local_name}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\n⏳ 下载中...")
        hf_token = os.getenv("HF_TOKEN")
        
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/tmp/hf_cache",
            token=hf_token
        )
        
        import shutil
        shutil.copy2(cached_path, str(target_file))
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\n✅ 下载成功!")
        print(f"   文件: {model_type}/{local_name}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "local_name": local_name}
        
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


def trigger_hot_reload():
    """触发主服务热加载"""
    print(f"\n🔄 触发热加载...")
    
    try:
        # 尝试查找并调用已部署的 ZImageAPI.reload 方法
        ZImageAPI = modal.Cls.lookup(APP_NAME, "ZImageAPI")
        result = ZImageAPI().reload.remote()
        
        if result.get("success"):
            print(f"   ✅ 热加载成功!")
            return True
        else:
            print(f"   ⚠️ 热加载响应: {result}")
            return False
            
    except modal.exception.NotFoundError:
        print(f"   ⚠️ 主服务 ({APP_NAME}) 尚未部署")
        print(f"   💡 请先部署主服务: modal deploy z_image_app.py")
        return False
    except Exception as e:
        print(f"   ⚠️ 热加载失败: {e}")
        print(f"   💡 如果主服务未运行，模型将在下次启动时自动加载")
        return False


@app.local_entrypoint()
def main():
    print(f"\n{'='*60}")
    print(f"Z-Image-Turbo 添加模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = download_model.remote()
    
    if result.get("success"):
        if result.get("action") == "downloaded":
            print(f"\n✅ 模型下载完成: {result.get('local_name')}")
            # 自动触发热加载
            trigger_hot_reload()
        else:
            print(f"\n✅ 模型已存在，无需下载")
    else:
        print(f"\n❌ 失败: {result.get('error')}")

