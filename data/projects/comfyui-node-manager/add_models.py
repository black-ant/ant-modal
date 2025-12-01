"""
=============================================================================
ComfyUI 添加模型
=============================================================================
从 HuggingFace 或 URL 下载模型到 ComfyUI 的 models 目录

使用方法:
    # 从 HuggingFace 下载
    modal run add_models.py --action=add-hf --repo-id=Comfy-Org/flux1-dev --filename=flux1-dev-fp8.safetensors --type=checkpoints
    
    # 从 URL 下载
    modal run add_models.py --action=add-url --url=https://xxx/model.safetensors --filename=model.safetensors --type=loras
    
    # 列出已下载的模型
    modal run add_models.py --action=list
    
    # 删除模型
    modal run add_models.py --action=remove --type=checkpoints --filename=xxx.safetensors

支持的模型类型 (--type):
    checkpoints, loras, vae, clip, controlnet, upscale_models, embeddings

重要说明:
    添加模型后需要重启 ComfyUI 服务才能生效:
    1. 运行: modal app stop comfyui-app
    2. 访问 ComfyUI URL，服务会自动重启并加载新模型
=============================================================================
"""
import modal
import os
import json
import requests
from pathlib import Path
from datetime import datetime

# Volume 名称 - 必须与 comfyui_app.py 使用相同的 Volume
VOLUME_NAME = "comfyui-cache"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 镜像配置
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("requests", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("comfyui-model-manager", image=image)

# 模型存储路径
MODELS_PATH = "/cache/models"

# 支持的模型类型
VALID_MODEL_TYPES = [
    "checkpoints", "loras", "vae", "clip", 
    "controlnet", "upscale_models", "embeddings"
]


@app.function(
    volumes={"/cache": vol},
    timeout=1800  # 30分钟超时，大模型可能需要较长时间
)
def download_from_huggingface(repo_id: str, filename: str, model_type: str):
    """
    从 HuggingFace 下载模型
    """
    from huggingface_hub import hf_hub_download
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"{'='*60}\n")
    
    if model_type not in VALID_MODEL_TYPES:
        return {
            "success": False, 
            "error": f"不支持的模型类型: {model_type}，支持: {', '.join(VALID_MODEL_TYPES)}"
        }
    
    # 目标目录
    target_dir = Path(MODELS_PATH) / model_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    # 检查是否已存在
    if target_file.exists():
        print(f"⚠️ 模型已存在: {filename}")
        return {
            "success": True,
            "action": "exists",
            "message": f"模型已存在: {filename}"
        }
    
    try:
        print("[1/2] 开始下载...")
        hf_token = os.getenv("HF_TOKEN")
        
        # 下载到 HF 缓存
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/cache/hf_cache",
            token=hf_token
        )
        
        print(f"✓ 下载完成: {cached_path}\n")
        
        # 创建符号链接到模型目录
        print("[2/2] 创建链接...")
        os.symlink(cached_path, str(target_file))
        
        # 记录下载信息
        info_file = target_dir / f".{filename}.info.json"
        info = {
            "filename": filename,
            "repo_id": repo_id,
            "model_type": model_type,
            "source": "huggingface",
            "downloaded_at": datetime.now().isoformat()
        }
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        vol.commit()
        print(f"✓ 已保存到 Volume\n")
        
        print(f"{'='*60}")
        print(f"✅ 模型下载成功: {filename}")
        print(f"   位置: {model_type}/{filename}")
        print(f"{'='*60}")
        print(f"\n📌 下一步:")
        print(f"   1. 运行: modal app stop comfyui-app")
        print(f"   2. 访问 ComfyUI URL，服务会自动重启并加载新模型")
        
        return {
            "success": True,
            "action": "downloaded",
            "filename": filename,
            "model_type": model_type,
            "message": "模型下载成功，请重启 ComfyUI 服务"
        }
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.function(
    volumes={"/cache": vol},
    timeout=1800
)
def download_from_url(url: str, filename: str, model_type: str):
    """
    从 URL 直接下载模型
    """
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"文件名: {filename}")
    print(f"类型: {model_type}")
    print(f"{'='*60}\n")
    
    if model_type not in VALID_MODEL_TYPES:
        return {
            "success": False, 
            "error": f"不支持的模型类型: {model_type}，支持: {', '.join(VALID_MODEL_TYPES)}"
        }
    
    # 目标目录
    target_dir = Path(MODELS_PATH) / model_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    # 检查是否已存在
    if target_file.exists():
        print(f"⚠️ 模型已存在: {filename}")
        return {
            "success": True,
            "action": "exists",
            "message": f"模型已存在: {filename}"
        }
    
    try:
        print("[1/2] 开始下载...")
        
        # 使用流式下载
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            print(f"   文件大小: {total_size / (1024*1024*1024):.2f} GB")
        
        # 下载文件
        downloaded = 0
        with open(target_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192*1024):  # 8MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r   进度: {progress:.1f}%", end="", flush=True)
        
        print(f"\n✓ 下载完成\n")
        
        # 记录下载信息
        print("[2/2] 记录信息...")
        info_file = target_dir / f".{filename}.info.json"
        info = {
            "filename": filename,
            "url": url,
            "model_type": model_type,
            "source": "url",
            "size_bytes": target_file.stat().st_size,
            "downloaded_at": datetime.now().isoformat()
        }
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        vol.commit()
        print(f"✓ 已保存到 Volume\n")
        
        print(f"{'='*60}")
        print(f"✅ 模型下载成功: {filename}")
        print(f"   位置: {model_type}/{filename}")
        print(f"{'='*60}")
        print(f"\n📌 下一步:")
        print(f"   1. 运行: modal app stop comfyui-app")
        print(f"   2. 访问 ComfyUI URL，服务会自动重启并加载新模型")
        
        return {
            "success": True,
            "action": "downloaded",
            "filename": filename,
            "model_type": model_type,
            "message": "模型下载成功，请重启 ComfyUI 服务"
        }
        
    except Exception as e:
        # 清理失败的下载
        if target_file.exists():
            target_file.unlink()
        print(f"❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.function(
    volumes={"/cache": vol},
    timeout=60
)
def list_models():
    """
    列出已下载的模型
    """
    print("=" * 60)
    print("📋 已下载的模型")
    print("=" * 60)
    
    models = {}
    models_path = Path(MODELS_PATH)
    
    if models_path.exists():
        for model_type_dir in models_path.iterdir():
            if model_type_dir.is_dir() and model_type_dir.name in VALID_MODEL_TYPES:
                model_type = model_type_dir.name
                models[model_type] = []
                
                for model_file in model_type_dir.iterdir():
                    if model_file.is_file() or model_file.is_symlink():
                        if not model_file.name.startswith('.'):
                            # 尝试获取文件大小
                            try:
                                if model_file.is_symlink():
                                    size = Path(os.readlink(model_file)).stat().st_size
                                else:
                                    size = model_file.stat().st_size
                                size_str = f"{size / (1024*1024):.1f} MB"
                            except:
                                size_str = "未知"
                            
                            models[model_type].append({
                                "name": model_file.name,
                                "size": size_str
                            })
                
                if models[model_type]:
                    print(f"\n📁 {model_type}:")
                    for m in models[model_type]:
                        print(f"   - {m['name']} ({m['size']})")
    
    total = sum(len(v) for v in models.values())
    print(f"\n{'='*60}")
    print(f"总计: {total} 个模型")
    
    return {"success": True, "models": models, "total": total}


