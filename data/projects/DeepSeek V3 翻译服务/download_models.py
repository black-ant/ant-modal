"""
=============================================================================
Z-Image-Turbo 模型下载器 (简化版)
=============================================================================
下载模型后自动触发热加载，无需重启应用！

使用方法:
    # 从 HuggingFace 下载
    modal run download_models.py --action=hf --repo-id=Comfy-Org/z_image_turbo --filename=qwen_3_4b.safetensors --type=text_encoders
    
    # 从 URL 下载
    modal run download_models.py --action=url --url=https://xxx/model.safetensors --filename=model.safetensors --type=checkpoints
    
    # 列出已有模型
    modal run download_models.py --action=list
    
    # 手动触发热加载
    modal run download_models.py --action=reload

支持的模型类型 (--type):
    checkpoints, loras, vae, clip, text_encoders, diffusion_models, 
    controlnet, upscale_models, embeddings
=============================================================================

@modal-args
{{action|操作类型|list|select|list,hf,url,delete,reload}}
{{repo_id|HuggingFace仓库ID||text}}
{{filename|文件名||text}}
{{type|模型类型|checkpoints|select|checkpoints,loras,vae,clip,text_encoders,diffusion_models,controlnet,upscale_models,embeddings}}
{{url|下载URL||text}}
{{no_reload|跳过热加载|false|bool}}
@modal-args-end
"""
import modal
import os
import requests
from pathlib import Path
from datetime import datetime

# =============================================================================
# 配置
# =============================================================================

# 与主应用共享同一个 Volume
VOLUME_NAME = "z-image-models"
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 支持的模型类型
MODEL_TYPES = [
    "checkpoints", "loras", "vae", "clip", "text_encoders",
    "diffusion_models", "controlnet", "upscale_models", "embeddings"
]

# 热加载 API URL (部署后会自动生成)
# 格式: https://[workspace]--z-image-turbo-zimageapi-reload.modal.run
RELOAD_API_URL = os.getenv("Z_IMAGE_RELOAD_URL", "")

# HuggingFace Secret
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# 镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]", "requests", "tqdm")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("z-image-downloader", image=image)


# =============================================================================
# 热加载函数
# =============================================================================

def trigger_reload(reload_url: str = None):
    """
    触发主应用的热加载
    """
    url = reload_url or RELOAD_API_URL
    
    if not url:
        print("\n⚠️ 未配置热加载 URL")
        print("   请设置环境变量 Z_IMAGE_RELOAD_URL 或使用 --reload-url 参数")
        print("   URL 格式: https://[workspace]--z-image-turbo-zimageapi-reload.modal.run")
        return False
    
    print(f"\n🔄 触发热加载...")
    print(f"   URL: {url}")
    
    try:
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"   ✅ 热加载成功! 链接了 {result.get('linked_count', 0)} 个模型")
                return True
            else:
                print(f"   ⚠️ 热加载响应: {result}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️ 无法连接 (服务可能未运行)")
        print("   💡 请先部署: modal deploy z_image_app.py")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    return False


# =============================================================================
# 下载函数
# =============================================================================

