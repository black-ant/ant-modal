"""
模型下载模块
负责从 HuggingFace 和远程 URL 下载所有必需的模型文件
"""

import os
import subprocess
import requests


def download_all_models():
    """下载所有模型文件"""
    from huggingface_hub import hf_hub_download
    
    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 HuggingFace Token状态: {'已配置' if hf_token else '未配置'}")
    
    # 下载基础模型
    download_flux_models(hf_hub_download, hf_token)
    
    # 下载 Clip 模型
    download_clip_models(hf_hub_download, hf_token)
    
    # 下载 VAE 模型
    download_vae_models(hf_hub_download, hf_token)
    
    # 下载 LoRA 模型
    download_lora_models(hf_hub_download)
    
    # 下载 LLAVA GGUF 模型
    download_llava_models(hf_hub_download)
    
    # 从 URL 下载模型
    download_url_models()


def download_flux_models(hf_hub_download, hf_token):
    """下载 Flux 基础模型"""
    print("📥 开始下载Flux基础模型...")
    flux_model = hf_hub_download(
        repo_id="Comfy-Org/flux1-dev",
        filename="flux1-dev-fp8.safetensors",
        cache_dir="/cache",
    )
    subprocess.run(
        f"ln -s {flux_model} /root/comfy/ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors",
        shell=True,
        check=True,
    )


def download_clip_models(hf_hub_download, hf_token):
    """下载 Clip 模型"""
    print("📥 开始下载Clip模型文件...")
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
            print(f"  📦 下载Clip模型: {clip_model['filename']}")
            clip_path = hf_hub_download(
                repo_id=clip_model["repo_id"],
                filename=clip_model["filename"],
                cache_dir="/cache",
                token=hf_token
            )
            subprocess.run(
                f"ln -s {clip_path} /root/comfy/ComfyUI/models/clip/{clip_model['local_name']}",
                shell=True,
                check=True
            )
        except Exception as e:
            print(f"❌ Clip模型下载失败 {clip_model['filename']}: {e}")


def download_vae_models(hf_hub_download, hf_token):
    """下载 VAE 模型"""
    print("📥 开始下载vae基础模型...")
    vae_model = hf_hub_download(
        repo_id="black-forest-labs/FLUX.1-dev",
        filename="ae.safetensors",
        cache_dir="/cache",
        token=hf_token
    )
    subprocess.run(
        f"ln -s {vae_model} /root/comfy/ComfyUI/models/vae/ae.safetensors",
        shell=True,
        check=True,
    )


def download_lora_models(hf_hub_download):
    """下载 LoRA 模型"""
    print("📥 开始下载LoRA模型...")
    lora_dir = "/root/comfy/ComfyUI/models/loras"
    os.makedirs(lora_dir, exist_ok=True)
    
    lora_models = [
        {
            "repo_id": "UmeAiRT/FLUX.1-dev-LoRA-Ume_Sky",
            "filename": "ume_sky_v2.safetensors",
            "local_name": "ume_sky_v2.safetensors"
        },
        {
            "repo_id": "Shakker-Labs/FLUX.1-dev-LoRA-Dark-Fantasy",
            "filename": "FLUX.1-dev-lora-Dark-Fantasy.safetensors",
            "local_name": "FLUX.1-dev-lora-Dark-Fantasy.safetensors"
        },
        {
            "repo_id": "aleksa-codes/flux-ghibsky-illustration",
            "filename": "lora_v2.safetensors",
            "local_name": "lora_v2.safetensors"
        }
    ]
    
    for lora in lora_models:
        try:
            print(f"  📦 下载LoRA: {lora['repo_id']}")
            lora_path = hf_hub_download(
                repo_id=lora["repo_id"],
                filename=lora["filename"],
                cache_dir="/cache",
            )
            subprocess.run(
                f"ln -s {lora_path} /root/comfy/ComfyUI/models/loras/{lora['local_name']}",
                shell=True,
                check=True
            )
        except Exception as e:
            print(f"❌ LoRA下载失败 {lora['repo_id']}: {e}")


