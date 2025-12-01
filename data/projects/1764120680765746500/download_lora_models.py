#!/usr/bin/env python3
"""
=============================================================================
ComfyUI LoRA 模型下载脚本
=============================================================================
功能说明：
- 从 HuggingFace 下载 3 个预定义的 LoRA 模型
  * UmeAiRT/FLUX.1-dev-LoRA-Ume_Sky (天空风格)
  * Shakker-Labs/FLUX.1-dev-LoRA-Dark-Fantasy (暗黑幻想)
  * aleksa-codes/flux-ghibsky-illustration (吉卜力天空)
- 支持缓存复用机制
- 创建软链接到 ComfyUI loras 目录

环境要求：
    可选 HuggingFace Secret（某些模型可能需要）

使用方法：
    modal run download_lora_models.py

独立运行：
    此脚本可独立运行，专注于 LoRA 模型下载
=============================================================================
"""

import os
import subprocess
import modal

# =============================================================================
# S1: 配置基础环境
# =============================================================================

print("🔧 配置 LoRA 模型下载环境...")

# 基础镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# HuggingFace Secret（可选）
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except:
    hf_secret = None
    print("⚠️  未配置 HuggingFace Secret，某些模型可能无法下载")

# Volume 持久化存储
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# =============================================================================
# S2: LoRA 模型下载函数
# =============================================================================

def download_lora_models():
    """下载 LoRA 模型"""
    from huggingface_hub import hf_hub_download
    
    print("📥 开始下载 LoRA 模型...")
    
    # LoRA 模型列表
    lora_models = [
        {
            "repo_id": "UmeAiRT/FLUX.1-dev-LoRA-Ume_Sky",
            "filename": "ume_sky_v2.safetensors",
            "local_name": "ume_sky_v2.safetensors",
            "description": "天空风格"
        },
        {
            "repo_id": "Shakker-Labs/FLUX.1-dev-LoRA-Dark-Fantasy",
            "filename": "FLUX.1-dev-lora-Dark-Fantasy.safetensors",
            "local_name": "FLUX.1-dev-lora-Dark-Fantasy.safetensors",
            "description": "暗黑幻想"
        },
        {
            "repo_id": "aleksa-codes/flux-ghibsky-illustration",
            "filename": "lora_v2.safetensors",
            "local_name": "lora_v2.safetensors",
            "description": "吉卜力天空"
        }
    ]
    
    # 创建 loras 目录
    lora_dir = "/root/comfy/ComfyUI/models/loras"
    os.makedirs(lora_dir, exist_ok=True)
    
    # 下载每个 LoRA 模型
    for lora in lora_models:
        try:
            print(f"\n📦 下载 {lora['description']}: {lora['repo_id']}")
            lora_path = hf_hub_download(
                repo_id=lora["repo_id"],
                filename=lora["filename"],
                cache_dir="/cache",
            )
            
            # 创建软链接
            target_path = f"{lora_dir}/{lora['local_name']}"
            subprocess.run(
                f"ln -sf {lora_path} {target_path}",
                shell=True,
                check=True
            )
            print(f"   ✅ {lora['local_name']} 下载完成")
            
        except Exception as e:
            print(f"   ❌ {lora['local_name']} 下载失败: {e}")
    
    print("\n✅ LoRA 模型下载完成！")


# 构建包含 LoRA 模型的镜像
secrets = [hf_secret] if hf_secret else []
image = image.run_function(
    download_lora_models,
    volumes={"/cache": vol},
    secrets=secrets
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-lora-models", image=image)

print("✅ LoRA 模型镜像构建完成！")
print("💡 提示：LoRA 模型已缓存，可用于风格迁移和效果增强")


@app.function(volumes={"/cache": vol})
def list_lora_models():
    """列出已下载的 LoRA 模型"""
    import os
    from pathlib import Path
    
    lora_dir = Path("/root/comfy/ComfyUI/models/loras")
    
    print("📋 已下载的 LoRA 模型:")
    if lora_dir.exists():
        lora_files = list(lora_dir.glob("*.safetensors"))
        if lora_files:
            for lora_file in sorted(lora_files):
                size_mb = lora_file.stat().st_size / (1024 * 1024)
                print(f"   ✅ {lora_file.name} ({size_mb:.1f} MB)")
            return {"status": "success", "count": len(lora_files)}
        else:
            print("   ⚠️  未找到 LoRA 模型文件")
            return {"status": "empty", "count": 0}
    else:
        print("   ❌ LoRA 目录不存在")
        return {"status": "error", "count": 0}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 列出 LoRA 模型...")
    result = list_lora_models.remote()
    print(f"\n📊 结果: {result}")

