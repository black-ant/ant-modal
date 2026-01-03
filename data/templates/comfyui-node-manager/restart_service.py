"""
=============================================================================
ComfyUI 重启服务
=============================================================================
停止 ComfyUI 主服务，下次访问 URL 时会自动重启并加载新资源

使用场景:
    - 添加了新的节点后
    - 添加了新的模型后
    - 需要刷新服务配置时

使用方法:
    modal run restart_service.py
=============================================================================
"""
import modal
import subprocess
import sys

# 配置参数
APP_NAME = "comfyui-app"

app = modal.App("comfyui-restart-helper")


@app.local_entrypoint()
def main():
    """停止 ComfyUI 主服务"""
    print(f"\n{'='*60}")
    print(f"🔄 重启 ComfyUI 服务")
    print(f"{'='*60}")
    print(f"应用名称: {APP_NAME}")
    print(f"{'='*60}\n")
    
    print("⏹️ 正在停止服务...")
    
    try:
        result = subprocess.run(
            ["modal", "app", "stop", APP_NAME],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ 服务已停止")
            print(f"\n{'='*60}")
            print("📌 后续步骤:")
            print("=" * 60)
            print("   1. 访问 ComfyUI URL，服务会自动重启")
            print("   2. 重启时会自动加载 Volume 中的新资源:")
            print("      - 链接 /cache/models 中的模型")
            print("      - 链接 /cache/custom_nodes 中的节点")
            print("      - 安装节点的 requirements.txt 依赖")
            print(f"{'='*60}")
        else:
            if "not found" in result.stderr.lower() or "no app" in result.stderr.lower():
                print("ℹ️ 服务未在运行，无需停止")
                print("\n📌 可以直接部署主服务:")
                print("   modal deploy comfyui_app.py")
            else:
                print(f"⚠️ 停止服务时出现问题:")
                print(f"   {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("⚠️ 操作超时，请手动运行:")
        print(f"   modal app stop {APP_NAME}")
    except FileNotFoundError:
        print("❌ 未找到 modal 命令，请确保已安装 Modal CLI")
        print("   pip install modal")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
    
    print()

