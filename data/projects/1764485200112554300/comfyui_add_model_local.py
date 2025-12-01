"""
=============================================================================
ComfyUI 上传本地模型
=============================================================================
将本地模型文件上传到 ComfyUI 的模型目录

此脚本会显示上传命令，请在项目操作面板中使用"上传模型"功能执行
或手动执行生成的 modal volume put 命令
=============================================================================
"""
import os
from pathlib import Path

# =============================================
# 配置参数
# =============================================
LOCAL_MODEL_PATH = "D:\\ai\\sd-webui-aki\\sd-webui-aki-v4.6.1\\models\\Lora\\全网首发 _ 国风山水-苍茫云天_v1.0.safetensors"
MODEL_FILENAME = ""
MODEL_TYPE = "loras"
VOLUME_NAME = "z-image-cache"

# =============================================
# 模型类型和目录映射
# =============================================
MODEL_DIRS = {
    "checkpoints": "/models/checkpoints",
    "loras": "/models/loras",
    "vae": "/models/vae",
    "clip": "/models/clip",
    "text_encoders": "/models/text_encoders",
    "diffusion_models": "/models/diffusion_models",
    "controlnet": "/models/controlnet",
    "upscale_models": "/models/upscale_models",
    "embeddings": "/models/embeddings",
}

# =============================================
# 生成上传命令
# =============================================
local_path = LOCAL_MODEL_PATH
filename = MODEL_FILENAME if MODEL_FILENAME else Path(local_path).name
model_type = MODEL_TYPE
remote_dir = MODEL_DIRS.get(model_type, MODEL_DIRS["checkpoints"])
remote_path = f"{remote_dir}/{filename}"

print("=" * 60)
print("📤 ComfyUI 本地模型上传")
print("=" * 60)
print(f"本地文件: {local_path}")
print(f"目标路径: {VOLUME_NAME}:{remote_path}")
print(f"模型类型: {model_type}")
print("=" * 60)
print()

# 检查本地文件是否存在
if os.path.exists(local_path):
    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"✅ 本地文件存在，大小: {size_mb:.1f} MB")
else:
    print(f"❌ 本地文件不存在: {local_path}")
    exit(1)

print()
print("请执行以下命令上传文件:")
print()
print(f'  modal volume put {VOLUME_NAME} "{local_path}" {remote_path}')
print()
print("=" * 60)
