"""
电商产品图批量生成
业务场景：电商运营需要为每个产品生成多种风格的展示图

解决的问题：
- 设计师处理一个产品需要 2 小时，产品上新时效性差
- 不同平台需要不同风格的图片，人工处理太耗时
- 需要快速生成 A/B 测试用的多个版本图片

这个例子展示：
- 批量生成不同风格的产品图
- 并行处理提升效率
- 保存到 Volume 便于下载
"""
import modal
import io
from datetime import datetime

app = modal.App("sd-ecommerce-product")

# 构建镜像
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

# 模型和输出存储
model_volume = modal.Volume.from_name("sd-models", create_if_missing=True)
output_volume = modal.Volume.from_name("product-images", create_if_missing=True)

# 预定义的电商图片风格模板
STYLE_TEMPLATES = {
    "简约白底": {
        "prompt_suffix": ", on pure white background, professional product photography, studio lighting, high quality, 4k",
        "negative": "busy background, cluttered, shadows, watermark"
    },
    "生活场景": {
        "prompt_suffix": ", in lifestyle setting, cozy home environment, natural lighting, warm atmosphere",
        "negative": "studio, artificial, cold, empty"
    },
    "节日促销": {
        "prompt_suffix": ", festive decoration, celebration mood, gift ribbons, sparkles, holiday theme",
        "negative": "plain, boring, dull colors"
    },
    "科技感": {
        "prompt_suffix": ", futuristic style, tech aesthetic, neon glow, dark background, modern design",
        "negative": "vintage, old, rustic, warm colors"
    },
    "自然清新": {
        "prompt_suffix": ", surrounded by green plants, natural daylight, fresh and clean, eco-friendly vibe",
        "negative": "artificial, plastic, industrial"
    }
}


@app.cls(
    image=image,
    gpu="A10G",
    volumes={"/models": model_volume, "/output": output_volume},
    timeout=600,
)
class ProductImageGenerator:
    @modal.enter()
    def load_model(self):
        """加载 SDXL 模型"""
        from diffusers import DiffusionPipeline
        import torch
        
        print("🎨 加载 Stable Diffusion XL 模型...")
        
        self.pipe = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            cache_dir="/models"
        )
        self.pipe.to("cuda")
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def generate_product_image(
        self,
        product_description: str,
        style: str = "简约白底",
        width: int = 1024,
        height: int = 1024,
        seed: int = None
    ) -> bytes:
        """
        生成单张产品图
        
        Args:
            product_description: 产品描述（如 "红色运动鞋"）
            style: 风格模板名称
            width: 图片宽度
            height: 图片高度
            seed: 随机种子
        """
        import torch
        
        style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["简约白底"])
        
        full_prompt = f"{product_description}{style_config['prompt_suffix']}"
        
        generator = None
        if seed is not None:
            generator = torch.Generator("cuda").manual_seed(seed)
        
        print(f"🎨 生成 [{style}] 风格的产品图...")
        
        image = self.pipe(
            prompt=full_prompt,
            negative_prompt=style_config["negative"],
            width=width,
            height=height,
            num_inference_steps=30,
            guidance_scale=7.5,
            generator=generator
        ).images[0]
        
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()


@app.function(
    image=image,
    volumes={"/output": output_volume},
    timeout=1200
)
def batch_generate_product_images(
    product_name: str,
    product_description: str,
    styles: list[str] = None,
    variants_per_style: int = 2
) -> dict:
    """
    批量生成多风格产品图
    
    Args:
        product_name: 产品名称（用于文件命名）
        product_description: 产品描述
        styles: 要生成的风格列表，None 表示全部
        variants_per_style: 每种风格生成几张变体
    
    Returns:
        生成结果统计
    """
    import os
    
    if styles is None:
        styles = list(STYLE_TEMPLATES.keys())
    
    generator = ProductImageGenerator()
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"/output/{product_name}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "product": product_name,
        "total_images": 0,
        "styles": {},
        "output_dir": output_dir
    }
    
    print(f"📦 为产品 [{product_name}] 生成图片")
    print(f"   描述: {product_description}")
    print(f"   风格: {', '.join(styles)}")
    print(f"   每风格变体: {variants_per_style}")
    
    for style in styles:
        results["styles"][style] = []
        
        for i in range(variants_per_style):
            seed = i * 1000 + hash(product_name) % 10000
            
            image_bytes = generator.generate_product_image.remote(
                product_description=product_description,
                style=style,
                seed=seed
            )
            
            # 保存图片
            filename = f"{style}_v{i+1}.png"
            filepath = f"{output_dir}/{filename}"
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            
            results["styles"][style].append(filename)
            results["total_images"] += 1
            
            print(f"  ✓ 保存: {filename}")
    
    output_volume.commit()
    
    print(f"\n✅ 完成！共生成 {results['total_images']} 张图片")
    print(f"📁 保存位置: {output_dir}")
    
    return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def generate_product_api(data: dict):
    """
    Web API: 批量生成产品图
    
    POST /generate_product_api
    {
        "product_name": "运动鞋",
        "product_description": "红色时尚运动鞋，网面透气设计",
        "styles": ["简约白底", "生活场景"],  // 可选
        "variants_per_style": 2  // 可选，默认2
    }
    """
    result = batch_generate_product_images.remote(
        product_name=data.get("product_name", "product"),
        product_description=data.get("product_description", ""),
        styles=data.get("styles"),
        variants_per_style=data.get("variants_per_style", 2)
    )
    
    return {
        "status": "success",
        "result": result
    }


@app.local_entrypoint()
def main():
    """
    演示批量生成产品图
    
    使用方法：
    modal run sd_ecommerce_product.py
    """
    print("🛍️  电商产品图批量生成")
    print("=" * 50)
    
    # 示例：为一款运动鞋生成多风格图片
    result = batch_generate_product_images.remote(
        product_name="运动鞋XR2024",
        product_description="时尚红色运动鞋，网面透气设计，白色中底",
        styles=["简约白底", "生活场景", "科技感"],
        variants_per_style=2
    )
    
    print("\n📊 生成统计:")
    print(f"   产品: {result['product']}")
    print(f"   总图片: {result['total_images']}")
    for style, files in result['styles'].items():
        print(f"   {style}: {len(files)} 张")
    
    print("\n💡 提示:")
    print("1. 可在 STYLE_TEMPLATES 中添加自定义风格")
    print("2. 部署 API 后可对接电商后台自动生成")
    print("3. 图片保存在 product-images Volume 中")

