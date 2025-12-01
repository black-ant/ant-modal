"""
LoRA 微调训练服务
使用 LoRA 技术微调 Stable Diffusion 模型
"""
import modal

app = modal.App("lora-training")

# 构建镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.24.0",
        "transformers==4.36.0",
        "accelerate",
        "peft",  # LoRA 库
        "torch==2.1.0",
        "torchvision",
        "datasets",
        "pillow",
    )
)

# 数据和模型存储
training_volume = modal.Volume.from_name("lora-training", create_if_missing=True)


@app.function(
    image=image,
    gpu="A100",
    volumes={"/training": training_volume},
    timeout=3600,  # 1小时
)
def train_lora(
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
    training_images_dir: str = "/training/images",
    output_dir: str = "/training/output",
    prompt: str = "a photo of sks person",
    num_train_epochs: int = 100,
    learning_rate: float = 1e-4,
    rank: int = 4,
):
    """
    训练 LoRA 模型
    
    Args:
        base_model: 基础模型
        training_images_dir: 训练图片目录
        output_dir: 输出目录
        prompt: 训练提示词
        num_train_epochs: 训练轮数
        learning_rate: 学习率
        rank: LoRA rank
    """
    from diffusers import StableDiffusionXLPipeline
    from peft import LoraConfig, get_peft_model
    import torch
    from torch.utils.data import Dataset, DataLoader
    from PIL import Image
    import os
    
    print("🎨 开始 LoRA 训练...")
    
    # 加载基础模型
    print("加载基础模型...")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.float16
    )
    pipe.to("cuda")
    
    # 配置 LoRA
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=rank,
        target_modules=["to_q", "to_v"],
        lora_dropout=0.1,
    )
    
    # 应用 LoRA
    unet = get_peft_model(pipe.unet, lora_config)
    
    # 准备数据集
    class ImageDataset(Dataset):
        def __init__(self, image_dir):
            self.images = [
                os.path.join(image_dir, f)
                for f in os.listdir(image_dir)
                if f.endswith(('.png', '.jpg', '.jpeg'))
            ]
        
        def __len__(self):
            return len(self.images)
        
        def __getitem__(self, idx):
            image = Image.open(self.images[idx]).convert("RGB")
            return image
    
    dataset = ImageDataset(training_images_dir)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=True)
    
    # 训练循环
    optimizer = torch.optim.AdamW(unet.parameters(), lr=learning_rate)
    
    print(f"开始训练 {num_train_epochs} 轮...")
    for epoch in range(num_train_epochs):
        for batch_idx, images in enumerate(dataloader):
            # 训练步骤
            # ... (简化示例)
            pass
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch + 1}/{num_train_epochs}")
    
    # 保存 LoRA 权重
    os.makedirs(output_dir, exist_ok=True)
    unet.save_pretrained(output_dir)
    
    # 提交到 Volume
    training_volume.commit()
    
    print(f"✓ LoRA 训练完成，权重已保存到 {output_dir}")
    return {"status": "completed", "output_dir": output_dir}


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/training": training_volume},
)
def generate_with_lora(
    prompt: str,
    lora_path: str = "/training/output",
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
) -> bytes:
    """
    使用训练好的 LoRA 生成图像
    """
    from diffusers import StableDiffusionXLPipeline
    import torch
    import io
    
    print("🎨 使用 LoRA 生成图像...")
    
    pipe = StableDiffusionXLPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.float16
    )
    pipe.load_lora_weights(lora_path)
    pipe.to("cuda")
    
    image = pipe(prompt).images[0]
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    
    print("✓ 图像生成完成")
    return buf.getvalue()


@app.local_entrypoint()
def main(action: str = "train"):
    """
    本地入口
    
    使用方法:
    modal run lora_training.py --action=train
    modal run lora_training.py --action=generate
    """
    if action == "train":
        result = train_lora.remote()
        print(result)
    elif action == "generate":
        image_bytes = generate_with_lora.remote("a photo of sks person")
        with open("lora_output.png", "wb") as f:
            f.write(image_bytes)
        print("✓ 图像已保存")
