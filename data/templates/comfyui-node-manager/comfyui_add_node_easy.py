"""
=============================================================================
ComfyUI 添加自定义节点
=============================================================================
将指定的 Git 仓库克隆到 ComfyUI 的 custom_nodes 目录

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime

# 配置参数（由模板变量填充）
GIT_REPO_URL = "https://github.com/yolain/ComfyUI-Easy-Use.git"
BRANCH = "main"
VOLUME_NAME = "comfyui-cache"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 包含 git 的镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("requests")
)

app = modal.App("comfyui-add-node", image=image)

# Custom Nodes 存储路径
CUSTOM_NODES_PATH = "/cache/custom_nodes"


@app.function(
    volumes={"/cache": vol},
    timeout=600
)
def install_node():
    """
    安装 Custom Node 到共享 Volume
    """
    repo_url = GIT_REPO_URL
    branch = BRANCH
    
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
            "node_name": node_name
        }
    
    try:
        # 步骤 1: 克隆仓库
        print("[1/4] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        print("✓ 克隆成功\n")
        
        # 步骤 2: 检查依赖文件（依赖将在 ComfyUI 启动时自动安装）
        requirements_file = f"{node_path}/requirements.txt"
        if os.path.exists(requirements_file):
            print("[2/3] 检测到依赖文件...")
            print("   ℹ️ 依赖将在 ComfyUI 启动时自动安装")
            # 读取依赖列表供参考
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
        print(f"\n📌 后续步骤:")
        print(f"   1. 运行: modal app stop comfyui-app")
        print(f"   2. 访问 ComfyUI URL，服务会自动重启")
        print(f"   3. 重启时会自动链接节点并安装依赖")
        
        return {
            "success": True,
            "action": "installed",
            "node_name": node_name,
            "node_path": node_path,
            "install_info": install_info
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "操作超时", "node_name": node_name}
    except Exception as e:
        # 清理失败的安装
        if os.path.exists(node_path):
            shutil.rmtree(node_path)
        return {"success": False, "error": str(e), "node_name": node_name}


@app.local_entrypoint()
def main():
    """
    本地入口
    """
    print(f"\n{'='*60}")
    print("ComfyUI 添加自定义节点")
    print(f"{'='*60}")
    print(f"仓库: {GIT_REPO_URL}")
    print(f"分支: {BRANCH}")
    print(f"{'='*60}\n")
    
    result = install_node.remote()
    
    if result.get("success"):
        print(f"\n✅ 操作完成: {result.get('action')}")
    else:
        print(f"\n❌ 操作失败: {result.get('error')}")
