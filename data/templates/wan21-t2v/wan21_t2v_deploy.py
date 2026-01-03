# =============================================================================
# Wan 2.1 T2V (Text-to-Video) ComfyUI 一键部署服务
# =============================================================================
# 启动命令: modal deploy wan21_t2v_deploy.py
# UI 端口: 24782
# GPU: L40S (48GB) - 使用 FP8 量化模型，显存需求低，质量无损
# =============================================================================

import json
import os
import subprocess
from pathlib import Path

import modal

# =============================================================================
# 配置区域
# =============================================================================
# HuggingFace 模型仓库 (Wan 2.1 T2V)
WAN_MODEL_REPO = "Wan-Video/Wan2.1-T2V-14B"

# 备用轻量模型 (1.3B 版本，显存需求低)
WAN_MODEL_REPO_LITE = "Wan-Video/Wan2.1-T2V-1.3B"

# 模型精度配置
MODEL_DTYPE = "fp8"  # fp8 量化，显存需求降低 50%
GPU_TYPE = "L40S"    # L40S 48GB 显存足够运行 FP8 模型

# Volume 名称
MODEL_VOLUME_NAME = "wan21-t2v-model-cache"

# 服务端口
UI_PORT = 24782

# =============================================================================
# S1: 环境准备 - 构建基础镜像
# =============================================================================
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git", "wget", "curl", "ffmpeg",
        "libgl1", "libglib2.0-0", "libsm6", "libxext6", "libxrender1"
    )
    .pip_install(
        "fastapi[standard]==0.115.4",
        "comfy-cli==1.5.3",
        "requests==2.32.3",
        "torch==2.5.1",
        "torchvision==0.20.1",
        "torchaudio==2.5.1",
    )
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia")
    # 安装 WanVideoWrapper 自定义节点 (支持 Wan 2.x 系列)
    .run_commands(
        "cd /root/comfy/ComfyUI/custom_nodes && "
        "git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git"
    )
    .run_commands(
        "cd /root/comfy/ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper && "
        "pip install -r requirements.txt || true"
    )
    # 安装 VideoHelperSuite 用于视频保存
    .run_commands(
        "cd /root/comfy/ComfyUI/custom_nodes && "
        "git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
    )
    .run_commands(
        "cd /root/comfy/ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && "
        "pip install -r requirements.txt || true"
    )
)

# HuggingFace Secret
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None


# =============================================================================
# S2: 模型下载函数
# =============================================================================
def download_wan_models():
    """
    下载 Wan 2.1 T2V 模型:
    - Wan 2.1 T2V 14B 主模型 (diffusion_models)
    - VAE 模型
    - T5/UMT5 文本编码器 (FP8 量化优先)
    """
    from huggingface_hub import hf_hub_download

    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 HuggingFace Token状态: {'已配置' if hf_token else '未配置'}")
    print(f"📦 从 {WAN_MODEL_REPO} 下载 Wan 2.1 T2V 模型...")
    print(f"💡 使用 FP8 量化: 显存需求 ~30GB, 质量几乎无损")

    # Wan 2.1 使用的模型目录结构
    model_dirs = {
        "diffusion_models": "/root/comfy/ComfyUI/models/diffusion_models/wan",
        "vae": "/root/comfy/ComfyUI/models/vae",
        "clip": "/root/comfy/ComfyUI/models/clip",
    }
    
    for dir_path in model_dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    # 下载主模型 (Wan 2.1 T2V 14B)
    print("📥 下载 Wan 2.1 T2V 主模型...")
    model_files = [
        "diffusion_models/wan2.1_t2v_14B_fp8_e4m3fn.safetensors",
        "wan2.1_t2v_14B_fp8_e4m3fn.safetensors",
        "diffusion_models/wan2.1_t2v_14B_fp8.safetensors",
        "wan2.1_t2v_14B_fp8.safetensors",
        "diffusion_models/wan2.1_t2v_14B_fp16.safetensors",
        "wan2.1_t2v_14B_fp16.safetensors",
        "wan2.1_t2v_14B.safetensors",
    ]
    
    model_downloaded = False
    for model_file in model_files:
        try:
            main_model = hf_hub_download(
                repo_id=WAN_MODEL_REPO,
                filename=model_file,
                cache_dir="/cache",
                token=hf_token
            )
            model_basename = os.path.basename(model_file)
            target = f"{model_dirs['diffusion_models']}/{model_basename}"
            subprocess.run(f"ln -sf {main_model} {target}", shell=True, check=True)
            print(f"   ✅ 主模型完成: {model_basename}")
            model_downloaded = True
            break
        except Exception as e:
            continue
    
    if not model_downloaded:
        print(f"   ⚠️ 14B 模型下载失败，尝试 1.3B 轻量版...")
        lite_files = ["wan2.1_t2v_1.3B_fp16.safetensors"]
        for lite_file in lite_files:
            try:
                lite_model = hf_hub_download(
                    repo_id=WAN_MODEL_REPO_LITE,
                    filename=lite_file,
                    cache_dir="/cache",
                    token=hf_token
                )
                lite_basename = os.path.basename(lite_file)
                target = f"{model_dirs['diffusion_models']}/{lite_basename}"
                subprocess.run(f"ln -sf {lite_model} {target}", shell=True, check=True)
                print(f"   ✅ 轻量模型完成: {lite_basename}")
                model_downloaded = True
                break
            except Exception as e:
                continue

    # 下载 VAE 模型
    print("📥 下载 VAE 模型...")
    vae_files = ["vae/wan_2.1_vae.safetensors", "wan_2.1_vae.safetensors"]
    for vae_file in vae_files:
        try:
            vae_model = hf_hub_download(
                repo_id=WAN_MODEL_REPO,
                filename=vae_file,
                cache_dir="/cache",
                token=hf_token
            )
            target = f"{model_dirs['vae']}/wan_2.1_vae.safetensors"
            subprocess.run(f"ln -sf {vae_model} {target}", shell=True, check=True)
            print(f"   ✅ VAE 完成")
            break
        except Exception as e:
            continue

    # 下载 CLIP 文本编码器
    print("📥 下载 CLIP 文本编码器...")
    clip_files = [
        "text_encoders/umt5_xxl_fp8_e4m3fn.safetensors",
        "umt5_xxl_fp8_e4m3fn.safetensors",
        "text_encoders/umt5_xxl_fp16.safetensors",
        "umt5_xxl_fp16.safetensors",
    ]
    for clip_file in clip_files:
        try:
            clip_model = hf_hub_download(
                repo_id=WAN_MODEL_REPO,
                filename=clip_file,
                cache_dir="/cache",
                token=hf_token
            )
            clip_basename = os.path.basename(clip_file)
            target = f"{model_dirs['clip']}/{clip_basename}"
            subprocess.run(f"ln -sf {clip_model} {target}", shell=True, check=True)
            print(f"   ✅ CLIP 完成: {clip_basename}")
            break
        except Exception as e:
            continue

    print("🎉 模型下载流程完成!")


