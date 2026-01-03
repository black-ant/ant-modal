#!/usr/bin/env python3
"""
=============================================================================
基础模型下载
=============================================================================
功能说明：
- 从 HuggingFace 下载 Flux1-dev-fp8 主模型
- 下载 3 个 Clip 模型文件（clip_g, clip_l, t5xxl_fp8）
- 下载 VAE 模型（ae.safetensors）
- 创建软链接到 ComfyUI 模型目录

环境要求：
    需要设置 HuggingFace Secret: huggingface-secret
    包含环境变量: HF_TOKEN

使用方法：
    modal run download_base_models.py

独立运行：
    此脚本可独立运行，包含完整的 HuggingFace 认证和下载逻辑
=============================================================================
"""

import os
import subprocess
import modal

# =============================================================================
# S1: 配置基础环境和 Secret
# =============================================================================

print("🔧 配置基础模型下载环境...")

# 基础镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# HuggingFace Secret
hf_secret = modal.Secret.from_name("huggingface-secret")

# Volume 持久化存储
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# =============================================================================
# S2: 基础模型下载函数
# =============================================================================

def download_base_models():
    """下载 ComfyUI 基础模型"""
    from huggingface_hub import hf_hub_download
    
    # S2.0: 获取 HuggingFace Token
    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 HuggingFace Token 状态: {'已配置 ✅' if hf_token else '未配置 ❌'}")
    
    # S2.1: 下载 Flux1-dev-fp8 主模型
    print("\n📥 S2.1: 下载 Flux1-dev-fp8 主模型...")
    try:
        flux_model = hf_hub_download(
            repo_id="Comfy-Org/flux1-dev",
            filename="flux1-dev-fp8.safetensors",
            cache_dir="/cache",
        )
        subprocess.run(
            f"ln -sf {flux_model} /root/comfy/ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors",
            shell=True,
            check=True,
        )
        print("   ✅ Flux1-dev-fp8 下载完成")
    except Exception as e:
        print(f"   ❌ Flux1-dev-fp8 下载失败: {e}")
    
    # S2.2: 下载 Clip 模型文件
    print("\n📥 S2.2: 下载 Clip 模型文件...")
    clip_models = [
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/clip_g.safetensors",
            "local_name": "clip_g.safetensors"
        },
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/clip_l.safetensors",
            "local_name": "clip_l.safetensors"
        },
        {
            "repo_id": "stabilityai/stable-diffusion-3-medium",
            "filename": "text_encoders/t5xxl_fp8_e4m3fn.safetensors",
            "local_name": "t5xxl_fp8_e4m3fn.safetensors"
        }
    ]
    
    clip_dir = "/root/comfy/ComfyUI/models/clip"
    os.makedirs(clip_dir, exist_ok=True)
    
    for clip_model in clip_models:
        try:
            print(f"   📦 下载 {clip_model['local_name']}...")
            clip_path = hf_hub_download(
                repo_id=clip_model["repo_id"],
                filename=clip_model["filename"],
                cache_dir="/cache",
                token=hf_token
            )
            subprocess.run(
                f"ln -sf {clip_path} {clip_dir}/{clip_model['local_name']}",
                shell=True,
                check=True
            )
            print(f"   ✅ {clip_model['local_name']} 下载完成")
        except Exception as e:
            print(f"   ❌ {clip_model['local_name']} 下载失败: {e}")
    
    # S2.3: 下载 VAE 模型
    print("\n📥 S2.3: 下载 VAE 模型...")
    try:
        vae_model = hf_hub_download(
            repo_id="black-forest-labs/FLUX.1-dev",
            filename="ae.safetensors",
            cache_dir="/cache",
            token=hf_token
        )
        subprocess.run(
            f"ln -sf {vae_model} /root/comfy/ComfyUI/models/vae/ae.safetensors",
            shell=True,
            check=True,
        )
        print("   ✅ VAE 模型下载完成")
    except Exception as e:
        print(f"   ❌ VAE 模型下载失败: {e}")
    
    print("\n✅ 基础模型下载完成！")


# 构建包含模型的镜像
image = image.run_function(
    download_base_models,
    volumes={"/cache": vol},
    secrets=[hf_secret]
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-base-models", image=image)

print("✅ 基础模型镜像构建完成！")
print("💡 提示：模型已缓存到 Volume，后续可快速复用")


@app.function(volumes={"/cache": vol}, secrets=[hf_secret])
def verify_models():
    """验证基础模型是否下载成功"""
    import os
    
    models_to_check = [
        "/root/comfy/ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors",
        "/root/comfy/ComfyUI/models/clip/clip_g.safetensors",
        "/root/comfy/ComfyUI/models/clip/clip_l.safetensors",
        "/root/comfy/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors",
        "/root/comfy/ComfyUI/models/vae/ae.safetensors",
    ]
    
    print("🔍 验证基础模型文件...")
    all_exist = True
    for model_path in models_to_check:
        exists = os.path.exists(model_path)
        status = "✅" if exists else "❌"
        print(f"   {status} {os.path.basename(model_path)}")
        if not exists:
            all_exist = False
    
    return {"status": "success" if all_exist else "partial", "all_models_exist": all_exist}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 验证基础模型...")
    result = verify_models.remote()
    print(f"\n📊 验证结果: {result}")

