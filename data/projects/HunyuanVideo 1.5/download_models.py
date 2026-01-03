"""
=============================================================================
HunyuanVideo 1.5 模型下载脚本
=============================================================================
下载 HunyuanVideo 1.5 所需的所有模型文件到 Modal Volume

模型列表:
  - 主模型: hunyuan_video_1.5_720p_bf16.safetensors (~16GB)
  - 文本编码器: clip_l.safetensors, llava_llama3_fp8_scaled.safetensors
  - VAE: hunyuan_video_vae_bf16.safetensors

使用方法:
    modal run download_models.py
=============================================================================
"""
import os
from pathlib import Path

import modal

# =============================================================================
# 项目变量
# =============================================================================
VOLUME_NAME = "hunyuan-video-cache"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4", "requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App(name="hunyuan-video-download", image=image)

# HuggingFace Secret (可选，用于访问受限模型)
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None


@app.function(
    volumes={"/models": vol},
    timeout=7200,  # 2小时超时
    secrets=[hf_secret] if hf_secret else [],
)
def download_hunyuan_models(resolution: str = "720p"):
    """
    下载 HunyuanVideo 1.5 模型
    
    Args:
        resolution: 分辨率选择 "480p" 或 "720p"
    """
    from huggingface_hub import hf_hub_download, snapshot_download
    
    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 HuggingFace Token: {'已配置 ✅' if hf_token else '未配置 (公开模型无需)'}")
    
    models_dir = Path("/models")
    
    # 创建目录结构
    (models_dir / "diffusion_models").mkdir(parents=True, exist_ok=True)
    (models_dir / "text_encoders").mkdir(parents=True, exist_ok=True)
    (models_dir / "vae").mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 60)
    print(f"📥 开始下载 HunyuanVideo 1.5 模型 ({resolution})")
    print("=" * 60)
    
    # =========================================================================
    # 1. 下载主模型 (Diffusion Model)
    # =========================================================================
    print("\n📥 [1/3] 下载主模型 (Diffusion Model)...")
    
    if resolution == "720p":
        model_file = "hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors"
        repo_id = "Kijai/HunyuanVideo_comfy"
    else:  # 480p
        model_file = "hunyuan_video_480_cfgdistill_fp8_e4m3fn.safetensors"
        repo_id = "Kijai/HunyuanVideo_comfy"
    
    try:
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=model_file,
            local_dir=models_dir / "diffusion_models",
            token=hf_token,
        )
        print(f"   ✅ {model_file}")
    except Exception as e:
        print(f"   ❌ 主模型下载失败: {e}")
        # 尝试备用源
        print("   🔄 尝试从官方源下载...")
        try:
            model_path = hf_hub_download(
                repo_id="tencent/HunyuanVideo-1.5",
                filename=f"hunyuan_video_1.5_{resolution}_t2v/diffusion_models/hunyuan_video_t2v_{resolution}_bf16.safetensors",
                local_dir=models_dir / "diffusion_models",
                token=hf_token,
            )
            print(f"   ✅ 从官方源下载成功")
        except Exception as e2:
            print(f"   ❌ 备用源也失败: {e2}")
    
    # =========================================================================
    # 2. 下载文本编码器 (Text Encoders)
    # =========================================================================
    print("\n📥 [2/3] 下载文本编码器...")
    
    text_encoders = [
        # CLIP-L 编码器
        ("Kijai/HunyuanVideo_comfy", "text_encoder/clip_l.safetensors", "clip_l.safetensors"),
        # LLaVA-Llama3 编码器 (FP8 量化版本，节省显存)
        ("Kijai/HunyuanVideo_comfy", "text_encoder/llava_llama3_fp8_scaled.safetensors", "llava_llama3_fp8_scaled.safetensors"),
    ]
    
    for repo_id, filename, local_name in text_encoders:
        try:
            encoder_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=models_dir / "text_encoders",
                token=hf_token,
            )
            # 重命名文件
            src = models_dir / "text_encoders" / filename
            dst = models_dir / "text_encoders" / local_name
            if src.exists() and not dst.exists():
                src.rename(dst)
            print(f"   ✅ {local_name}")
        except Exception as e:
            print(f"   ❌ {local_name}: {e}")
    
    # =========================================================================
    # 3. 下载 VAE 模型
    # =========================================================================
    print("\n📥 [3/3] 下载 VAE 模型...")
    
    try:
        vae_path = hf_hub_download(
            repo_id="Kijai/HunyuanVideo_comfy",
            filename="vae/hunyuan_video_vae_bf16.safetensors",
            local_dir=models_dir / "vae",
            token=hf_token,
        )
        print("   ✅ hunyuan_video_vae_bf16.safetensors")
    except Exception as e:
        print(f"   ❌ VAE 下载失败: {e}")
    
    # =========================================================================
    # 提交 Volume 更改
    # =========================================================================
    vol.commit()
    
    # =========================================================================
    # 显示下载结果
    # =========================================================================
    print("\n" + "=" * 60)
    print("📊 下载完成，模型列表:")
    print("=" * 60)
    
    for model_type in ["diffusion_models", "text_encoders", "vae"]:
        type_dir = models_dir / model_type
        if type_dir.exists():
            files = list(type_dir.rglob("*.safetensors"))
            if files:
                print(f"\n📁 {model_type}/")
                for f in files:
                    size_gb = f.stat().st_size / (1024**3)
                    print(f"   - {f.name} ({size_gb:.2f} GB)")
    
    print("\n✅ 模型下载完成！现在可以部署 hunyuan_video_deploy.py")


