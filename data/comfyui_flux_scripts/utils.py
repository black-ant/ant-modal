"""
实用工具函数集合
提供图像处理、格式转换、文件管理等辅助功能
"""

import modal
from pathlib import Path
from typing import Optional, Tuple, List
from config import get_volume

# 工具镜像 - 包含图像处理库
utils_image = (
    modal.Image.debian_slim()
    .pip_install(
        "Pillow",
        "numpy",
        "requests"
    )
)

vol = get_volume()
app = modal.App("comfyui-utils", image=utils_image)


@app.function()
def convert_image_format(
    image_bytes: bytes,
    output_format: str = "PNG",
    quality: int = 95
) -> bytes:
    """
    转换图片格式
    
    Args:
        image_bytes: 输入图片字节
        output_format: 输出格式 (PNG, JPEG, WEBP等)
        quality: 质量 (1-100, 仅用于 JPEG/WEBP)
    
    Returns:
        bytes: 转换后的图片字节
    """
    from PIL import Image
    from io import BytesIO
    
    # 读取图片
    input_image = Image.open(BytesIO(image_bytes))
    
    # 转换模式（JPEG不支持透明度）
    if output_format.upper() in ["JPEG", "JPG"] and input_image.mode in ["RGBA", "LA"]:
        # 创建白色背景
        background = Image.new("RGB", input_image.size, (255, 255, 255))
        if input_image.mode == "RGBA":
            background.paste(input_image, mask=input_image.split()[3])
        else:
            background.paste(input_image, mask=input_image.split()[1])
        input_image = background
    
    # 保存到字节流
    output_buffer = BytesIO()
    save_kwargs = {"format": output_format.upper()}
    
    if output_format.upper() in ["JPEG", "JPG", "WEBP"]:
        save_kwargs["quality"] = quality
    
    input_image.save(output_buffer, **save_kwargs)
    
    return output_buffer.getvalue()


@app.function()
def resize_image(
    image_bytes: bytes,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
    resample_method: str = "LANCZOS"
) -> bytes:
    """
    调整图片尺寸
    
    Args:
        image_bytes: 输入图片字节
        width: 目标宽度（None表示自动）
        height: 目标高度（None表示自动）
        maintain_aspect: 是否保持宽高比
        resample_method: 重采样方法 (LANCZOS, BILINEAR, BICUBIC, NEAREST)
    
    Returns:
        bytes: 调整后的图片字节
    """
    from PIL import Image
    from io import BytesIO
    
    # 读取图片
    img = Image.open(BytesIO(image_bytes))
    original_width, original_height = img.size
    
    # 计算新尺寸
    if maintain_aspect:
        if width and not height:
            # 只指定宽度，按比例计算高度
            height = int(original_height * (width / original_width))
        elif height and not width:
            # 只指定高度，按比例计算宽度
            width = int(original_width * (height / original_height))
        elif width and height:
            # 都指定时，选择较小的缩放比例
            scale = min(width / original_width, height / original_height)
            width = int(original_width * scale)
            height = int(original_height * scale)
    else:
        width = width or original_width
        height = height or original_height
    
    # 获取重采样方法
    resample_methods = {
        "LANCZOS": Image.Resampling.LANCZOS,
        "BILINEAR": Image.Resampling.BILINEAR,
        "BICUBIC": Image.Resampling.BICUBIC,
        "NEAREST": Image.Resampling.NEAREST
    }
    resample = resample_methods.get(resample_method.upper(), Image.Resampling.LANCZOS)
    
    # 调整大小
    resized_img = img.resize((width, height), resample)
    
    # 保存到字节流
    output_buffer = BytesIO()
    resized_img.save(output_buffer, format=img.format or "PNG")
    
    return output_buffer.getvalue()


@app.function()
def get_image_info(image_bytes: bytes) -> dict:
    """
    获取图片信息
    
    Args:
        image_bytes: 图片字节
    
    Returns:
        dict: 图片信息
    """
    from PIL import Image
    from io import BytesIO
    
    img = Image.open(BytesIO(image_bytes))
    
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
        "size_bytes": len(image_bytes),
        "size_kb": len(image_bytes) / 1024,
        "size_mb": len(image_bytes) / (1024 * 1024)
    }