@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else []
)
def download_from_hf(repo_id: str, filename: str, model_type: str = "checkpoints", subfolder: str = ""):
    """从 HuggingFace 下载模型"""
    from huggingface_hub import hf_hub_download
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 目标路径
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    # 检查是否已存在
    if target_file.exists() or target_file.is_symlink():
        print(f"\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists", "file": filename}
    
    try:
        print(f"\n⏳ 下载中...")
        hf_token = os.getenv("HF_TOKEN")
        
        # 下载
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            subfolder=subfolder if subfolder else None,
            cache_dir="/tmp/hf_cache",
            token=hf_token
        )
        
        # 复制到 Volume (使用符号链接节省空间)
        import shutil
        shutil.copy2(cached_path, str(target_file))
        
        # 提交 Volume
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\n✅ 下载成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {
            "success": True, 
            "action": "downloaded",
            "file": filename,
            "type": model_type,
            "size_mb": size_mb
        }
        
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.function(
    volumes={"/models": vol},
    timeout=3600
)
def download_from_url(url: str, filename: str, model_type: str = "checkpoints"):
    """从 URL 下载模型"""
    from tqdm import tqdm
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 目标路径
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    # 检查是否已存在
    if target_file.exists():
        print(f"\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists", "file": filename}
    
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
        
        # 提交 Volume
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\n✅ 下载成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {
            "success": True,
            "action": "downloaded",
            "file": filename,
            "type": model_type,
            "size_mb": size_mb
        }
        
    except Exception as e:
        # 清理失败的文件
        if target_file.exists():
            target_file.unlink()
        print(f"\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.function(volumes={"/models": vol})
def list_models():
    """列出所有模型"""
    print("=" * 60)
    print("📋 模型列表")
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
    
    print(f"\n{'='*60}")
    print(f"📊 共 {total} 个模型")
    
    return {"models": models, "total": total}


@app.function(volumes={"/models": vol})
def delete_model(model_type: str, filename: str):
    """删除模型"""
    print(f"🗑️ 删除模型: {model_type}/{filename}")
    
    target_file = Path(f"/models/{model_type}/{filename}")
    
    if not target_file.exists():
        print(f"   ❌ 模型不存在")
        return {"success": False, "error": "模型不存在"}
    
    try:
        target_file.unlink()
        vol.commit()
        print(f"   ✅ 已删除")
        return {"success": True}
    except Exception as e:
        print(f"   ❌ 删除失败: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# 本地入口
# =============================================================================

@app.local_entrypoint()
def main(
    action: str = "list",
    repo_id: str = "",
    url: str = "",
    filename: str = "",
    type: str = "checkpoints",
    subfolder: str = "",
    reload_url: str = "",
    no_reload: bool = False
):
    """
    模型下载器
    
    参数:
        action: hf, url, list, delete, reload
        repo_id: HuggingFace 仓库 ID
        url: 下载 URL
        filename: 文件名
        type: 模型类型
        subfolder: HuggingFace 子文件夹
        reload_url: 热加载 API URL
        no_reload: 跳过热加载
    """
    print(f"\n{'='*60}")
    print("Z-Image-Turbo 模型管理")
    print(f"{'='*60}")
    
    result = None
    need_reload = False
    
    if action == "hf":
        # 从 HuggingFace 下载
        if not repo_id or not filename:
            print("❌ 请提供 --repo-id 和 --filename")
            print("\n示例:")
            print("  modal run download_models.py --action=hf \\")
            print("    --repo-id=Comfy-Org/z_image_turbo \\")
            print("    --filename=qwen_3_4b.safetensors \\")
            print("    --type=text_encoders")
            return
        
        result = download_from_hf.remote(repo_id, filename, type, subfolder)
        need_reload = result.get("action") == "downloaded"
        
    elif action == "url":
        # 从 URL 下载
        if not url or not filename:
            print("❌ 请提供 --url 和 --filename")
            print("\n示例:")
            print("  modal run download_models.py --action=url \\")
            print("    --url=https://example.com/model.safetensors \\")
            print("    --filename=my_model.safetensors \\")
            print("    --type=checkpoints")
            return
        
        result = download_from_url.remote(url, filename, type)
        need_reload = result.get("action") == "downloaded"
        
    elif action == "list":
        # 列出模型
        list_models.remote()
        return
        
    elif action == "delete":
        # 删除模型
        if not filename:
            print("❌ 请提供 --filename 和 --type")
            return
        result = delete_model.remote(type, filename)
        need_reload = result.get("success", False)
        
    elif action == "reload":
        # 手动触发热加载
        trigger_reload(reload_url)
        return
        
    else:
        print(f"❌ 未知操作: {action}")
        print("支持: hf, url, list, delete, reload")
        return
    
    # 自动热加载
    if need_reload and not no_reload:
        print("\n" + "=" * 60)
        trigger_reload(reload_url)
    
    # 打印结果
    if result:
        if result.get("success"):
            print(f"\n✅ 操作完成")
        else:
            print(f"\n❌ 操作失败: {result.get('error')}")
