#!/usr/bin/env python3
"""
=============================================================================
ComfyUI URL 模型下载脚本
=============================================================================
功能说明：
- 从 Civitai 等远程 URL 下载额外的模型文件
- 包含 14 个风格模型（一青十色、中世纪风格、机械风格等）
- 实现智能缓存检测，避免重复下载
- 支持 checkpoints 和 loras 两种类型

使用方法：
    modal run download_url_models.py

独立运行：
    此脚本可独立运行，提供完整的 URL 下载和缓存管理
=============================================================================
"""

import os
import subprocess
import modal
import requests

# =============================================================================
# S1: 配置基础环境
# =============================================================================

print("🔧 配置 URL 模型下载环境...")

# 基础镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
    .pip_install("requests==2.32.3")
)

# Volume 持久化存储
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# =============================================================================
# S2: URL 模型下载函数
# =============================================================================

def download_url_models():
    """从远程 URL 下载模型"""
    
    print("📥 开始从 URL 下载额外模型...")
    
    # 模型 URL 列表
    url_models = [
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/994980/xuer20E7BBAAE584BF20E4B880E99D.rPLX.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22xuerOneCyanTenColor_fluxV10.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T092255Z&X-Amz-SignedHeaders=host&X-Amz-Signature=623d3344c404f1479831b1f9a6908d5e215059a052d28d9123a67be437223e75",
            "filename": "一青十色.safetensors",
            "type": "checkpoints"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/17651/flux1LoraFlywayEpic.NKkZ.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22flux.1_lora_flyway_Epic-Characters_v1.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T083947Z&X-Amz-SignedHeaders=host&X-Amz-Signature=4ae9dcbd8c0205fb258b7839bb5895a94db6831ab9bf87c10936f4eafd6c028a",
            "filename": "中世纪风格.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/933225/newFantasyCorev4FLUX.pt13.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22New_Fantasy_CoreV4_FLUX.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Az-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T084003Z&X-Amz-SignedHeaders=host&X-Amz-Signature=45b8f8e990b9105872964a0d6a440b131bcdfcde0e0d8d0d5de29756b24b55d9",
            "filename": "奇幻幻想风.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/4768839/fluxthous40k.YPhQ.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22FluxThouS40k.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T084019Z&X-Amz-SignedHeaders=host&X-Amz-Signature=2c3aa9cd675bd52d2a190ffc033b6f98bf434d990b1053be3da5885e57571aa5",
            "filename": "中世纪铠甲风.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3182257/bustywomenV3.c0P4.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22BustyWomen-v3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121512Z&X-Amz-SignedHeaders=host&X-Amz-Signature=042811cfcc72b1b0dad382f504c2963c367137b5382a7a83351cf974afc25ab9",
            "filename": "异世界风格.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/7156478/fluxlisimoV5LoraFLUX.lPnA.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22fluxlisimo_v5_lora_FLUX.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123032Z&X-Amz-SignedHeaders=host&X-Amz-Signature=0154bafbf69aceac56ae628fa4581fbf5de619fb75f83fc492394e26d87b9de6",
            "filename": "提升细节.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/4821834/msFantasyFluxV3.ZUzM.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22MS_Fantasy_Flux_V3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T122846Z&X-Amz-SignedHeaders=host&X-Amz-Signature=56293c78b11ced23a246413ae8162e6fcfc9e5a271445d01fd02ab1a8fe8c55f",
            "filename": "MS幻想风格.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/modelVersion/2029387/Dystopian_Mythology_Fantasy.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Dystopian_Mythology_Fantasy.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T122735Z&X-Amz-SignedHeaders=host&X-Amz-Signature=5ffe9b52bd74e7792b34895f5e4d8f21a5f8f0294262555c14410964147193b4",
            "filename": "反乌托邦幻想.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/1490212/cheongsamF1Rank4Bf16.oUML.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22cheongsam_f1_rank4_bf16.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121558Z&X-Amz-SignedHeaders=host&X-Amz-Signature=a6d1bda3a8b1d51317c1a90cb709646fabdd0ead8325f3966a4475dc831d9df1",
            "filename": "旗袍风.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3182257/bustywomenV3.c0P4.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22BustyWomen-v3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121512Z&X-Amz-SignedHeaders=host&X-Amz-Signature=042811cfcc72b1b0dad382f504c2963c367137b5382a7a83351cf974afc25ab9",
            "filename": "好身材.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/1247607/mechaII.mgu7.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Mecha_II.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123151Z&X-Amz-SignedHeaders=host&X-Amz-Signature=f3a2c4232cef7c8c6cdda210460dbe79e22f7c155ce077ed0ec8c98d3a50ee20",
            "filename": "机械风格.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3879899/retroAnimeGITS95Style.uaNv.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Retro_Anime_-_GITS_95_style_IL_v1.0.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123317Z&X-Amz-SignedHeaders=host&X-Amz-Signature=2d8df89101f999b47fabbd712b1a77b94efda726a935dc955fd3aba79adb810c",
            "filename": "日漫风.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3343899/yfgChatgpt4oStyle.qbhG.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22YFG-ChatGPT-4o-Style-v2e16.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123433Z&X-Amz-SignedHeaders=host&X-Amz-Signature=28ee2b9322ac58775c304df97c24ffff30241a7d8d40e9d742af2daee6b05e91",
            "filename": "暗黑电影.safetensors",
            "type": "loras"
        },
        {
            "url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/532363/tensorxyGufengBDLora.Oyq1.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Tensorxy_Gufeng_BD_LoRA_v1..safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250921/us-east-1/s3/aws4_request&X-Amz-Date=20250921T052055Z&X-Amz-SignedHeaders=host&X-Amz-Signature=4e42ff1a60f8e0aabd5ae41729bccc2f61d94b405dfb86b0050b462a8c30a1ab",
            "filename": "古风美女.safetensors",
            "type": "loras"
        }
    ]
    
    # 缓存目录
    url_download_dir = "/cache"
    os.makedirs(url_download_dir, exist_ok=True)
    
    # 下载统计
    downloaded = 0
    cached = 0
    failed = 0
    
    for model in url_models:
        final_model_path = os.path.join(
            "/root/comfy/ComfyUI/models", model["type"], model["filename"]
        )
        cached_file_path = os.path.join(url_download_dir, model["filename"])
        
        # S2.1: 检查缓存是否已有文件
        if os.path.exists(cached_file_path):
            print(f"📦 缓存命中: {model['filename']}")
            cached += 1
            
            # 创建软链接（如果不存在）
            if not os.path.exists(final_model_path):
                os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
                subprocess.run(
                    f"ln -sf {cached_file_path} {final_model_path}",
                    shell=True,
                    check=True
                )
                print(f"   ✅ 从缓存创建链接")
            continue
        
        # S2.2: 下载文件
        print(f"⬇️  下载: {model['filename']}...")
        try:
            with requests.get(model["url"], stream=True, allow_redirects=True, timeout=300) as r:
                r.raise_for_status()
                
                # 获取文件大小
                total_size = int(r.headers.get('content-length', 0))
                total_mb = total_size / (1024 * 1024)
                
                print(f"   📊 文件大小: {total_mb:.1f} MB")
                
                with open(cached_file_path, 'wb') as f:
                    downloaded_size = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 每下载 50MB 显示进度
                        if downloaded_size % (50 * 1024 * 1024) < 8192:
                            progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                            print(f"   📥 进度: {progress:.1f}%")
            
            print(f"   ✅ 下载完成，已保存到缓存")
            downloaded += 1
            
            # S2.3: 创建软链接
            os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
            subprocess.run(
                f"ln -sf {cached_file_path} {final_model_path}",
                shell=True,
                check=True
            )
            
        except Exception as e:
            print(f"   ❌ 下载失败: {e}")
            failed += 1
            
            # 清理不完整的文件
            if os.path.exists(cached_file_path):
                os.remove(cached_file_path)
                print(f"   🧹 已清理不完整的文件")
    
    print(f"\n✅ URL 模型下载完成！")
    print(f"   📊 统计: 下载={downloaded}, 缓存命中={cached}, 失败={failed}")


