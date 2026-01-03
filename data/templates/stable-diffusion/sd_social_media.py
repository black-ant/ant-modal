"""
社交媒体营销图生成
业务场景：运营团队每天需要产出大量社交媒体配图

解决的问题：
- 每天需要发布 5-10 条内容，设计资源不足
- 不同平台尺寸要求不同，需要多次调整
- 热点事件需要快速响应，传统设计流程太慢

这个例子展示：
- 一键生成多平台尺寸图片
- 预设营销主题模板
- 批量生成节日/活动图片
"""
import modal
import io
from datetime import datetime

app = modal.App("sd-social-media")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.24.0",
        "transformers==4.36.0",
        "accelerate",
        "safetensors",
        "torch==2.1.0",
        "torchvision",
        "Pillow",
    )
)

model_volume = modal.Volume.from_name("sd-models", create_if_missing=True)
output_volume = modal.Volume.from_name("social-media-images", create_if_missing=True)

# 平台尺寸配置
PLATFORM_SIZES = {
    "微信公众号封面": {"width": 1024, "height": 576},   # 16:9
    "微信朋友圈": {"width": 1024, "height": 1024},      # 1:1
    "小红书封面": {"width": 768, "height": 1024},       # 3:4
    "抖音封面": {"width": 576, "height": 1024},         # 9:16
    "微博配图": {"width": 1024, "height": 768},         # 4:3
    "淘宝主图": {"width": 800, "height": 800},          # 1:1
}

# 营销主题模板
MARKETING_THEMES = {
    "新品上市": {
        "prompt_prefix": "New product launch announcement, ",
        "prompt_suffix": ", modern design, vibrant colors, exciting atmosphere, professional marketing style",
        "negative": "old, vintage, boring, dull"
    },
    "限时促销": {
        "prompt_prefix": "Flash sale promotion, ",
        "prompt_suffix": ", urgent feeling, bold text area, red and gold accents, shopping excitement",
        "negative": "calm, slow, ordinary"
    },
    "节日祝福": {
        "prompt_prefix": "Holiday celebration, ",
        "prompt_suffix": ", festive decorations, warm atmosphere, joyful mood, traditional elements",
        "negative": "sad, dark, gloomy"
    },
    "品牌故事": {
        "prompt_prefix": "Brand storytelling, ",
        "prompt_suffix": ", elegant composition, emotional connection, premium quality feel, artistic style",
        "negative": "cheap, cluttered, noisy"
    },
    "用户证言": {
        "prompt_prefix": "Customer testimonial background, ",
        "prompt_suffix": ", trustworthy atmosphere, professional look, clean space for text, friendly vibe",
        "negative": "fake, artificial, cold"
    }
}


@app.cls(
    image=image,
    gpu="A10G",
    volumes={"/models": model_volume, "/output": output_volume},
    timeout=600,
)
class SocialMediaGenerator:
    @modal.enter()
    def load_model(self):
        from diffusers import DiffusionPipeline
        import torch
        
        print("🎨 加载模型...")
        self.pipe = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            cache_dir="/models"
        )
        self.pipe.to("cuda")
        print("✓ 模型就绪")
    
    @modal.method()
    def generate_image(
        self,
        content_description: str,
        theme: str,
        platform: str,
        seed: int = None
    ) -> bytes:
        """生成单张社媒图片"""
        import torch
        
        theme_config = MARKETING_THEMES.get(theme, MARKETING_THEMES["新品上市"])
        size_config = PLATFORM_SIZES.get(platform, PLATFORM_SIZES["微信朋友圈"])
        
        prompt = f"{theme_config['prompt_prefix']}{content_description}{theme_config['prompt_suffix']}"
        
        generator = None
        if seed is not None:
            generator = torch.Generator("cuda").manual_seed(seed)
        
        image = self.pipe(
            prompt=prompt,
            negative_prompt=theme_config["negative"],
            width=size_config["width"],
            height=size_config["height"],
            num_inference_steps=25,
            guidance_scale=7.5,
            generator=generator
        ).images[0]
        
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()


