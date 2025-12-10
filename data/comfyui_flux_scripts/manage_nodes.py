"""
Custom Nodes 管理工具
提供动态安装、卸载、列举自定义节点的功能
支持持久化到 Volume，无需修改主应用
"""

import modal
import subprocess
import os
import json
from datetime import datetime
from pathlib import Path
from config import get_volume

# 复用主应用的 Volume
volume = get_volume()

# 管理工具镜像 - 只需基础依赖
manage_image = (
    modal.Image.debian_slim()
    .apt_install("git", "wget")
    .pip_install("requests", "huggingface_hub")
)

app = modal.App("comfyui-node-manager", image=manage_image)


@app.function(
    volumes={"/cache": volume},
    timeout=600
)
def install_node(repo_url: str, branch: str = "main"):
    """
    安装 Custom Node 到共享 Volume
    
    Args:
        repo_url: GitHub 仓库地址，例如 "https://github.com/ltdrdata/ComfyUI-Manager.git"
        branch: Git 分支，默认 "main"
    
    Returns:
        dict: 安装结果信息
    """
    custom_nodes_path = "/cache/custom_nodes"
    os.makedirs(custom_nodes_path, exist_ok=True)
    
    node_name = repo_url.split("/")[-1].replace(".git", "")
    node_path = os.path.join(custom_nodes_path, node_name)
    
    print(f"{'='*60}")
    print(f"📦 开始安装 Custom Node: {node_name}")
    print(f"🔗 仓库地址: {repo_url}")
    print(f"🌿 分支: {branch}")
    print(f"{'='*60}\n")
    
    try:
        # 检查是否已存在
        if os.path.exists(node_path):
            print(f"⚠️  节点已存在: {node_path}")
            return {
                "success": False,
                "error": f"节点 {node_name} 已安装",
                "node_name": node_name,
                "action": "skipped"
            }
        
        # 步骤 1: 克隆仓库
        print(f"[1/4] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        
        print(f"✅ 克隆成功\n")
        
        # 步骤 2: 检查并安装依赖
        requirements_file = os.path.join(node_path, "requirements.txt")
        installed_packages = []
        
        if os.path.exists(requirements_file):
            print(f"[2/4] 发现依赖文件，开始安装...")
            
            # 读取依赖内容
            with open(requirements_file, 'r') as f:
                deps = f.read()
                print(f"📋 依赖列表:\n{deps}\n")
            
            # 安装到节点目录
            pip_cmd = ["pip", "install", "-r", requirements_file]
            pip_result = subprocess.run(
                pip_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if pip_result.returncode == 0:
                print("✅ 依赖安装成功\n")
                installed_packages = [
                    line for line in pip_result.stdout.split("\n") 
                    if "Successfully installed" in line
                ]
            else:
                print(f"⚠️  依赖安装警告:\n{pip_result.stderr}\n")
        else:
            print(f"[2/4] 无依赖文件，跳过\n")
        
        # 步骤 3: 执行自定义安装脚本（如果有）
        install_script = os.path.join(node_path, "install.py")
        if os.path.exists(install_script):
            print(f"[3/4] 发现安装脚本，执行中...")
            install_result = subprocess.run(
                ["python", install_script],
                cwd=node_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            if install_result.returncode == 0:
                print("✅ 安装脚本执行成功\n")
            else:
                print(f"⚠️  安装脚本警告:\n{install_result.stderr}\n")
        else:
            print(f"[3/4] 无安装脚本，跳过\n")
        
        # 步骤 4: 记录安装信息
        print(f"[4/4] 记录安装信息并持久化...")
        install_info = {
            "node_name": node_name,
            "repo_url": repo_url,
            "branch": branch,
            "installed_at": datetime.now().isoformat(),
            "has_requirements": os.path.exists(requirements_file),
            "has_install_script": os.path.exists(install_script),
            "installed_packages": installed_packages
        }
        
        info_file = os.path.join(node_path, ".install_info.json")
        with open(info_file, 'w') as f:
            json.dump(install_info, f, indent=2)
        
        # 提交到 Volume（关键！）
        volume.commit()
        print(f"✅ 已持久化到 Volume\n")
        
        print(f"{'='*60}")
        print(f"✅ Custom Node {node_name} 安装成功！")
        print(f"{'='*60}")
        print(f"\n⚠️  重要提示:")
        print(f"   需要重启 ComfyUI 才能加载新节点")
        print(f"\n")
        
        return {
            "success": True,
            "node_name": node_name,
            "node_path": node_path,
            "install_info": install_info,
            "action": "installed",
            "next_steps": "重启 ComfyUI 服务以加载新节点"
        }
        
    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "error": f"操作超时: {str(e)}",
            "node_name": node_name,
            "action": "timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "node_name": node_name,
            "action": "failed"
        }


@app.function(volumes={"/cache": volume})
def list_nodes():
    """列出所有已安装的自定义节点"""
    custom_nodes_path = "/cache/custom_nodes"
    nodes = []
    
    if not os.path.exists(custom_nodes_path):
        return {"nodes": [], "count": 0}
    
    for item in os.listdir(custom_nodes_path):
        item_path = os.path.join(custom_nodes_path, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # 读取安装信息
            info_file = os.path.join(item_path, ".install_info.json")
            install_info = None
            if os.path.exists(info_file):
                with open(info_file, 'r') as f:
                    install_info = json.load(f)
            
            # 统计节点文件
            py_files = list(Path(item_path).glob("*.py"))
            
            node_info = {
                "name": item,
                "path": item_path,
                "has_requirements": os.path.exists(os.path.join(item_path, "requirements.txt")),
                "has_init": os.path.exists(os.path.join(item_path, "__init__.py")),
                "py_files_count": len(py_files),
                "install_info": install_info
            }
            nodes.append(node_info)
    
    return {
        "nodes": nodes,
        "count": len(nodes)
    }


@app.function(volumes={"/cache": volume})
def uninstall_node(node_name: str):
    """卸载指定的节点"""
    import shutil
    
    node_path = f"/cache/custom_nodes/{node_name}"
    
    if not os.path.exists(node_path):
        return {
            "success": False,
            "error": f"节点 {node_name} 不存在"
        }
    
    try:
        shutil.rmtree(node_path)
        volume.commit()
        
        return {
            "success": True,
            "message": f"节点 {node_name} 已卸载",
            "note": "需要重启 ComfyUI 才能生效"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": volume})
def update_node(node_name: str):
    """更新指定节点到最新版本"""
    node_path = f"/cache/custom_nodes/{node_name}"
    
    if not os.path.exists(node_path):
        return {
            "success": False,
            "error": f"节点 {node_name} 不存在"
        }
    
    try:
        print(f"🔄 更新节点: {node_name}")
        
        # Git pull
        result = subprocess.run(
            ["git", "pull"],
            cwd=node_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"Git pull 失败: {result.stderr}")
        
        # 重新安装依赖（如果有）
        requirements_file = os.path.join(node_path, "requirements.txt")
        if os.path.exists(requirements_file):
            print(f"📦 更新依赖...")
            subprocess.run(
                ["pip", "install", "-r", requirements_file, "--upgrade"],
                timeout=300
            )
        
        # 更新安装信息
        info_file = os.path.join(node_path, ".install_info.json")
        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                install_info = json.load(f)
            
            install_info['updated_at'] = datetime.now().isoformat()
            
            with open(info_file, 'w') as f:
                json.dump(install_info, f, indent=2)
        
        volume.commit()
        
        return {
            "success": True,
            "message": f"节点 {node_name} 已更新",
            "output": result.stdout
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": volume})
def batch_install_nodes(repo_urls: list[str]):
    """批量安装多个节点"""
    results = []
    
    for repo_url in repo_urls:
        print(f"\n{'='*60}")
        print(f"处理: {repo_url}")
        print(f"{'='*60}\n")
        
        result = install_node.local(repo_url)
        results.append({
            "repo_url": repo_url,
            "result": result
        })
    
    return {
        "total": len(repo_urls),
        "results": results,
        "successful": sum(1 for r in results if r['result']['success']),
        "failed": sum(1 for r in results if not r['result']['success'])
    }


# 本地命令行入口
@app.local_entrypoint()
def main(
    action: str = "list",
    repo_url: str = "",
    node_name: str = "",
    branch: str = "main"
):
    """
    命令行入口
    
    使用示例:
    modal run manage_nodes.py --action=list
    modal run manage_nodes.py --action=install --repo-url=https://github.com/ltdrdata/ComfyUI-Manager.git
    modal run manage_nodes.py --action=update --node-name=ComfyUI-Manager
    modal run manage_nodes.py --action=uninstall --node-name=ComfyUI-Manager
    """
    if action == "list":
        result = list_nodes.remote()
        print(f"\n{'='*60}")
        print(f"已安装的 Custom Nodes: {result['count']} 个")
        print(f"{'='*60}\n")
        
        for node in result['nodes']:
            print(f"📦 {node['name']}")
            print(f"   路径: {node['path']}")
            print(f"   Python 文件: {node['py_files_count']} 个")
            
            if node['install_info']:
                print(f"   安装时间: {node['install_info']['installed_at']}")
                print(f"   仓库: {node['install_info']['repo_url']}")
                if 'updated_at' in node['install_info']:
                    print(f"   更新时间: {node['install_info']['updated_at']}")
            print()
    
    elif action == "install":
        if not repo_url:
            print("❌ 错误: 需要提供 --repo-url 参数")
            return
        
        result = install_node.remote(repo_url, branch)
        
        if result['success']:
            print(f"\n✅ 安装成功!")
            print(f"节点名称: {result['node_name']}")
            print(f"节点路径: {result['node_path']}")
            print(f"\n{result['next_steps']}")
        else:
            print(f"\n❌ 安装失败: {result['error']}")
    
    elif action == "update":
        if not node_name:
            print("❌ 错误: 需要提供 --node-name 参数")
            return
        
        result = update_node.remote(node_name)
        if result['success']:
            print(f"\n✅ {result['message']}")
        else:
            print(f"\n❌ 更新失败: {result['error']}")
    
    elif action == "uninstall":
        if not node_name:
            print("❌ 错误: 需要提供 --node-name 参数")
            return
        
        result = uninstall_node.remote(node_name)
        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"💡 {result['note']}")
        else:
            print(f"\n❌ 卸载失败: {result['error']}")
    
    else:
        print(f"❌ 未知操作: {action}")
        print("支持的操作: list, install, update, uninstall")