@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else [],
)
def download_i2v_models():
    """下载图生视频 (I2V) 额外模型"""
    from huggingface_hub import hf_hub_download
    
    hf_token = os.getenv("HF_TOKEN")
    models_dir = Path("/models")
    
    print("\n📥 下载 HunyuanVideo 1.5 I2V 额外模型...")
    
    # I2V 需要额外的 image encoder
    try:
        hf_hub_download(
            repo_id="Kijai/HunyuanVideo_comfy",
            filename="image_encoder/pytorch_model.bin",
            local_dir=models_dir / "clip_vision",
            token=hf_token,
        )
        print("   ✅ I2V Image Encoder")
    except Exception as e:
        print(f"   ❌ I2V 模型下载失败: {e}")
    
    vol.commit()
    print("\n✅ I2V 模型下载完成！")


@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else [],
)
def download_sr_models():
    """下载超分辨率模型 (480p->720p, 720p->1080p)"""
    from huggingface_hub import hf_hub_download
    
    hf_token = os.getenv("HF_TOKEN")
    models_dir = Path("/models")
    
    print("\n📥 下载 HunyuanVideo 1.5 超分辨率模型...")
    
    sr_models = [
        ("tencent/HunyuanVideo-1.5", "hunyuan_video_1.5_720p_sr/diffusion_models/hunyuan_video_sr_720p_bf16.safetensors"),
        ("tencent/HunyuanVideo-1.5", "hunyuan_video_1.5_1080p_sr/diffusion_models/hunyuan_video_sr_1080p_bf16.safetensors"),
    ]
    
    for repo_id, filename in sr_models:
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=models_dir / "diffusion_models",
                token=hf_token,
            )
            print(f"   ✅ {filename.split('/')[-1]}")
        except Exception as e:
            print(f"   ❌ {filename}: {e}")
    
    vol.commit()
    print("\n✅ 超分辨率模型下载完成！")


@app.local_entrypoint()
def main(resolution: str = "720p", include_i2v: bool = False, include_sr: bool = False):
    """
    下载 HunyuanVideo 1.5 模型
    
    Args:
        resolution: 分辨率 "480p" 或 "720p" (默认 720p)
        include_i2v: 是否下载 I2V 模型
        include_sr: 是否下载超分辨率模型
    """
    print("=" * 60)
    print("HunyuanVideo 1.5 模型下载")
    print("=" * 60)
    print(f"📦 Volume: {VOLUME_NAME}")
    print(f"📐 分辨率: {resolution}")
    print(f"🖼️ I2V 模型: {'是' if include_i2v else '否'}")
    print(f"🔍 超分模型: {'是' if include_sr else '否'}")
    
    # 下载主模型
    download_hunyuan_models.remote(resolution=resolution)
    
    # 可选：下载 I2V 模型
    if include_i2v:
        download_i2v_models.remote()
    
    # 可选：下载超分辨率模型
    if include_sr:
        download_sr_models.remote()
    
    print("\n🎉 所有模型下载完成！")
