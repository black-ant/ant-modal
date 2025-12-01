"""
UI 服务模块
提供 ComfyUI 交互式 Web 界面
"""

import subprocess
from pathlib import Path


def link_custom_nodes():
    """链接持久化的自定义节点"""
    print("🔗 链接持久化的自定义节点...")
    cache_custom_nodes = Path("/cache/custom_nodes")
    comfy_custom_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    
    if cache_custom_nodes.exists():
        for node_dir in cache_custom_nodes.iterdir():
            if node_dir.is_dir():
                link_path = comfy_custom_nodes / node_dir.name
                if not link_path.exists() and not link_path.is_symlink():
                    subprocess.run(
                        f"ln -s {node_dir} {link_path}",
                        shell=True,
                        check=False
                    )
                    print(f"   ✅ 已链接: {node_dir.name}")


def start_ui_server(port=8000):
    """启动 ComfyUI UI 服务器"""
    print(f"🌐 启动ComfyUI交互式Web界面，端口: {port}...")
    
    # 链接自定义节点
    link_custom_nodes()
    
    # 启动服务
    subprocess.Popen(
        f"comfy launch -- --listen 0.0.0.0 --port {port}",
        shell=True
    )
