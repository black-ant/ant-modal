#!/usr/bin/env python3
"""
=============================================================================
LLAVA 模型下载
=============================================================================
功能说明：
- 从 HuggingFace 下载 LLAVA GGUF 模型文件
  * Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf
  * llama-joycaption-beta-one-llava-mmproj-model-f16.gguf
- 创建专用的 llava_gguf 目录
- 用于图像描述和理解功能

环境要求：
    无特殊要求，公开模型

使用方法：
    modal run download_llava_models.py

独立运行：
    此脚本可独立运行，专注于 LLAVA 图像理解模型
=============================================================================
"""

import os
import subprocess
import modal

# =============================================================================
# S1: 配置基础环境
# =============================================================================

print("🔧 配置 LLAVA 模型下载环境...")

# 基础镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# Volume 持久化存储
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# =============================================================================
# S2: LLAVA 模型下载函数
# =============================================================================

def download_llava_models():
    """下载 LLAVA GGUF 模型"""
    from huggingface_hub import hf_hub_download
    
    print("📥 开始下载 LLAVA GGUF 模型...")
    
    # LLAVA 模型列表
    llava_gguf_models = [
        {
            "repo_id": "concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf",
            "filename": "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf",
            "local_name": "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf",
            "description": "LLAVA 主模型"
        },
        {
            "repo_id": "concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf",
            "filename": "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf",
            "local_name": "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf",
            "description": "LLAVA 投影模型"
        }
    ]
    
    # 创建 llava_gguf 目录
    llava_gguf_dir = "/root/comfy/ComfyUI/models/llava_gguf"
    os.makedirs(llava_gguf_dir, exist_ok=True)
    
    # 下载每个 LLAVA 模型
    for llava_model in llava_gguf_models:
        try:
            print(f"\n📦 下载 {llava_model['description']}: {llava_model['filename']}")
            llava_path = hf_hub_download(
                repo_id=llava_model["repo_id"],
                filename=llava_model["filename"],
                cache_dir="/cache",
            )
            
            # 创建软链接
            target_path = f"{llava_gguf_dir}/{llava_model['local_name']}"
            subprocess.run(
                f"ln -sf {llava_path} {target_path}",
                shell=True,
                check=True
            )
            print(f"   ✅ {llava_model['local_name']} 下载完成")
            
        except Exception as e:
            print(f"   ❌ {llava_model['local_name']} 下载失败: {e}")
    
    print("\n✅ LLAVA 模型下载完成！")


# 构建包含 LLAVA 模型的镜像
image = image.run_function(
    download_llava_models,
    volumes={"/cache": vol}
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-llava-models", image=image)

print("✅ LLAVA 模型镜像构建完成！")
print("💡 提示：LLAVA 模型用于图像描述和理解功能")


@app.function(volumes={"/cache": vol})
def verify_llava_models():
    """验证 LLAVA 模型是否下载成功"""
    import os
    from pathlib import Path
    
    llava_dir = Path("/root/comfy/ComfyUI/models/llava_gguf")
    
    expected_models = [
        "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf",
        "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf"
    ]
    
    print("🔍 验证 LLAVA 模型文件...")
    all_exist = True
    
    if llava_dir.exists():
        for model_name in expected_models:
            model_path = llava_dir / model_name
            exists = model_path.exists()
            status = "✅" if exists else "❌"
            
            if exists:
                size_mb = model_path.stat().st_size / (1024 * 1024)
                print(f"   {status} {model_name} ({size_mb:.1f} MB)")
            else:
                print(f"   {status} {model_name}")
                all_exist = False
    else:
        print("   ❌ LLAVA 目录不存在")
        all_exist = False
    
    return {"status": "success" if all_exist else "partial", "all_models_exist": all_exist}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 验证 LLAVA 模型...")
    result = verify_llava_models.remote()
    print(f"\n📊 验证结果: {result}")

