"""
=============================================================================
ComfyUI 添加自定义节点
=============================================================================
从 Git 仓库安装自定义节点到 ComfyUI

使用方法:
    modal run add_node.py
=============================================================================
"""
import modal
import subprocess
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"

# 脚本变量 - 每次执行时填写
NODE_REPO_URL = "{{NODE_REPO_URL:节点 Git 仓库 URL:https://github.com/ltdrdata/ComfyUI-Manager.git}}"
NODE_BRANCH = "{{NODE_BRANCH:分支:main}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("requests")
)

app = modal.App(f"{APP_NAME}-node-installer", image=image)


@app.function(
    volumes={"/cache": vol},
    timeout=600
)
def install_node():
    """安装自定义节点到共享 Volume"""
    repo_url = NODE_REPO_URL
    branch = NODE_BRANCH
    
    node_name = repo_url.split("/")[-1].replace(".git", "")
    node_path = f"/cache/custom_nodes/{node_name}"
    
    print(f"{'='*60}")
    print(f"📦 安装 Custom Node: {node_name}")
    print(f"{'='*60}")
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"Volume: {VOLUME_NAME}")
    
    # 确保目录存在
    Path("/cache/custom_nodes").mkdir(parents=True, exist_ok=True)
    
    # 检查是否已存在
    if Path(node_path).exists():
        print(f"\n⚠️ 节点已存在: {node_name}")
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
                vol.commit()
                print(f"✅ 节点更新成功")
                return {
                    "success": True,
                    "action": "updated",
                    "node_name": node_name,
                    "message": "节点已更新，请重启 ComfyUI 服务"
                }
            else:
                print(f"⚠️ 更新失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 更新出错: {e}")
    
    try:
        # 步骤 1: 克隆仓库
        print("\n[1/3] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        print("✓ 克隆成功")
        
        # 步骤 2: 检查依赖文件
        requirements_file = f"{node_path}/requirements.txt"
        has_req = Path(requirements_file).exists()
        
        if has_req:
            print("\n[2/3] 检测到依赖文件...")
            print("   ℹ️ 依赖将在 ComfyUI 启动时自动安装")
            with open(requirements_file, 'r') as f:
                deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if deps:
                    print(f"   📦 依赖项: {', '.join(deps[:5])}" + ("..." if len(deps) > 5 else ""))
        else:
            print("\n[2/3] 无依赖文件")
        
        # 步骤 3: 记录安装信息
        print("\n[3/3] 记录安装信息...")
        install_info = {
            "node_name": node_name,
            "repo_url": repo_url,
            "branch": branch,
            "installed_at": datetime.now().isoformat(),
            "has_requirements": has_req
        }
        
        info_file = f"{node_path}/.install_info.json"
        with open(info_file, 'w') as f:
            json.dump(install_info, f, indent=2)
        
        vol.commit()
        print("✓ 已保存到 Volume")
        
        print(f"\n{'='*60}")
        print(f"✅ Custom Node {node_name} 安装成功!")
        print(f"{'='*60}")
        
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
        if Path(node_path).exists():
            import shutil
            shutil.rmtree(node_path)
        return {"success": False, "error": str(e), "node_name": node_name}


@app.local_entrypoint()
def main():
    print(f"\n{'='*60}")
    print(f"ComfyUI 添加自定义节点 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = install_node.remote()
    
    if result.get("success"):
        print(f"\n✅ 操作完成")
        print(f"\n📌 下一步: 重启 ComfyUI 服务使节点生效")
        print(f"   运行: modal app stop {APP_NAME}")
        print(f"   然后访问 ComfyUI URL，服务会自动重启并加载节点")
    else:
        print(f"\n❌ 失败: {result.get('error')}")
