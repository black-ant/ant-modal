"""
Stable Diffusion 图像生成服务
使用 SDXL 模型生成高质量图像
"""
import modal

app = modal.App("stable-diffusion")

# 构建包含 Stable Diffusion 的镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.24.0",
        "transformers==4.36.0",
        "accelerate",
        "safetensors",
        "torch==2.1.0",
        "torchvision",
    )
)

# 模型缓存 Volume
model_volume = modal.Volume.from_name("sd-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A10G",
    volumes={"/models": model_volume},
    timeout=600,
)
class StableDiffusion:
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
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: int = None
    ) -> bytes:
        """
        生成图像
        
        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            guidance_scale: 引导系数
            seed: 随机种子
        
        Returns:
            图像的字节数据
        """
        import torch
        import io
        
        if seed is not None:
            generator = torch.Generator("cuda").manual_seed(seed)
        else:
            generator = None
        
        print(f"🎨 生成图像: {prompt[:50]}...")
        
        image = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator
        ).images[0]
        
        # 转换为字节
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        
        print("✓ 图像生成完成")
        return buf.getvalue()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def generate_image(data: dict):
    """
    Web API 端点
    
    POST /generate_image
    {
        "prompt": "a beautiful sunset over mountains",
        "negative_prompt": "blurry, low quality",
        "width": 1024,
        "height": 1024,
        "steps": 30,
        "guidance": 7.5,
        "seed": 42
    }
    """
    sd = StableDiffusion()
    
    image_bytes = sd.generate.remote(
        prompt=data.get("prompt", ""),
        negative_prompt=data.get("negative_prompt", ""),
        width=data.get("width", 1024),
        height=data.get("height", 1024),
        num_inference_steps=data.get("steps", 30),
        guidance_scale=data.get("guidance", 7.5),
        seed=data.get("seed")
    )
    
    import base64
    return {
        "image": base64.b64encode(image_bytes).decode(),
        "format": "png"
    }


@app.local_entrypoint()
def main(prompt: str = "a beautiful sunset over mountains"):
    """
    本地测试
    
    使用方法:
    modal run sd_service.py --prompt="your prompt here"
    """
    sd = StableDiffusion()
    image_bytes = sd.generate.remote(prompt=prompt)
    
    # 保存图像
    with open("output.png", "wb") as f:
        f.write(image_bytes)
    
    print("✓ 图像已保存到 output.png")
