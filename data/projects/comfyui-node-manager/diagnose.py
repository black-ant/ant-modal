"""
=============================================================================
ComfyUI 诊断工具
=============================================================================
检查 Volume 中存储的模型和节点状态

使用方法:
    modal run diagnose.py
=============================================================================
"""
import modal
import os
import json
from pathlib import Path

# 配置参数
VOLUME_NAME = "comfyui-cache"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App("comfyui-diagnose", image=image)

# 模型类型映射
MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "controlnet", "upscale_models", "embeddings"]


@app.function(volumes={"/cache": vol})
def diagnose():
    """诊断 Volume 内容"""
    print("=" * 60)
    print("🔍 ComfyUI Volume 诊断报告")
    print("=" * 60)
    
    result = {"models": {}, "custom_nodes": [], "summary": {}}
    
    # 1. 检查模型
    print("\n📦 模型检查:")
    cache_models = Path("/cache/models")
    total_models = 0
    
    if cache_models.exists():
        for model_type in MODEL_TYPES:
            model_dir = cache_models / model_type
            if model_dir.exists():
                files = list(model_dir.iterdir())
                if files:
                    result["models"][model_type] = []
                    print(f"\n   📁 {model_type} ({len(files)} 个):")
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
                        is_link = f.is_symlink()
                        result["models"][model_type].append({
                            "name": f.name,
                            "size_mb": round(size_mb, 2),
                            "is_link": is_link
                        })
                        link_mark = " 🔗" if is_link else ""
                        print(f"      • {f.name} ({size_mb:.1f} MB){link_mark}")
                        total_models += 1
    else:
        print("   ℹ️ 无持久化模型目录")
    
    # 2. 检查节点
    print("\n" + "=" * 60)
    print("🧩 节点检查:")
    cache_nodes = Path("/cache/custom_nodes")
    
    if cache_nodes.exists():
        nodes = list(cache_nodes.iterdir())
        valid_nodes = 0
        
        for node_dir in nodes:
            if node_dir.is_dir():
                has_req = (node_dir / "requirements.txt").exists()
                has_init = (node_dir / "__init__.py").exists()
                
                # 尝试读取安装信息
                info_file = node_dir / ".install_info.json"
                install_info = {}
                if info_file.exists():
                    try:
                        install_info = json.loads(info_file.read_text())
                    except:
                        pass
                
                info = {
                    "name": node_dir.name,
                    "has_requirements": has_req,
                    "has_init": has_init,
                    "valid": has_init,
                    "repo_url": install_info.get("repo_url", ""),
                    "installed_at": install_info.get("installed_at", "")
                }
                result["custom_nodes"].append(info)
                
                status = "✅" if has_init else "⚠️"
                if has_init:
                    valid_nodes += 1
                
                print(f"\n   {status} {node_dir.name}")
                if info["repo_url"]:
                    print(f"      仓库: {info['repo_url']}")
                print(f"      requirements.txt: {'有' if has_req else '无'}")
                print(f"      __init__.py: {'有' if has_init else '无'}")
        
        print(f"\n   📊 节点统计: {valid_nodes}/{len(nodes)} 个有效")
    else:
        print("   ℹ️ 无持久化节点目录")
    
    # 3. 汇总
    result["summary"] = {
        "total_models": total_models,
        "total_nodes": len(result["custom_nodes"]),
        "valid_nodes": sum(1 for n in result["custom_nodes"] if n["valid"])
    }
    
    print("\n" + "=" * 60)
    print("📊 汇总")
    print("=" * 60)
    print(f"   模型: {result['summary']['total_models']} 个")
    print(f"   节点: {result['summary']['valid_nodes']}/{result['summary']['total_nodes']} 个有效")
    
    if result["summary"]["total_nodes"] > 0 or result["summary"]["total_models"] > 0:
        print("\n📌 提示:")
        print("   如果添加了新资源，需要重启 ComfyUI 服务才能生效")
        print("   运行: modal app stop comfyui-app")
    
    print("=" * 60)
    
    return result


@app.local_entrypoint()
def main():
    print("\n🔍 开始诊断 ComfyUI Volume...")
    result = diagnose.remote()
    print("\n✅ 诊断完成")

