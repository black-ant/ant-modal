"""
=============================================================================
Z-Image-Turbo 添加模型 (URL)
=============================================================================
从 URL 直接下载模型到项目共享的 Volume

使用方法:
    modal run add_model_url.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
MODEL_URL = "{{MODEL_URL:模型下载 URL:}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名:model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:loras}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests", "tqdm")

app = modal.App(f"{APP_NAME}-url-downloader", image=image)


@app.function(volumes={"/models": vol}, timeout=3600)
def download_model():
    """从 URL 下载模型"""
    import requests
    from tqdm import tqdm
    
    url = MODEL_URL
    filename = MODEL_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if not url:
        return {"success": False, "error": "未提供下载 URL"}
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    if target_file.exists():
        print(f"\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\n⏳ 下载中...")
        
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(target_file, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192*1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\n✅ 下载成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "filename": filename}
        
    except Exception as e:
        if target_file.exists():
            target_file.unlink()
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
            print(f"\n✅ 模型下载完成: {result.get('filename')}")
            # 自动触发热加载
            trigger_hot_reload()
        else:
            print(f"\n✅ 模型已存在，无需下载")
    else:
        print(f"\n❌ 失败: {result.get('error')}")

