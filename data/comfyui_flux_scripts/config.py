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

# GPU 配置选项
# 可选: "T4", "A10G", "A100", "L4", "L40S", "H100" 等
GPU_TYPE = "L40S"

# GPU 数量（多GPU并行）
GPU_COUNT = 1

# 容器配置
MAX_CONTAINERS = 1  # 最大并发容器数
MAX_CONCURRENT_INPUTS = 10  # 每个容器的最大并发请求
CONTAINER_IDLE_TIMEOUT = 300  # 容器空闲超时（秒）
SCALEDOWN_WINDOW = 300  # 缩容窗口（秒）

# 内存配置（MB）
MEMORY_SIZE = 16384  # 16GB

# 超时配置（秒）
STARTUP_TIMEOUT = 180  # 启动超时
REQUEST_TIMEOUT = 1200  # 请求超时

# 网络配置
API_PORT = 8000

# 重试配置
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

# 日志配置
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR


# ============================================
# GPU 配置辅助函数
# ============================================

def get_gpu_config(gpu_type: str = None, gpu_count: int = None):
    """
    获取 GPU 配置
    
    Args:
        gpu_type: GPU 类型，如果为 None 则使用默认配置
        gpu_count: GPU 数量，如果为 None 则使用默认配置
    
    Returns:
        str or modal.gpu.A100 等 GPU 对象
    """
    gpu = gpu_type or GPU_TYPE
    count = gpu_count or GPU_COUNT
    
    if count == 1:
        return gpu
    else:
        # 多 GPU 配置
        return f"{gpu}:{count}"


def get_memory_config():
    """获取内存配置（MB）"""
    return MEMORY_SIZE


def get_timeout_config():
    """获取超时配置字典"""
    return {
        "startup_timeout": STARTUP_TIMEOUT,
        "request_timeout": REQUEST_TIMEOUT,
        "container_idle_timeout": CONTAINER_IDLE_TIMEOUT
    }


# ============================================
# 环境配置辅助函数
# ============================================

def get_env_vars():
    """获取环境变量配置"""
    return {
        "COMFYUI_PORT": str(API_PORT),
        "LOG_LEVEL": LOG_LEVEL,
        "PYTHONUNBUFFERED": "1"
    }


def is_production():
    """检查是否为生产环境"""
    import os
    return os.getenv("MODAL_ENVIRONMENT", "dev") == "production"


# ============================================
# 预设配置
# ============================================

# 快速开发配置
DEV_CONFIG = {
    "gpu": "T4",
    "max_containers": 1,
    "memory": 8192,
    "timeout": 600
}

# 生产环境配置
PROD_CONFIG = {
    "gpu": "A100",
    "max_containers": 5,
    "memory": 32768,
    "timeout": 1800
}

# 高性能配置
HIGH_PERF_CONFIG = {
    "gpu": "H100",
    "max_containers": 3,
    "memory": 65536,
    "timeout": 3600
}


def get_preset_config(preset: str = "default"):
    """
    获取预设配置
    
    Args:
        preset: 预设名称 ("dev", "prod", "high_perf", "default")
    
    Returns:
        dict: 配置字典
    """
    presets = {
        "dev": DEV_CONFIG,
        "prod": PROD_CONFIG,
        "high_perf": HIGH_PERF_CONFIG,
        "default": {
            "gpu": GPU_TYPE,
            "max_containers": MAX_CONTAINERS,
            "memory": MEMORY_SIZE,
            "timeout": REQUEST_TIMEOUT
        }
    }
    
    return presets.get(preset, presets["default"])