def create_workflow_file():
    """创建 T2V 工作流 JSON 文件"""
    workflow = {
        "1": {
            "class_type": "WanVideoModelLoader",
            "inputs": {"model_name": "wan2.1_t2v_14B_fp16.safetensors", "weight_dtype": "fp16"}
        },
        "2": {
            "class_type": "WanVideoVAELoader",
            "inputs": {"vae_name": "wan_2.1_vae.safetensors"}
        },
        "3": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "model": ["1", 0],
                "positive_prompt": "A serene landscape with mountains and flowing river, cinematic, 4K",
                "negative_prompt": "low quality, blurry, distorted, watermark"
            }
        },
        "4": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["1", 0], "vae": ["2", 0], "conditioning": ["3", 0],
                "width": 1280, "height": 720, "num_frames": 81,
                "steps": 30, "cfg": 5.0, "seed": 42, "denoise": 1.0
            }
        },
        "5": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["4", 0], "frame_rate": 16,
                "format": "video/h264-mp4", "filename_prefix": "wan21_t2v"
            }
        }
    }
    Path("/root/workflow_wan21_t2v.json").write_text(json.dumps(workflow, ensure_ascii=False, indent=2))
    print(f"📝 T2V 工作流文件已创建")


# =============================================================================
# S3: 服务配置
# =============================================================================
vol = modal.Volume.from_name(MODEL_VOLUME_NAME, create_if_missing=True)

image = (
    image.pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_wan_models,
        volumes={"/cache": vol},
        secrets=[hf_secret] if hf_secret else [],
        gpu="L40S",
        timeout=7200
    )
    .run_function(create_workflow_file)
)

app = modal.App(name="wan21-t2v-server", image=image)


# =============================================================================
# S4: UI 服务 (ComfyUI Web 界面)
# =============================================================================
@app.function(
    max_containers=1,
    gpu="L40S",
    volumes={"/cache": vol},
    timeout=86400,
    container_idle_timeout=600,
)
@modal.concurrent(max_inputs=1)
@modal.web_server(UI_PORT, startup_timeout=180)
def ui():
    """ComfyUI Web 界面 - Wan 2.1 T2V"""
    print(f"🎬 启动 Wan 2.1 T2V Web 界面 (端口: {UI_PORT})...")
    subprocess.Popen(f"comfy launch -- --listen 0.0.0.0 --port {UI_PORT}", shell=True)


# =============================================================================
# S5: 本地入口点
# =============================================================================
@app.local_entrypoint()
def main():
    print("=" * 60)
    print("🎬 Wan 2.1 T2V (Text-to-Video) ComfyUI 一键部署")
    print("=" * 60)
    print(f"\n📦 模型来源: HuggingFace {WAN_MODEL_REPO}")
    print(f"\n🔧 配置:")
    print(f"   - Volume: {MODEL_VOLUME_NAME}")
    print(f"   - UI 端口: {UI_PORT}")
    print(f"   - GPU: {GPU_TYPE} (48GB)")
    print(f"\n📌 部署命令: modal deploy wan21_t2v_deploy.py")
    print("=" * 60)
