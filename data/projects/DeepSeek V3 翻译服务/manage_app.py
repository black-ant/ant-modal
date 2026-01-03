"""
=============================================================================
Z-Image-Turbo 应用管理器
=============================================================================
管理 Z-Image-Turbo 应用的部署、重启、状态检查

使用方法:
    # 检查状态
    modal run manage_app.py --action=status
    
    # 重启应用 (停止后重新部署)
    modal run manage_app.py --action=restart
    
    # 强制重新部署
    modal run manage_app.py --action=redeploy
    
    # 停止应用
    modal run manage_app.py --action=stop
    
    # 查看日志
    modal run manage_app.py --action=logs
=============================================================================
"""
import modal
import subprocess
import time
import os

app = modal.App("z-image-manager")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

APP_NAME = "z-image-turbo"


@app.function(image=image)
def check_health(url: str):
    """检查应用健康状态"""
    import requests
    
    try:
        response = requests.get(url, timeout=10)
        return {
            "status": "running",
            "code": response.status_code,
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {"status": "stopped", "url": url}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_modal_command(cmd: list, capture: bool = True):
    """运行 Modal CLI 命令"""
    print(f"   执行: {' '.join(cmd)}")
    
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    else:
        result = subprocess.run(cmd)
        return result


def stop_app():
    """停止应用"""
    print(f"\n🛑 停止 {APP_NAME}...")
    result = run_modal_command(["modal", "app", "stop", APP_NAME])
    
    if result.returncode == 0:
        print("   ✅ 应用已停止")
        return True
    else:
        if "not found" in result.stderr.lower():
            print("   ℹ️ 应用未运行")
            return True
        print(f"   ⚠️ {result.stderr}")
        return False


def deploy_app():
    """部署应用"""
    print(f"\n🚀 部署 {APP_NAME}...")
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "z_image_app.py")
    
    if not os.path.exists(app_file):
        print(f"   ❌ 找不到 {app_file}")
        return None
    
    result = run_modal_command(["modal", "deploy", app_file])
    
    if result.returncode == 0:
        print("   ✅ 部署成功")
        
        # 提取 URL
        urls = []
        for line in result.stdout.split('\n'):
            if "https://" in line and "modal.run" in line:
                url = line.strip()
                if url.startswith("https://"):
                    urls.append(url)
        
        return urls
    else:
        print(f"   ❌ 部署失败: {result.stderr}")
        return None


def get_app_status():
    """获取应用状态"""
    print(f"\n📊 检查 {APP_NAME} 状态...")
    
    result = run_modal_command(["modal", "app", "list"])
    
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        for line in lines:
            if APP_NAME in line.lower():
                print(f"   {line}")
                if "deployed" in line.lower():
                    return "deployed"
                elif "running" in line.lower():
                    return "running"
        print(f"   ℹ️ 应用未部署")
        return "not_deployed"
    else:
        print(f"   ⚠️ 无法获取状态: {result.stderr}")
        return "unknown"


def get_app_logs():
    """获取应用日志"""
    print(f"\n📜 获取 {APP_NAME} 日志...")
    run_modal_command(["modal", "app", "logs", APP_NAME], capture=False)


@app.local_entrypoint()
def main(action: str = "status", url: str = ""):
    """
    应用管理器
    
    参数:
        action: status, restart, redeploy, stop, logs
        url: 应用 URL (用于健康检查)
    """
    print("=" * 60)
    print("Z-Image-Turbo 应用管理器")
    print("=" * 60)
    
    if action == "status":
        # 检查状态
        status = get_app_status()
        
        if url and status in ["deployed", "running"]:
            with modal.enable_output():
                health = check_health.remote(url)
                print(f"\n🏥 健康检查: {health}")
    
    elif action == "stop":
        # 停止应用
        stop_app()
    
    elif action == "restart":
        # 重启应用
        print("\n🔄 重启应用...")
        
        # 1. 停止
        stop_app()
        
        # 2. 等待
        print("\n⏳ 等待 5 秒...")
        time.sleep(5)
        
        # 3. 重新部署
        urls = deploy_app()
        
        if urls:
            print("\n🌐 应用 URL:")
            for u in urls:
                print(f"   {u}")
            
            # 4. 等待启动
            print("\n⏳ 等待应用启动...")
            time.sleep(10)
            
            # 5. 健康检查
            for u in urls:
                if "ui" in u.lower():
                    with modal.enable_output():
                        health = check_health.remote(u)
                        print(f"\n🏥 健康检查: {health}")
                    break
    
    elif action == "redeploy":
        # 强制重新部署
        urls = deploy_app()
        
        if urls:
            print("\n🌐 应用 URL:")
            for u in urls:
                print(f"   {u}")
    
    elif action == "logs":
        # 查看日志
        get_app_logs()
    
    else:
        print(f"❌ 未知操作: {action}")
        print("支持: status, restart, redeploy, stop, logs")
    
    print("\n" + "=" * 60)

