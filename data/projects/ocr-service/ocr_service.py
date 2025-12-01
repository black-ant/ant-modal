"""
OCR 文字识别服务
使用 PaddleOCR 或 EasyOCR 识别图片中的文字

适用场景：
- 发票/票据识别
- 身份证/证件识别
- 截图文字提取
"""
import modal
import io
import base64

app = modal.App("ocr-service")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "easyocr",
        "Pillow",
        "numpy",
    )
)

model_volume = modal.Volume.from_name("ocr-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume},
    timeout=300,
)
class OCRService:
    @modal.enter()
    def load_model(self):
        import easyocr
        import os
        
        print("📝 加载 OCR 模型...")
        
        os.environ["EASYOCR_MODULE_PATH"] = "/models"
        
        # 支持中文和英文
        self.reader = easyocr.Reader(
            ["ch_sim", "en"],
            model_storage_directory="/models",
            gpu=True
        )
        
        print("✓ OCR 模型加载完成")
    
    @modal.method()
    def recognize(
        self,
        image_data: bytes,
        detail: bool = True,
        paragraph: bool = False
    ) -> dict:
        """
        识别图片中的文字
        
        Args:
            image_data: 图像二进制数据
            detail: 是否返回详细信息（位置、置信度）
            paragraph: 是否合并段落
        
        Returns:
            识别结果
        """
        from PIL import Image
        import numpy as np
        
        # 加载图像
        img = Image.open(io.BytesIO(image_data))
        img_array = np.array(img)
        
        # OCR 识别
        results = self.reader.readtext(
            img_array,
            detail=1,
            paragraph=paragraph
        )
        
        if detail:
            ocr_results = []
            for bbox, text, confidence in results:
                ocr_results.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [[int(p[0]), int(p[1])] for p in bbox]
                })
            
            # 提取纯文本
            full_text = " ".join([r["text"] for r in ocr_results])
            
            return {
                "text": full_text,
                "details": ocr_results
            }
        else:
            return {
                "text": " ".join([r[1] for r in results])
            }
    
    @modal.method()
    def batch_recognize(self, images: list[bytes]) -> list[dict]:
        """批量识别"""
        results = []
        for img_data in images:
            result = self.recognize(img_data)
            results.append(result)
        return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def ocr_api(data: dict):
    """
    OCR 识别 API
    
    POST /ocr_api
    {
        "image": "base64_encoded_image",
        "detail": true,
        "paragraph": false
    }
    """
    try:
        image_data = base64.b64decode(data.get("image", ""))
        
        ocr = OCRService()
        result = ocr.recognize.remote(
            image_data,
            detail=data.get("detail", True),
            paragraph=data.get("paragraph", False)
        )
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    """演示 OCR 识别"""
    from PIL import Image, ImageDraw, ImageFont
    
    print("📝 OCR 文字识别服务")
    print("=" * 50)
    
    # 创建带文字的测试图像
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Hello World!", fill="black")
    draw.text((50, 100), "你好，世界！", fill="black")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    ocr = OCRService()
    result = ocr.recognize.remote(buffer.getvalue())
    
    print(f"\n识别文本: {result['text']}")
    print(f"\n详细结果:")
    for r in result.get("details", []):
        print(f"  '{r['text']}' (置信度: {r['confidence']:.2%})")
    
    print("\n💡 提示: 支持中英文混合识别")

