"""
ComfyUI Flux 项目配置文件
包含镜像构建、密钥配置、存储卷设置
"""

import modal

# ============================================
# 镜像配置
# ============================================

def build_base_image():
    """构建基础 Docker 镜像"""
    image = (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install("git")
        .pip_install("fastapi[standard]==0.115.4")
        .pip_install("comfy-cli==1.5.1")
        .run_commands("python -m pip uninstall llama-cpp-python")
        .run_commands("pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124")
        .pip_install("requests==2.32.3")
        .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
    )
    return image


def install_custom_nodes(image):
    """安装 ComfyUI 自定义节点"""
    image = image.run_commands(
        "comfy node install --fast-deps was-node-suite-comfyui@1.0.2",
        "git clone https://github.com/judian17/ComfyUI-joycaption-beta-one-GGUF.git /root/comfy/ComfyUI/custom_nodes/ComfyUI-joycaption-beta-one-GGUF"
    )
    return image


# ============================================
# 密钥配置
# ============================================

def get_hf_secret():
    """获取 HuggingFace Secret"""
    return modal.Secret.from_name("huggingface-secret")


# ============================================
# 存储卷配置
# ============================================

def get_volume():
    """获取持久化存储卷"""
    return modal.Volume.from_name("hf-hub-cache", create_if_missing=True)


# ============================================
# 应用配置
# ============================================

APP_NAME = "example-comfyapp"
GPU_TYPE = "L40S"
MAX_CONTAINERS = 1
MAX_CONCURRENT_INPUTS = 10
SCALEDOWN_WINDOW = 300
API_PORT = 8000
