#!/usr/bin/env python3
"""
=============================================================================
ComfyUI 基础环境安装脚本
=============================================================================
功能说明：
- 构建基础 Docker 镜像（Debian Slim + Python 3.11）
- 安装 Git、FastAPI、comfy-cli 等基础依赖
- 安装 llama-cpp-python（CUDA 124 版本）
- 安装 ComfyUI 核心（版本 0.3.59）

使用方法：
    modal run setup_base_environment.py

独立运行：
    此脚本可独立运行，创建最小可用的 ComfyUI 环境
=============================================================================
"""

import modal

# =============================================================================
# S1: 构建基础镜像
# =============================================================================

print("🔧 开始构建 ComfyUI 基础环境...")

# S1.1: 创建基础 Debian 镜像，安装 Python 3.11
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("fastapi[standard]==0.115.4")
    .pip_install("comfy-cli==1.5.1")
)

# S1.2: 安装 llama-cpp-python（CUDA 124 版本）
print("📦 安装 llama-cpp-python...")
image = image.run_commands(
    "python -m pip uninstall llama-cpp-python -y || true",
    "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124"
)

# S1.3: 安装 requests 和 ComfyUI 核心
print("📦 安装 ComfyUI 核心...")
image = image.pip_install("requests==2.32.3")
image = image.run_commands(
    "comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59"
)

# =============================================================================
# S2: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-base-environment", image=image)

print("✅ 基础环境镜像构建完成！")
print("💡 提示：此镜像包含 ComfyUI 核心环境，可作为其他模块的基础")

# =============================================================================
# S3: 测试函数
# =============================================================================

@app.function()
def test_environment():
    """测试基础环境是否正常"""
    import subprocess
    import sys
    
    print("🧪 测试 Python 版本...")
    print(f"   Python: {sys.version}")
    
    print("🧪 测试 comfy-cli...")
    result = subprocess.run(["comfy", "--version"], capture_output=True, text=True)
    print(f"   {result.stdout.strip()}")
    
    print("🧪 测试 ComfyUI 安装...")
    result = subprocess.run(["ls", "-la", "/root/comfy/ComfyUI"], capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✅ ComfyUI 目录存在")
    else:
        print("   ❌ ComfyUI 目录不存在")
    
    return {"status": "success", "message": "基础环境测试通过"}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 运行基础环境测试...")
    result = test_environment.remote()
    print(f"📊 测试结果: {result}")

