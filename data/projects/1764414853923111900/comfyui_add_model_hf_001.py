"""
=============================================================================
ComfyUI 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到 ComfyUI 的模型目录

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
import subprocess
from pathlib import Path

# 配置参数（由模板变量填充）
HF_REPO_ID = "Comfy-Org/z_image_turbo"
HF_FILENAME = "split_files/text_encoders/qwen_3_4b.safetensors"
MODEL_TYPE = " text_encoders"
VOLUME_NAME = "comfyui-cache"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# HuggingFace Secret (可选)
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# 镜像配置
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4", "requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("comfyui-add-model", image=image)

# 模型类型和目录映射
MODEL_DIRS = {
    "checkpoints": "/cache/models/checkpoints",
    "loras": "/cache/models/loras",
    "vae": "/cache/models/vae",
    "clip": "/cache/models/clip",
    "controlnet": "/cache/models/controlnet",
    "upscale_models": "/cache/models/upscale_models",
    "embeddings": "/cache/models/embeddings",
}


@app.function(
    volumes={"/cache": vol},
    secrets=[hf_secret] if hf_secret else [],
    timeout=1800  # 30分钟超时
)
def add_model():
    """
    从 HuggingFace 下载模型
    """
    from huggingface_hub import hf_hub_download
    
    repo_id = HF_REPO_ID
    filename = HF_FILENAME
    model_type = MODEL_TYPE
    
    hf_token = os.getenv("HF_TOKEN")
    local_name = filename.split("/")[-1]
    model_dir = MODEL_DIRS.get(model_type, MODEL_DIRS["checkpoints"])
    final_path = f"{model_dir}/{local_name}"
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"保存为: {local_name}")
    print(f"{'='*60}\n")
    
    # 检查是否已存在
    if os.path.exists(final_path):
        print(f"⚠️ 模型已存在: {final_path}")
        return {"success": False, "error": "模型已存在", "path": final_path}
    
    try:
        # 确保目录存在
        os.makedirs(model_dir, exist_ok=True)
        
        # 下载模型
        print("⬇️ 开始下载...")
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/cache/hf_cache",
            token=hf_token
        )
        
        # 创建软链接
        subprocess.run(f"ln -s {cached_path} {final_path}", shell=True, check=True)
        
        # 提交到 Volume
        vol.commit()
        
        print(f"\n✅ 模型下载成功!")
        print(f"路径: {final_path}")
        print(f"\n⚠️ 重启 ComfyUI 后生效")
        
        return {
            "success": True,
            "path": final_path,
            "model_type": model_type,
            "source": f"hf://{repo_id}/{filename}"
        }
        
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    """
    本地入口
    """
    print(f"\n{'='*60}")
    print("ComfyUI 添加模型 (HuggingFace)")
    print(f"{'='*60}")
    print(f"仓库: {HF_REPO_ID}")
    print(f"文件: {HF_FILENAME}")
    print(f"类型: {MODEL_TYPE}")
    print(f"{'='*60}\n")
    
    result = add_model.remote()
    
    if result.get("success"):
        print(f"\n✅ 下载完成: {result.get('path')}")
    else:
        print(f"\n❌ 下载失败: {result.get('error')}")
