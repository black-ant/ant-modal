"""
=============================================================================
SVD 1.1 (Stable Video Diffusion) ComfyUI 部署服务
=============================================================================
Stability AI 图生视频模型 - 从单张图片生成高质量视频

特点:
- 支持 SVD 和 SVD-XT 两个版本
- 14 帧 (SVD) 或 25 帧 (SVD-XT) 视频生成
- 576x1024 分辨率
- 6fps 帧率

部署命令: modal deploy svd_deploy.py
=============================================================================
"""
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
    .apt_install("git", "wget", "curl", "ffmpeg")  # ffmpeg 用于视频处理
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
# S2: 模型下载 - SVD 1.1 模型
# =============================================================================
def hf_download():
    """
    下载 SVD 1.1 模型:
    - svd.safetensors (14 帧标准版)
    - svd_xt.safetensors (25 帧扩展版)
    - svd_image_decoder.safetensors (图像解码器)
    """
    from huggingface_hub import hf_hub_download

    hf_token = os.getenv("HF_TOKEN")
    
    print("📦 下载 SVD 1.1 模型...")

    # 模型配置列表
    models = [
        {
            "repo_id": "stabilityai/stable-video-diffusion-img2vid",
            "filename": "svd.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/checkpoints",
            "target_name": "svd.safetensors",
            "desc": "SVD 标准版 (14 帧)"
        },
        {
            "repo_id": "stabilityai/stable-video-diffusion-img2vid-xt",
            "filename": "svd_xt.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/checkpoints",
            "target_name": "svd_xt.safetensors",
            "desc": "SVD-XT 扩展版 (25 帧)"
        },
        {
            "repo_id": "stabilityai/stable-video-diffusion-img2vid",
            "filename": "svd_image_decoder.safetensors",
            "target_dir": "/root/comfy/ComfyUI/models/vae",
            "target_name": "svd_image_decoder.safetensors",
            "desc": "SVD 图像解码器"
        }
    ]

    for model in models:
        print(f"📥 下载 {model['desc']}: {model['target_name']}...")
        
        try:
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
        except Exception as e:
            print(f"   ❌ {model['desc']} 失败: {e}")

    print("\n🎉 所有模型下载完成!")


def create_workflow_file():
    """创建 SVD 工作流 JSON 文件"""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "svd_xt.safetensors"
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "example.png"
            }
        },
        "3": {
            "class_type": "SVD_img2vid_Conditioning",
            "inputs": {
                "width": 1024,
                "height": 576,
                "video_frames": 25,
                "motion_bucket_id": 127,
                "fps": 6,
                "augmentation_level": 0,
                "clip_vision": ["1", 1],
                "init_image": ["2", 0],
                "vae": ["1", 2]
            }
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 20,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["3", 1],
                "latent_image": ["3", 2]
            }
        },
        "5": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            }
        },
        "6": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": 6,
                "loop_count": 0,
                "filename_prefix": "svd_output",
                "format": "video/h264-mp4",
                "images": ["5", 0]
            }
        }
    }
    
    Path("/root/workflow_api.json").write_text(json.dumps(workflow, ensure_ascii=False, indent=2))
    print("📝 SVD 工作流文件已创建")


# =============================================================================
# S3: 服务配置
# =============================================================================
vol = modal.Volume.from_name("svd-cache", create_if_missing=True)

image = (
    image
    .pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        hf_download,
        volumes={"/cache": vol},
        secrets=[hf_secret] if hf_secret else []
    )
    .run_function(create_workflow_file)
)

app = modal.App(name="svd-video", image=image)


# =============================================================================
# S4: UI 服务
# =============================================================================
@app.function(
    max_containers=1,
    gpu="A100",  # SVD 需要较大显存
    volumes={"/root": vol},  # 挂载到 /root，包含所有 ComfyUI 数据
    timeout=86400,
    scaledown_window=600,
)
@modal.concurrent(max_inputs=5)
@modal.web_server(8000, startup_timeout=120)
def ui():
    """ComfyUI Web 界面 - SVD 视频生成"""
    print("🌐 启动 SVD ComfyUI Web 界面 (端口: 8000)...")
    # 确保必要的目录存在
    Path("/root/comfy/ComfyUI/user/default/workflows").mkdir(parents=True, exist_ok=True)
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)


# =============================================================================
# S5: 本地入口点
# =============================================================================
@app.local_entrypoint()
def main():
    print("=" * 60)
    print("🎬 SVD 1.1 (Stable Video Diffusion) ComfyUI 部署")
    print("=" * 60)
    print("\n📦 模型来源:")
    print("   - stabilityai/stable-video-diffusion-img2vid")
    print("   - stabilityai/stable-video-diffusion-img2vid-xt")
    print("\n📋 已下载模型:")
    print("   - svd.safetensors (14 帧标准版)")
    print("   - svd_xt.safetensors (25 帧扩展版)")
    print("   - svd_image_decoder.safetensors (图像解码器)")
    print("\n🔧 配置:")
    print("   - GPU: A100 (40GB/80GB)")
    print("   - 分辨率: 576x1024")
    print("   - 帧率: 6 fps")
    print("   - 帧数: 14 (SVD) / 25 (SVD-XT)")
    print("\n📌 部署命令: modal deploy svd_deploy.py")
    print("=" * 60)
