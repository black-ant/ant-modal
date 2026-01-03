"""
=============================================================================
HunyuanVideo 1.5 应用管理脚本
=============================================================================
管理 Modal 上的 HunyuanVideo 应用：查看状态、停止应用、查看日志等

使用方法:
    # 查看应用状态
    modal run manage_app.py --action status
    
    # 停止应用
    modal run manage_app.py --action stop
    
    # 查看日志
    modal run manage_app.py --action logs
    
    # 列出 Volume 中的模型
    modal run manage_app.py --action list-models
=============================================================================
"""
import os
from pathlib import Path

import modal

# =============================================================================
# 项目变量
# =============================================================================
VOLUME_NAME = "hunyuan-video-cache"
APP_NAME = "hunyuan-video-app"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(name="hunyuan-video-manage", image=image)


@app.function(volumes={"/models": vol})
def list_models():
    """列出 Volume 中的所有模型"""
    models_dir = Path("/models")
    
    print("\n" + "=" * 60)
    print("📦 HunyuanVideo 1.5 模型列表")
    print("=" * 60)
    
    if not models_dir.exists():
        print("\n❌ Volume 中暂无模型，请先运行 download_models.py")
        return
    
    total_size = 0
    for model_type in ["diffusion_models", "text_encoders", "vae", "clip_vision", "loras"]:
        type_dir = models_dir / model_type
        if type_dir.exists():
            files = list(type_dir.rglob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith('.')]
            if files:
                print(f"\n📁 {model_type}/")
                for f in files:
                    size_gb = f.stat().st_size / (1024**3)
                    total_size += f.stat().st_size
                    print(f"   - {f.name} ({size_gb:.2f} GB)")
    
    print(f"\n📊 总大小: {total_size / (1024**3):.2f} GB")


@app.function(volumes={"/models": vol})
def clear_models(confirm: bool = False):
    """清空 Volume 中的所有模型"""
    if not confirm:
        print("⚠️ 此操作将删除所有模型！")
        print("   如果确认，请使用: modal run manage_app.py::clear_models --confirm")
        return
    
    import shutil
    models_dir = Path("/models")
    
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                print(f"   🗑️ 已删除: {item.name}/")
            else:
                item.unlink()
                print(f"   🗑️ 已删除: {item.name}")
    
    vol.commit()
    print("\n✅ Volume 已清空")


@app.function()
def show_status():
    """显示应用状态"""
    print("\n" + "=" * 60)
    print(f"📊 HunyuanVideo 1.5 应用状态")
    print("=" * 60)
    print(f"\n🏷️ 应用名称: {APP_NAME}")
    print(f"📦 Volume: {VOLUME_NAME}")
    print("\n💡 提示:")
    print(f"   - 查看日志: modal app logs {APP_NAME}")
    print(f"   - 停止应用: modal app stop {APP_NAME}")
    print(f"   - 查看详情: https://modal.com/apps")


@app.local_entrypoint()
def main(action: str = "status"):
    """
    HunyuanVideo 1.5 应用管理
    
    Args:
        action: 操作类型
            - status: 查看状态
            - list-models: 列出模型
            - clear-models: 清空模型 (危险)
    """
    if action == "status":
        show_status.remote()
    elif action == "list-models":
        list_models.remote()
    elif action == "clear-models":
        clear_models.remote(confirm=False)
    else:
        print(f"❌ 未知操作: {action}")
        print("   可用操作: status, list-models, clear-models")