def download_llava_models(hf_hub_download):
    """下载 LLAVA GGUF 模型"""
    print("📥 开始下载LLAVA GGUF模型...")
    llava_gguf_dir = "/root/comfy/ComfyUI/models/llava_gguf"
    os.makedirs(llava_gguf_dir, exist_ok=True)
    
    llava_gguf_models = [
        {
            "repo_id": "concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf",
            "filename": "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf",
            "local_name": "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf"
        },
        {
            "repo_id": "concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf",
            "filename": "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf",
            "local_name": "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf"
        }
    ]
    
    for llava_model in llava_gguf_models:
        try:
            print(f"  📦 下载LLAVA GGUF模型: {llava_model['filename']}")
            llava_path = hf_hub_download(
                repo_id=llava_model["repo_id"],
                filename=llava_model["filename"],
                cache_dir="/cache",
            )
            subprocess.run(
                f"ln -s {llava_path} /root/comfy/ComfyUI/models/llava_gguf/{llava_model['local_name']}",
                shell=True,
                check=True
            )
        except Exception as e:
            print(f"❌ LLAVA GGUF模型下载失败 {llava_model['filename']}: {e}")


def download_url_models():
    """从 URL 下载额外模型"""
    print("📥 开始从远程URL下载模型...")
    
    url_models = [
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/994980/xuer20E7BBAAE584BF20E4B880E99D.rPLX.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22xuerOneCyanTenColor_fluxV10.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T092255Z&X-Amz-SignedHeaders=host&X-Amz-Signature=623d3344c404f1479831b1f9a6908d5e215059a052d28d9123a67be437223e75", "filename": "一青十色.safetensors", "type": "checkpoints"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/17651/flux1LoraFlywayEpic.NKkZ.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22flux.1_lora_flyway_Epic-Characters_v1.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T083947Z&X-Amz-SignedHeaders=host&X-Amz-Signature=4ae9dcbd8c0205fb258b7839bb5895a94db6831ab9bf87c10936f4eafd6c028a", "filename": "中世纪风格.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/933225/newFantasyCorev4FLUX.pt13.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22New_Fantasy_CoreV4_FLUX.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T084003Z&X-Amz-SignedHeaders=host&X-Amz-Signature=45b8f8e990b9105872964a0d6a440b131bcdfcde0e0d8d0d5de29756b24b55d9", "filename": "奇幻幻想风.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/4768839/fluxthous40k.YPhQ.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22FluxThouS40k.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250907/us-east-1/s3/aws4_request&X-Amz-Date=20250907T084019Z&X-Amz-SignedHeaders=host&X-Amz-Signature=2c3aa9cd675bd52d2a190ffc033b6f98bf434d990b1053be3da5885e57571aa5", "filename": "中世纪铠甲风.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3182257/bustywomenV3.c0P4.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22BustyWomen-v3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121512Z&X-Amz-SignedHeaders=host&X-Amz-Signature=042811cfcc72b1b0dad382f504c2963c367137b5382a7a83351cf974afc25ab9", "filename": "异世界风格.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/7156478/fluxlisimoV5LoraFLUX.lPnA.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22fluxlisimo_v5_lora_FLUX.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123032Z&X-Amz-SignedHeaders=host&X-Amz-Signature=0154bafbf69aceac56ae628fa4581fbf5de619fb75f83fc492394e26d87b9de6", "filename": "提升细节.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/4821834/msFantasyFluxV3.ZUzM.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22MS_Fantasy_Flux_V3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T122846Z&X-Amz-SignedHeaders=host&X-Amz-Signature=56293c78b11ced23a246413ae8162e6fcfc9e5a271445d01fd02ab1a8fe8c55f", "filename": "MS幻想风格.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/modelVersion/2029387/Dystopian_Mythology_Fantasy.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Dystopian_Mythology_Fantasy.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T122735Z&X-Amz-SignedHeaders=host&X-Amz-Signature=5ffe9b52bd74e7792b34895f5e4d8f21a5f8f0294262555c14410964147193b4", "filename": "反乌托邦幻想.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/1490212/cheongsamF1Rank4Bf16.oUML.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22cheongsam_f1_rank4_bf16.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121558Z&X-Amz-SignedHeaders=host&X-Amz-Signature=a6d1bda3a8b1d51317c1a90cb709646fabdd0ead8325f3966a4475dc831d9df1", "filename": "旗袍风.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3182257/bustywomenV3.c0P4.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22BustyWomen-v3.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T121512Z&X-Amz-SignedHeaders=host&X-Amz-Signature=042811cfcc72b1b0dad382f504c2963c367137b5382a7a83351cf974afc25ab9", "filename": "好身材.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/1247607/mechaII.mgu7.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Mecha_II.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123151Z&X-Amz-SignedHeaders=host&X-Amz-Signature=f3a2c4232cef7c8c6cdda210460dbe79e22f7c155ce077ed0ec8c98d3a50ee20", "filename": "机械风格.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3879899/retroAnimeGITS95Style.uaNv.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Retro_Anime_-_GITS_95_style_IL_v1.0.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123317Z&X-Amz-SignedHeaders=host&X-Amz-Signature=2d8df89101f999b47fabbd712b1a77b94efda726a935dc955fd3aba79adb810c", "filename": "日漫风.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/3343899/yfgChatgpt4oStyle.qbhG.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22YFG-ChatGPT-4o-Style-v2e16.safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250909/us-east-1/s3/aws4_request&X-Amz-Date=20250909T123433Z&X-Amz-SignedHeaders=host&X-Amz-Signature=28ee2b9322ac58775c304df97c24ffff30241a7d8d40e9d742af2daee6b05e91", "filename": "暗黑电影.safetensors", "type": "loras"},
        {"url": "https://civitai-delivery-worker-prod.5ac0637cfd0766c97916cefa3764fbdf.r2.cloudflarestorage.com/model/532363/tensorxyGufengBDLora.Oyq1.safetensors?X-Amz-Expires=86400&response-content-disposition=attachment%3B%20filename%3D%22Tensorxy_Gufeng_BD_LoRA_v1..safetensors%22&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=e01358d793ad6966166af8b3064953ad/20250921/us-east-1/s3/aws4_request&X-Amz-Date=20250921T052055Z&X-Amz-SignedHeaders=host&X-Amz-Signature=4e42ff1a60f8e0aabd5ae41729bccc2f61d94b405dfb86b0050b462a8c30a1ab", "filename": "古风美女.safetensors", "type": "loras"}
    ]
    
    url_download_dir = "/cache"
    os.makedirs(url_download_dir, exist_ok=True)
    
    for model in url_models:
        final_model_path = os.path.join("/root/comfy/ComfyUI/models", model["type"], model["filename"])
        cached_file_path = os.path.join(url_download_dir, model["filename"])
        
        # 检查缓存
        if os.path.exists(cached_file_path):
            print(f"📦 缓存中发现模型 '{model['filename']}'，直接使用缓存")
            if not os.path.exists(final_model_path):
                os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
                subprocess.run(f"ln -s {cached_file_path} {final_model_path}", shell=True, check=True)
                print(f"✅ 从缓存创建链接: '{model['filename']}'")
            else:
                print(f"✅ 模型 '{model['filename']}' 缓存和链接都已存在")
            continue
        
        # 下载
        print(f"⬇️ 缓存中未找到，开始下载 '{model['filename']}' ...")
        try:
            with requests.get(model["url"], stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                with open(cached_file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"📥 下载完成，已保存到缓存: '{model['filename']}'")
            
            # 创建链接
            os.makedirs(os.path.dirname(final_model_path), exist_ok=True)
            subprocess.run(f"ln -s {cached_file_path} {final_model_path}", shell=True, check=True)
            print(f"✅ 模型 '{model['filename']}' 下载并链接完成")
        
        except Exception as e:
            print(f"❌ URL下载失败 {model['url']}: {e}")
            if os.path.exists(cached_file_path):
                os.remove(cached_file_path)
                print(f"🧹 已清理不完整的缓存文件: '{model['filename']}'")
