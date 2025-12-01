#!/usr/bin/env python3
"""
=============================================================================
ComfyUI 自定义节点安装脚本
=============================================================================
功能说明：
- 安装 was-node-suite-comfyui 扩展（版本 1.0.2）
- 克隆安装 ComfyUI-joycaption-beta-one-GGUF 节点
- 将节点持久化存储到 Volume /cache/custom_nodes

使用方法：
    modal run install_custom_nodes.py

独立运行：
    此脚本可独立运行，基于基础环境添加自定义节点
=============================================================================
"""

import subprocess
from pathlib import Path
import modal

# =============================================================================
# S1: 构建带自定义节点的镜像
# =============================================================================

print("🔧 开始安装 ComfyUI 自定义节点...")

# 基础镜像（与 setup_base_environment.py 相同的基础环境）
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("fastapi[standard]==0.115.4")
    .pip_install("comfy-cli==1.5.1")
    .run_commands(
        "python -m pip uninstall llama-cpp-python -y || true",
        "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124"
    )
    .pip_install("requests==2.32.3")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
)

# =============================================================================
# S2: 自定义节点安装函数
# =============================================================================

def install_nodes():
    """安装自定义节点到 Volume 持久化存储"""
    import os
    
    print("📦 S2.1: 安装 was-node-suite-comfyui...")
    try:
        subprocess.run(
            "comfy node install --fast-deps was-node-suite-comfyui@1.0.2",
            shell=True,
            check=True
        )
        print("   ✅ was-node-suite-comfyui 安装成功")
    except Exception as e:
        print(f"   ❌ was-node-suite-comfyui 安装失败: {e}")
    
    print("📦 S2.2: 克隆 ComfyUI-joycaption-beta-one-GGUF...")
    try:
        subprocess.run(
            "git clone https://github.com/judian17/ComfyUI-joycaption-beta-one-GGUF.git /root/comfy/ComfyUI/custom_nodes/ComfyUI-joycaption-beta-one-GGUF",
            shell=True,
            check=True
        )
        print("   ✅ ComfyUI-joycaption-beta-one-GGUF 安装成功")
    except Exception as e:
        print(f"   ❌ ComfyUI-joycaption-beta-one-GGUF 安装失败: {e}")
    
    # S2.3: 将节点复制到持久化存储
    print("📦 S2.3: 持久化自定义节点到 Volume...")
    custom_nodes_dir = Path("/root/comfy/ComfyUI/custom_nodes")
    cache_nodes_dir = Path("/cache/custom_nodes")
    
    cache_nodes_dir.mkdir(parents=True, exist_ok=True)
    
    if custom_nodes_dir.exists():
        for node_dir in custom_nodes_dir.iterdir():
            if node_dir.is_dir() and not node_dir.name.startswith('.'):
                target_dir = cache_nodes_dir / node_dir.name
                if not target_dir.exists():
                    subprocess.run(
                        f"cp -r {node_dir} {target_dir}",
                        shell=True,
                        check=False
                    )
                    print(f"   ✅ 已持久化: {node_dir.name}")
                else:
                    print(f"   ⏭️  已存在: {node_dir.name}")
    
    print("✅ 自定义节点安装完成！")


# S2.4: 在镜像构建时安装节点
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

image = image.run_function(
    install_nodes,
    volumes={"/cache": vol}
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-custom-nodes", image=image)

print("✅ 自定义节点镜像构建完成！")
print("💡 提示：节点已持久化到 Volume，后续部署可直接使用")


@app.function(volumes={"/cache": vol})
def list_installed_nodes():
    """列出已安装的自定义节点"""
    import os
    
    nodes_dir = Path("/root/comfy/ComfyUI/custom_nodes")
    cache_nodes_dir = Path("/cache/custom_nodes")
    
    print("📋 ComfyUI 自定义节点列表:")
    print("\n=== 当前环境节点 ===")
    if nodes_dir.exists():
        for item in nodes_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                print(f"   ✅ {item.name}")
    
    print("\n=== Volume 持久化节点 ===")
    if cache_nodes_dir.exists():
        for item in cache_nodes_dir.iterdir():
            if item.is_dir():
                print(f"   💾 {item.name}")
    
    return {"status": "success"}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 列出已安装的自定义节点...")
    list_installed_nodes.remote()