@app.function(
    volumes={"/cache": vol},
    timeout=60
)
def remove_model(model_type: str, filename: str):
    """
    删除指定的模型
    """
    print(f"🗑️ 删除模型: {model_type}/{filename}")
    
    if model_type not in VALID_MODEL_TYPES:
        return {
            "success": False, 
            "error": f"不支持的模型类型: {model_type}"
        }
    
    model_file = Path(MODELS_PATH) / model_type / filename
    info_file = Path(MODELS_PATH) / model_type / f".{filename}.info.json"
    
    if not model_file.exists():
        print(f"❌ 模型不存在: {filename}")
        return {"success": False, "error": f"模型不存在: {filename}"}
    
    try:
        # 如果是符号链接，只删除链接
        if model_file.is_symlink():
            model_file.unlink()
        else:
            model_file.unlink()
        
        # 删除信息文件
        if info_file.exists():
            info_file.unlink()
        
        vol.commit()
        print(f"✅ 模型已删除: {filename}")
        print(f"\n📌 请重启 ComfyUI 服务使更改生效")
        return {"success": True, "message": f"模型 {filename} 已删除"}
        
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main(
    action: str = "list",
    repo_id: str = "",
    url: str = "",
    filename: str = "",
    type: str = "checkpoints"
):
    """
    本地入口 - 支持命令行参数
    
    使用方法:
        modal run add_models.py --action=add-hf --repo-id=xxx --filename=xxx --type=checkpoints
        modal run add_models.py --action=add-url --url=xxx --filename=xxx --type=loras
        modal run add_models.py --action=list
        modal run add_models.py --action=remove --type=xxx --filename=xxx
    """
    print(f"\n{'='*60}")
    print("ComfyUI 模型管理")
    print(f"{'='*60}")
    print(f"操作: {action}")
    
    if action == "add-hf":
        if not repo_id or not filename:
            print("❌ 错误: 请提供 --repo-id 和 --filename 参数")
            return
        print(f"仓库: {repo_id}")
        print(f"文件: {filename}")
        print(f"类型: {type}")
        print(f"{'='*60}\n")
        result = download_from_huggingface.remote(repo_id, filename, type)
        
    elif action == "add-url":
        if not url or not filename:
            print("❌ 错误: 请提供 --url 和 --filename 参数")
            return
        print(f"URL: {url}")
        print(f"文件: {filename}")
        print(f"类型: {type}")
        print(f"{'='*60}\n")
        result = download_from_url.remote(url, filename, type)
        
    elif action == "list":
        print(f"{'='*60}\n")
        result = list_models.remote()
        
    elif action == "remove":
        if not filename:
            print("❌ 错误: 请提供 --filename 参数")
            return
        print(f"类型: {type}")
        print(f"文件: {filename}")
        print(f"{'='*60}\n")
        result = remove_model.remote(type, filename)
        
    else:
        print(f"❌ 未知操作: {action}")
        print("支持的操作: add-hf, add-url, list, remove")
        return
    
    if result.get("success"):
        print(f"\n✅ 操作完成")
    else:
        print(f"\n❌ 操作失败: {result.get('error')}")
