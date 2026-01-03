# =============================================================================
# Z-Image-Turbo ComfyUI 一键部署服务 (快速版)
# =============================================================================
# 启动命令: modal deploy z_image_turbo_deploy.py
# UI 端口: 8000
# GPU: L40S (48GB)
# =============================================================================

import json
import os
import subprocess
from pathlib import Path

import modal

# =============================================================================
# S1: 环境准备 - 构建基础镜像
# =============================================================================
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl")
    .pip_install(
        "fastapi[standard]==0.115.4",
        "comfy-cli==1.5.3",
        "requests==2.32.3",
    )
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia")
)

# HuggingFace Secret
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None


# =============================================================================
# S2: 模型下载 - 从 Tongyi-MAI/Z-Image-Turbo 下载 3 个核心模型
# =============================================================================
def hf_download():
    """
    下载 Z-Image-Turbo 模型:
    - z_image_turbo_bf16.safetensors (主扩散模型)
    - qwen_3_4b.safetensors (CLIP 文本编码器)
    - ae.safetensors (VAE 解码器)
    - pixel_art_style_z_image_turbo.safetensors (Pixel Art LoRA)
    """
    from huggingface_hub import hf_hub_download

    hf_token = os.getenv("HF_TOKEN")
    
    print("📦 下载模型...")

    # 模型配置列表
    models = [
        # 从 Comfy-Org/z_image_turbo 下载的核心模型
        {
            "repo_id": "Comfy-Org/z_image_turbo",
            "filename": "split_files/diffusion_models/z_image_turbo_bf16.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/diffusion_models",
            "target_name": "z_image_turbo_bf16.safetensors",
            "desc": "主扩散模型"
        },
        {
            "repo_id": "Comfy-Org/z_image_turbo",
            "filename": "split_files/text_encoders/qwen_3_4b.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/clip",
            "target_name": "qwen_3_4b.safetensors",
            "desc": "CLIP 文本编码器"
        },
        {
            "repo_id": "Comfy-Org/z_image_turbo",
            "filename": "split_files/vae/ae.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/vae",
            "target_name": "ae.safetensors",
            "desc": "VAE 解码器"
        },
        # LoRA 模型 (来自不同仓库)
        {
            "repo_id": "tarn59/pixel_art_style_lora_z_image_turbo",
            "filename": "pixel_art_style_z_image_turbo.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/loras",
            "target_name": "pixel_art_style_z_image_turbo.safetensors",
            "desc": "Pixel Art LoRA"
        }
    ]

    for model in models:
        print(f"📥 下载 {model['desc']}: {model['target_name']}...")
        
        cached_path = hf_hub_download(
            repo_id=model["repo_id"],
            filename=model["filename"],
            cache_dir="/cache",
            token=hf_token
        )
        
        Path(model["target_dir"]).mkdir(parents=True, exist_ok=True)
        target_path = f"{model['target_dir']}/{model['target_name']}"
        subprocess.run(f"ln -sf {cached_path} {target_path}", shell=True, check=True)
        print(f"   ✅ {model['desc']} 完成")

    print("🎉 所有模型下载完成!")


def create_workflow_file():
    """创建工作流 JSON 文件"""
    workflow = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "z_image_turbo_bf16.safetensors",
                "weight_dtype": "default"
            }
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "qwen_3_4b.safetensors",
                "clip_name2": "qwen_3_4b.safetensors",
                "type": "z_image"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "一位美丽的亚洲女性，照片级真实，自然光线，高清细节",
                "clip": ["2", 0]
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "低质量，模糊，畸形，丑陋，文字，水印",
                "clip": ["2", 0]
            }
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": 42,
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "z_image_turbo", "images": ["8", 0]}
        }
    }
    
    Path("/root/workflow_api.json").write_text(json.dumps(workflow, ensure_ascii=False, indent=2))
    print("📝 工作流文件已创建")


# =============================================================================
# S3: 服务配置
# =============================================================================
vol = modal.Volume.from_name("z-image-turbo-cache", create_if_missing=True)

image = (
    image.pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        hf_download,
        volumes={"/cache": vol},
        secrets=[hf_secret] if hf_secret else []
    )
    .run_function(create_workflow_file)
)

app = modal.App(name="z-image-turbo", image=image)


# =============================================================================
# S4: UI 服务
# =============================================================================
@app.function(
    max_containers=1,
    gpu="L40S",
    volumes={"/cache": vol},
    timeout=86400,
    container_idle_timeout=600,
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """ComfyUI Web 界面 - Z-Image-Turbo"""
    print("🌐 启动 Z-Image-Turbo Web 界面 (端口: 8000)...")
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)


# =============================================================================
# S5: 本地入口点
# =============================================================================
@app.local_entrypoint()
def main():
    print("=" * 60)
    print("🖼️ Z-Image-Turbo ComfyUI 一键部署 (快速版)")
    print("=" * 60)
    print("\n📦 模型来源:")
    print("   - Comfy-Org/z_image_turbo")
    print("   - tarn59/pixel_art_style_lora_z_image_turbo")
    print("\n📋 已下载模型:")
    print("   - z_image_turbo_bf16.safetensors (主扩散模型)")
    print("   - qwen_3_4b.safetensors (CLIP 文本编码器)")
    print("   - ae.safetensors (VAE 解码器)")
    print("   - pixel_art_style_z_image_turbo.safetensors (Pixel Art LoRA)")
    print("\n🔧 配置:")
    print("   - GPU: L40S (48GB)")
    print("   - 采样步数: 4 步 (极速生成)")
    print("   - 分辨率: 1024x1024")
    print("\n📌 部署命令: modal deploy z_image_turbo_deploy.py")
    print("=" * 60)