@app.function(
    image=image,
    volumes={"/output": output_volume},
    timeout=1800
)
def generate_multi_platform_images(
    campaign_name: str,
    content_description: str,
    theme: str = "新品上市",
    platforms: list[str] = None
) -> dict:
    """
    为营销活动生成多平台图片
    
    一次性生成所有需要的平台尺寸
    """
    import os
    
    if platforms is None:
        platforms = list(PLATFORM_SIZES.keys())
    
    generator = SocialMediaGenerator()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"/output/{campaign_name}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "campaign": campaign_name,
        "theme": theme,
        "images": [],
        "output_dir": output_dir
    }
    
    print(f"📱 生成社媒营销图")
    print(f"   活动: {campaign_name}")
    print(f"   主题: {theme}")
    print(f"   平台: {', '.join(platforms)}")
    
    # 使用相同种子确保风格一致性
    base_seed = hash(campaign_name) % 100000
    
    for i, platform in enumerate(platforms):
        print(f"\n🔄 生成 {platform} 图片...")
        
        image_bytes = generator.generate_image.remote(
            content_description=content_description,
            theme=theme,
            platform=platform,
            seed=base_seed + i
        )
        
        filename = f"{platform.replace('/', '_')}.png"
        filepath = f"{output_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        size = PLATFORM_SIZES[platform]
        results["images"].append({
            "platform": platform,
            "filename": filename,
            "size": f"{size['width']}x{size['height']}"
        })
        
        print(f"   ✓ {platform}: {size['width']}x{size['height']}")
    
    output_volume.commit()
    
    print(f"\n✅ 完成！共生成 {len(results['images'])} 张图片")
    return results


@app.function(
    image=image,
    volumes={"/output": output_volume},
    timeout=3600
)
def generate_campaign_series(
    campaign_name: str,
    content_list: list[dict],
    platforms: list[str] = None
) -> dict:
    """
    批量生成一个营销活动的系列图片
    
    Args:
        campaign_name: 活动名称
        content_list: 内容列表 [{"description": "...", "theme": "..."}]
        platforms: 目标平台列表
    """
    results = {
        "campaign": campaign_name,
        "series": []
    }
    
    print(f"📢 批量生成营销活动系列图片")
    print(f"   活动: {campaign_name}")
    print(f"   内容数: {len(content_list)}")
    
    for i, content in enumerate(content_list, 1):
        print(f"\n{'='*40}")
        print(f"📄 处理第 {i}/{len(content_list)} 个内容")
        
        result = generate_multi_platform_images.remote(
            campaign_name=f"{campaign_name}_part{i}",
            content_description=content["description"],
            theme=content.get("theme", "新品上市"),
            platforms=platforms or ["微信公众号封面", "小红书封面", "微博配图"]
        )
        
        results["series"].append(result)
    
    print(f"\n{'='*40}")
    total_images = sum(len(s["images"]) for s in results["series"])
    print(f"🎉 活动图片全部生成完成！共 {total_images} 张")
    
    return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def generate_social_media_api(data: dict):
    """
    Web API: 生成社媒图片
    
    POST /generate_social_media_api
    {
        "campaign_name": "双十一预热",
        "content_description": "全场5折起，限时抢购",
        "theme": "限时促销",
        "platforms": ["微信朋友圈", "小红书封面"]
    }
    """
    result = generate_multi_platform_images.remote(
        campaign_name=data.get("campaign_name", "campaign"),
        content_description=data.get("content_description", ""),
        theme=data.get("theme", "新品上市"),
        platforms=data.get("platforms")
    )
    
    return {"status": "success", "result": result}


@app.local_entrypoint()
def main():
    """演示社媒图片生成"""
    print("📱 社交媒体营销图生成")
    print("=" * 50)
    
    # 生成一个促销活动的多平台图片
    result = generate_multi_platform_images.remote(
        campaign_name="春节大促",
        content_description="新春特惠，红包雨不停，全场满减优惠",
        theme="节日祝福",
        platforms=["微信公众号封面", "微信朋友圈", "小红书封面"]
    )
    
    print("\n📊 生成结果:")
    for img in result["images"]:
        print(f"   {img['platform']}: {img['size']}")
    
    print("\n💡 提示:")
    print("1. 可在 PLATFORM_SIZES 添加更多平台尺寸")
    print("2. 在 MARKETING_THEMES 添加自定义营销主题")
    print("3. 使用 generate_campaign_series 批量生成整个活动")