# 构建包含 URL 模型的镜像
image = image.run_function(
    download_url_models,
    volumes={"/cache": vol}
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-url-models", image=image)

print("✅ URL 模型镜像构建完成！")
print("💡 提示：包含多种风格的 LoRA 和 Checkpoint 模型")


@app.function(volumes={"/cache": vol})
def list_url_models():
    """列出已下载的 URL 模型"""
    import os
    from pathlib import Path
    
    print("📋 已下载的 URL 模型:")
    
    # 检查 loras
    lora_dir = Path("/root/comfy/ComfyUI/models/loras")
    if lora_dir.exists():
        print("\n=== LoRA 模型 ===")
        for lora_file in sorted(lora_dir.glob("*.safetensors")):
            size_mb = lora_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ {lora_file.name} ({size_mb:.1f} MB)")
    
    # 检查 checkpoints
    checkpoint_dir = Path("/root/comfy/ComfyUI/models/checkpoints")
    if checkpoint_dir.exists():
        print("\n=== Checkpoint 模型 ===")
        for checkpoint_file in sorted(checkpoint_dir.glob("*.safetensors")):
            size_mb = checkpoint_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ {checkpoint_file.name} ({size_mb:.1f} MB)")
    
    return {"status": "success"}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 列出 URL 模型...")
    list_url_models.remote()