@app.function()
def create_thumbnail(
    image_bytes: bytes,
    max_size: Tuple[int, int] = (256, 256)
) -> bytes:
    """
    创建缩略图
    
    Args:
        image_bytes: 原始图片字节
        max_size: 最大尺寸 (width, height)
    
    Returns:
        bytes: 缩略图字节
    """
    from PIL import Image
    from io import BytesIO
    
    img = Image.open(BytesIO(image_bytes))
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    output_buffer = BytesIO()
    img.save(output_buffer, format="PNG")
    
    return output_buffer.getvalue()


@app.function()
def add_watermark(
    image_bytes: bytes,
    watermark_text: str,
    position: str = "bottom-right",
    opacity: float = 0.5,
    font_size: int = 36
) -> bytes:
    """
    为图片添加水印
    
    Args:
        image_bytes: 原始图片字节
        watermark_text: 水印文本
        position: 位置 (top-left, top-right, bottom-left, bottom-right, center)
        opacity: 不透明度 (0-1)
        font_size: 字体大小
    
    Returns:
        bytes: 添加水印后的图片字节
    """
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    
    # 打开图片
    img = Image.open(BytesIO(image_bytes))
    
    # 创建绘图对象
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # 创建透明图层
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    # 使用默认字体（可以改为自定义字体）
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 获取文本边界框
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算位置
    positions = {
        "top-left": (10, 10),
        "top-right": (img.width - text_width - 10, 10),
        "bottom-left": (10, img.height - text_height - 10),
        "bottom-right": (img.width - text_width - 10, img.height - text_height - 10),
        "center": ((img.width - text_width) // 2, (img.height - text_height) // 2)
    }
    
    pos = positions.get(position, positions["bottom-right"])
    
    # 绘制水印
    text_color = (255, 255, 255, int(255 * opacity))
    draw.text(pos, watermark_text, font=font, fill=text_color)
    
    # 合并图层
    watermarked = Image.alpha_composite(img, txt_layer)
    
    # 转换回原始模式
    if img.mode != "RGBA":
        watermarked = watermarked.convert(img.mode)
    
    # 保存
    output_buffer = BytesIO()
    watermarked.save(output_buffer, format="PNG")
    
    return output_buffer.getvalue()


@app.function(volumes={"/cache": vol})
def save_to_volume(
    file_bytes: bytes,
    filename: str,
    subfolder: str = "outputs"
) -> dict:
    """
    保存文件到 Volume
    
    Args:
        file_bytes: 文件字节
        filename: 文件名
        subfolder: 子文件夹名
    
    Returns:
        dict: 保存结果
    """
    import os
    
    output_dir = f"/cache/{subfolder}"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = f"{output_dir}/{filename}"
    
    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        vol.commit()
        
        return {
            "success": True,
            "path": file_path,
            "size_bytes": len(file_bytes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": vol})
def load_from_volume(
    filename: str,
    subfolder: str = "outputs"
) -> dict:
    """
    从 Volume 加载文件
    
    Args:
        filename: 文件名
        subfolder: 子文件夹名
    
    Returns:
        dict: 加载结果
    """
    file_path = f"/cache/{subfolder}/{filename}"
    
    try:
        if not Path(file_path).exists():
            return {
                "success": False,
                "error": f"文件不存在: {filename}"
            }
        
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        return {
            "success": True,
            "file_bytes": file_bytes,
            "size_bytes": len(file_bytes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": vol})
def list_volume_files(
    subfolder: str = "outputs",
    extension: Optional[str] = None
) -> dict:
    """
    列出 Volume 中的文件
    
    Args:
        subfolder: 子文件夹名
        extension: 文件扩展名过滤 (如 ".png")
    
    Returns:
        dict: 文件列表
    """
    import os
    
    folder_path = f"/cache/{subfolder}"
    
    if not Path(folder_path).exists():
        return {"files": [], "count": 0}
    
    files = []
    for file in Path(folder_path).iterdir():
        if file.is_file():
            if extension is None or file.suffix.lower() == extension.lower():
                files.append({
                    "name": file.name,
                    "path": str(file),
                    "size_bytes": file.stat().st_size,
                    "size_kb": file.stat().st_size / 1024,
                    "extension": file.suffix
                })
    
    return {
        "files": files,
        "count": len(files)
    }


@app.function()
def batch_process_images(
    images_bytes: List[bytes],
    operation: str,
    **kwargs
) -> List[bytes]:
    """
    批量处理图片
    
    Args:
        images_bytes: 图片字节列表
        operation: 操作类型 (resize, convert, thumbnail, watermark)
        **kwargs: 操作参数
    
    Returns:
        List[bytes]: 处理后的图片字节列表
    """
    operations = {
        "resize": resize_image,
        "convert": convert_image_format,
        "thumbnail": create_thumbnail,
        "watermark": add_watermark
    }
    
    if operation not in operations:
        raise ValueError(f"未知操作: {operation}")
    
    func = operations[operation]
    results = []
    
    for img_bytes in images_bytes:
        try:
            processed = func.local(img_bytes, **kwargs)
            results.append(processed)
        except Exception as e:
            print(f"处理失败: {e}")
            results.append(img_bytes)  # 返回原图
    
    return results


@app.local_entrypoint()
def main(
    action: str = "info",
    image_file: str = "",
    output_file: str = "output.png",
    **kwargs
):
    """
    工具函数命令行入口
    
    使用示例:
    modal run utils.py --action=info --image-file=test.png
    modal run utils.py --action=resize --image-file=test.png --width=512 --height=512
    modal run utils.py --action=convert --image-file=test.png --output-format=JPEG
    modal run utils.py --action=watermark --image-file=test.png --watermark-text="My Image"
    """
    
    if not image_file:
        print("❌ 错误: 需要提供 --image-file 参数")
        return
    
    # 读取图片
    try:
        with open(image_file, 'rb') as f:
            image_bytes = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    if action == "info":
        # 获取图片信息
        info = get_image_info.remote(image_bytes)
        
        print(f"\n{'='*60}")
        print(f"图片信息: {Path(image_file).name}")
        print(f"{'='*60}")
        print(f"尺寸: {info['width']} x {info['height']}")
        print(f"格式: {info['format']}")
        print(f"模式: {info['mode']}")
        print(f"大小: {info['size_kb']:.2f} KB ({info['size_mb']:.2f} MB)")
    
    elif action == "resize":
        # 调整大小
        width = kwargs.get('width')
        height = kwargs.get('height')
        
        if not width and not height:
            print("❌ 错误: 需要提供 --width 或 --height 参数")
            return
        
        result = resize_image.remote(
            image_bytes,
            width=int(width) if width else None,
            height=int(height) if height else None
        )
        
        with open(output_file, 'wb') as f:
            f.write(result)
        
        print(f"✅ 调整后的图片已保存到: {output_file}")
    
    elif action == "convert":
        # 转换格式
        output_format = kwargs.get('output_format', 'PNG')
        quality = int(kwargs.get('quality', 95))
        
        result = convert_image_format.remote(
            image_bytes,
            output_format=output_format,
            quality=quality
        )
        
        with open(output_file, 'wb') as f:
            f.write(result)
        
        print(f"✅ 转换后的图片已保存到: {output_file}")
    
    elif action == "watermark":
        # 添加水印
        watermark_text = kwargs.get('watermark_text', 'Watermark')
        position = kwargs.get('position', 'bottom-right')
        
        result = add_watermark.remote(
            image_bytes,
            watermark_text=watermark_text,
            position=position
        )
        
        with open(output_file, 'wb') as f:
            f.write(result)
        
        print(f"✅ 添加水印后的图片已保存到: {output_file}")
    
    else:
        print(f"❌ 未知操作: {action}")
        print("支持的操作: info, resize, convert, watermark")
