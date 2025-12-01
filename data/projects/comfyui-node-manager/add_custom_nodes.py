"""
=============================================================================
ComfyUI 添加自定义节点
=============================================================================
将指定的 Git 仓库克隆到 ComfyUI 的 custom_nodes 目录

使用方法:
    modal run add_custom_nodes.py --action=install --repo-url=https://github.com/xxx/xxx.git --branch=main
    modal run add_custom_nodes.py --action=list
    modal run add_custom_nodes.py --action=remove --node-name=xxx

重要说明:
    添加节点后需要重启 ComfyUI 服务才能生效:
    1. 运行: modal app stop comfyui-app
    2. 访问 ComfyUI URL，服务会自动重启并加载新节点
=============================================================================
"""
import modal
import os
import subprocess
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Volume 名称 - 必须与 comfyui_app.py 使用相同的 Volume
VOLUME_NAME = "comfyui-cache"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 包含 git 的镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("requests")
)

app = modal.App("comfyui-node-manager", image=image)

# Custom Nodes 存储路径
CUSTOM_NODES_PATH = "/cache/custom_nodes"


@app.function(
    volumes={"/cache": vol},
    timeout=600
)
def install_node(repo_url: str, branch: str = "main"):
    """
    安装 Custom Node 到共享 Volume
    """
    node_name = repo_url.split("/")[-1].replace(".git", "")
    node_path = f"{CUSTOM_NODES_PATH}/{node_name}"
    
    print(f"{'='*60}")
    print(f"📦 安装 Custom Node: {node_name}")
    print(f"{'='*60}")
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"{'='*60}\n")
    
    # 确保目录存在
    os.makedirs(CUSTOM_NODES_PATH, exist_ok=True)
    
    # 检查是否已存在
    if os.path.exists(node_path):
        print(f"⚠️ 节点已存在: {node_name}")
        print("正在更新节点...")
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=node_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"✅ 节点更新成功")
            else:
                print(f"⚠️ 更新失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 更新出错: {e}")
        
        vol.commit()
        return {
            "success": True,
            "action": "updated",
            "node_name": node_name,
            "message": "节点已更新，请重启 ComfyUI 服务"
        }
    
    try:
        # 步骤 1: 克隆仓库
        print("[1/3] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        print("✓ 克隆成功\n")
        
        # 步骤 2: 检查依赖文件
        requirements_file = f"{node_path}/requirements.txt"
        if os.path.exists(requirements_file):
            print("[2/3] 检测到依赖文件...")
            print("   ℹ️ 依赖将在 ComfyUI 启动时自动安装")
            with open(requirements_file, 'r') as f:
                deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if deps:
                    print(f"   📦 依赖项: {', '.join(deps[:5])}" + ("..." if len(deps) > 5 else ""))
            print()
        else:
            print("[2/3] 无依赖文件\n")
        
        # 步骤 3: 记录安装信息并持久化
        print("[3/3] 记录安装信息并持久化...")
        install_info = {
            "node_name": node_name,
            "repo_url": repo_url,
            "branch": branch,
            "installed_at": datetime.now().isoformat(),
            "has_requirements": os.path.exists(requirements_file)
        }
        
        info_file = f"{node_path}/.install_info.json"
        with open(info_file, 'w') as f:
            json.dump(install_info, f, indent=2)
        
        vol.commit()
        print("✓ 已保存到 Volume\n")
        
        print(f"{'='*60}")
        print(f"✅ Custom Node {node_name} 安装成功!")
        print(f"{'='*60}")
        print(f"\n📌 下一步:")
        print(f"   1. 运行: modal app stop comfyui-app")
        print(f"   2. 访问 ComfyUI URL，服务会自动重启")
        print(f"   3. 重启时会自动链接节点并安装依赖")
        
        return {
            "success": True,
            "action": "installed",
            "node_name": node_name,
            "message": "节点安装成功，请重启 ComfyUI 服务"
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "操作超时", "node_name": node_name}
    except Exception as e:
        # 清理失败的安装
        if os.path.exists(node_path):
            shutil.rmtree(node_path)
        return {"success": False, "error": str(e), "node_name": node_name}


@app.function(
    volumes={"/cache": vol},
    timeout=60
)
def list_nodes():
    """
    列出已安装的节点
    """
    print("=" * 60)
    print("📋 已安装的 Custom Nodes")
    print("=" * 60)
    
    nodes = []
    cache_nodes = Path(CUSTOM_NODES_PATH)
    
    if cache_nodes.exists():
        for node_dir in cache_nodes.iterdir():
            if node_dir.is_dir():
                # 尝试读取安装信息
                info_file = node_dir / ".install_info.json"
                if info_file.exists():
                    info = json.loads(info_file.read_text())
                else:
                    info = {"node_name": node_dir.name}
                
                nodes.append(info)
                print(f"\n📦 {info.get('node_name', node_dir.name)}")
                if info.get('repo_url'):
                    print(f"   仓库: {info['repo_url']}")
                if info.get('installed_at'):
                    print(f"   安装时间: {info['installed_at']}")
    else:
        print("ℹ️ 暂无自定义节点")
    
    print(f"\n{'='*60}")
    print(f"总计: {len(nodes)} 个节点")
    
    return {"success": True, "nodes": nodes, "count": len(nodes)}


@app.function(
    volumes={"/cache": vol},
    timeout=60
)
def remove_node(node_name: str):
    """
    删除指定的节点
    """
    node_path = Path(CUSTOM_NODES_PATH) / node_name
    
    print(f"🗑️ 删除节点: {node_name}")
    
    if not node_path.exists():
        print(f"❌ 节点不存在: {node_name}")
        return {"success": False, "error": f"节点不存在: {node_name}"}
    
    try:
        shutil.rmtree(node_path)
        vol.commit()
        print(f"✅ 节点已删除: {node_name}")
        print(f"\n📌 请重启 ComfyUI 服务使更改生效")
        return {"success": True, "message": f"节点 {node_name} 已删除"}
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main(
    action: str = "list",
    repo_url: str = "",
    branch: str = "main",
    node_name: str = ""
):
    """
    本地入口 - 支持命令行参数
    
    使用方法:
        modal run add_custom_nodes.py --action=install --repo-url=https://github.com/xxx/xxx.git
        modal run add_custom_nodes.py --action=list
        modal run add_custom_nodes.py --action=remove --node-name=xxx
    """
    print(f"\n{'='*60}")
    print("ComfyUI Custom Nodes 管理")
    print(f"{'='*60}")
    print(f"操作: {action}")
    
    if action == "install":
        if not repo_url:
            print("❌ 错误: 请提供 --repo-url 参数")
            return
        print(f"仓库: {repo_url}")
        print(f"分支: {branch}")
        print(f"{'='*60}\n")
        result = install_node.remote(repo_url, branch)
        
    elif action == "list":
        print(f"{'='*60}\n")
        result = list_nodes.remote()
        
    elif action == "remove":
        if not node_name:
            print("❌ 错误: 请提供 --node-name 参数")
            return
        print(f"节点: {node_name}")
        print(f"{'='*60}\n")
        result = remove_node.remote(node_name)
        
    else:
        print(f"❌ 未知操作: {action}")
        print("支持的操作: install, list, remove")
        return
    
    if result.get("success"):
        print(f"\n✅ 操作完成")
    else:
        print(f"\n❌ 操作失败: {result.get('error')}")

