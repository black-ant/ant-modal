"""
=============================================================================
ComfyUI 添加模型 (本地上传)
=============================================================================
从本地上传模型文件到共享 Volume

使用方法:
    modal run add_model_local.py --local-path=./model.safetensors --type=checkpoints
=============================================================================
"""
import modal
from pathlib import Path
import shutil

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"

# 脚本变量 - 每次执行时填写
LOCAL_FILE_PATH = "{{LOCAL_FILE_PATH:本地文件路径:./model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:checkpoints}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-local-uploader", image=image)


@app.function(volumes={"/cache": vol}, timeout=3600)
def upload_model(local_path: str, model_type: str):
    """将本地模型上传到 Volume"""
    
    print(f"{'='*60}")
    print(f"📤 上传本地模型到 Volume")
    print(f"{'='*60}")
    print(f"本地文件: {local_path}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 获取文件名
    filename = Path(local_path).name
    
    # 目标路径
    target_dir = Path(f"/cache/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    if target_file.exists():
        print(f"\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\n⏳ 上传中...")
        
        # 从挂载点复制文件到 Volume
        source_file = Path(local_path)
        if not source_file.exists():
            raise Exception(f"本地文件不存在: {local_path}")
        
        shutil.copy2(str(source_file), str(target_file))
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\n✅ 上传成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "uploaded", "size_mb": size_mb, "filename": filename}
        
    except Exception as e:
        # 清理失败的上传
        if target_file.exists():
            target_file.unlink()
        print(f"\n❌ 上传失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main(local_path: str = LOCAL_FILE_PATH, type: str = MODEL_TYPE):
    """
    本地入口
    
    使用方法:
        modal run add_model_local.py --local-path=./model.safetensors --type=checkpoints
    """
    print(f"\n{'='*60}")
    print(f"ComfyUI 上传本地模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    # 验证本地文件存在
    if not Path(local_path).exists():
        print(f"\n❌ 错误: 本地文件不存在: {local_path}")
        return
    
    # 创建文件挂载
    print(f"准备挂载本地文件...")
    local_file = Path(local_path).resolve()
    
    # 使用 Mount 将本地文件挂载到容器
    mount = modal.Mount.from_local_file(
        local_path=str(local_file),
        remote_path=f"/tmp/{local_file.name}"
    )
    
    # 运行上传函数，传入挂载后的路径
    with mount:
        result = upload_model.remote(f"/tmp/{local_file.name}", type)
    
    if result.get("success"):
        if result.get("action") == "uploaded":
            print(f"\n✅ 模型上传完成: {result.get('filename')}")
            print(f"\n📌 下一步: 重启 ComfyUI 服务使模型生效")
            print(f"   运行: modal app stop {APP_NAME}")
        else:
            print(f"\n✅ 模型已存在，无需上传")
    else:
        print(f"\n❌ 失败: {result.get('error')}")
