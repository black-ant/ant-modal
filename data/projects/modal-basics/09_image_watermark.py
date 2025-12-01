"""
09 - 批量图片水印服务
业务场景：内容平台/电商需要给大量图片添加版权水印

解决的问题：
- 每天有数百张产品图需要添加水印
- 本地 Photoshop 批处理太慢，一张要 5 秒
- 需要一个 API 服务，上传即可获得带水印的图片

这个例子展示：
- 自定义 Image 安装图片处理库
- Web API 接收图片
- 并行处理多张图片
- Volume 存储处理后的图片
"""
import modal
from pathlib import Path
import io
import base64
from datetime import datetime

# 创建带有 Pillow 的自定义镜像
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "Pillow>=10.0.0"
)

app = modal.App("image-watermark", image=image)

# 存储处理后的图片
volume = modal.Volume.from_name("watermarked-images", create_if_missing=True)


@app.function()
def add_watermark(
    image_data: bytes,
    watermark_text: str = "© 2024 MyCompany",
    position: str = "bottom-right",
    opacity: float = 0.5
) -> bytes:
    """
    给单张图片添加文字水印
    
    参数：
    - image_data: 图片二进制数据
    - watermark_text: 水印文字
    - position: 水印位置 (bottom-right, bottom-left, top-right, top-left, center)
    - opacity: 透明度 (0.0 - 1.0)
    """
    from PIL import Image, ImageDraw, ImageFont
    
    # 打开图片
    img = Image.open(io.BytesIO(image_data))
    
    # 如果是 RGBA 模式，转换处理
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # 创建水印层
    watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)
    
    # 计算字体大小（基于图片尺寸）
    font_size = max(20, min(img.width, img.height) // 20)
    
    # 使用默认字体（实际项目中可以使用自定义字体）
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 获取文字尺寸
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算水印位置
    padding = 20
    positions = {
        "bottom-right": (img.width - text_width - padding, img.height - text_height - padding),
        "bottom-left": (padding, img.height - text_height - padding),
        "top-right": (img.width - text_width - padding, padding),
        "top-left": (padding, padding),
        "center": ((img.width - text_width) // 2, (img.height - text_height) // 2),
    }
    x, y = positions.get(position, positions["bottom-right"])
    
    # 绘制水印文字（半透明白色带阴影）
    shadow_offset = 2
    shadow_color = (0, 0, 0, int(255 * opacity * 0.5))
    text_color = (255, 255, 255, int(255 * opacity))
    
    draw.text((x + shadow_offset, y + shadow_offset), watermark_text, font=font, fill=shadow_color)
    draw.text((x, y), watermark_text, font=font, fill=text_color)
    
    # 合并图层
    watermarked = Image.alpha_composite(img, watermark_layer)
    
    # 转换回 RGB 并输出
    if watermarked.mode == "RGBA":
        watermarked = watermarked.convert("RGB")
    
    output = io.BytesIO()
    watermarked.save(output, format="JPEG", quality=95)
    return output.getvalue()


@app.function()
def process_batch(images: list[dict], watermark_text: str) -> list[dict]:
    """
    批量处理多张图片
    每张图片独立处理，并行执行
    """
    results = []
    for img_info in images:
        try:
            watermarked = add_watermark.remote(
                img_info["data"],
                watermark_text,
                img_info.get("position", "bottom-right")
            )
            results.append({
                "filename": img_info["filename"],
                "status": "success",
                "data": watermarked
            })
        except Exception as e:
            results.append({
                "filename": img_info["filename"],
                "status": "error",
                "error": str(e)
            })
    return results


@app.function()
@modal.web_endpoint(method="POST")
def watermark_api(request: dict):
    """
    POST /watermark_api
    
    Web API 端点，接收图片并返回带水印的图片
    
    请求格式：
    {
        "image": "base64编码的图片数据",
        "watermark_text": "© 2024 MyCompany",
        "position": "bottom-right"
    }
    
    响应格式：
    {
        "status": "success",
        "watermarked_image": "base64编码的处理后图片"
    }
    """
    try:
        # 解码 base64 图片
        image_b64 = request.get("image", "")
        image_data = base64.b64decode(image_b64)
        
        watermark_text = request.get("watermark_text", "© 2024 MyCompany")
        position = request.get("position", "bottom-right")
        
        # 处理图片
        watermarked = add_watermark.remote(image_data, watermark_text, position)
        
        # 返回 base64 编码的结果
        return {
            "status": "success",
            "watermarked_image": base64.b64encode(watermarked).decode()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.function(volumes={"/images": volume})
def save_watermarked_images(images: list[dict]) -> list[str]:
    """
    将处理后的图片保存到 Volume
    """
    saved_paths = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for i, img in enumerate(images):
        if img["status"] == "success":
            filename = f"/images/{timestamp}_{img['filename']}"
            with open(filename, "wb") as f:
                f.write(img["data"])
            saved_paths.append(filename)
    
    volume.commit()
    return saved_paths


@app.local_entrypoint()
def main():
    """
    演示批量水印处理
    
    使用方法：
    - 测试运行：modal run 09_image_watermark.py
    - 部署 API：modal deploy 09_image_watermark.py
    """
    from PIL import Image
    
    print("🖼️  批量图片水印服务")
    print("=" * 50)
    
    # 创建测试图片
    print("📷 创建测试图片...")
    test_images = []
    
    for i in range(5):
        # 创建一张纯色测试图片
        img = Image.new("RGB", (800, 600), color=(100 + i * 30, 150, 200))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        test_images.append({
            "filename": f"test_image_{i+1}.jpg",
            "data": buffer.getvalue(),
            "position": ["bottom-right", "bottom-left", "top-right", "top-left", "center"][i]
        })
    
    print(f"📦 准备处理 {len(test_images)} 张图片...")
    
    # 并行添加水印
    watermarked_results = []
    for img_info in test_images:
        result_data = add_watermark.remote(
            img_info["data"],
            "© 2024 MyCompany",
            img_info["position"]
        )
        watermarked_results.append({
            "filename": img_info["filename"],
            "status": "success",
            "data": result_data
        })
    
    print("✅ 水印添加完成！")
    
    # 保存到 Volume
    saved = save_watermarked_images.remote(watermarked_results)
    print(f"💾 已保存 {len(saved)} 张图片到 Volume")
    
    print("\n💡 提示:")
    print("1. 部署后可通过 API 上传图片自动添加水印")
    print("2. 支持自定义水印文字和位置")
    print("3. 处理后的图片会自动保存到云端存储")

