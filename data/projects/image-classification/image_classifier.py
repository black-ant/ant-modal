"""
图像识别分类服务
使用 ResNet/ViT 进行图像分类

适用场景：
- 商品图片自动分类
- 内容审核图片识别
- 图片标签生成
"""
import modal
import io
import base64

app = modal.App("image-classification")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.0",
        "torchvision",
        "transformers",
        "Pillow",
    )
)

model_volume = modal.Volume.from_name("classifier-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume},
    timeout=300,
)
class ImageClassifier:
    @modal.enter()
    def load_model(self):
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        import torch
        
        print("🖼️ 加载图像分类模型...")
        
        # 使用 ViT 模型（也可以换成 ResNet）
        model_name = "google/vit-base-patch16-224"
        
        self.processor = AutoImageProcessor.from_pretrained(
            model_name,
            cache_dir="/models"
        )
        
        self.model = AutoModelForImageClassification.from_pretrained(
            model_name,
            cache_dir="/models"
        )
        self.model.to("cuda")
        self.model.eval()
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def classify(self, image_data: bytes, top_k: int = 5) -> list[dict]:
        """
        对图像进行分类
        
        Args:
            image_data: 图像二进制数据
            top_k: 返回前 k 个预测结果
        
        Returns:
            分类结果列表 [{"label": "cat", "score": 0.95}, ...]
        """
        from PIL import Image
        import torch
        
        # 加载图像
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # 预处理
        inputs = self.processor(img, return_tensors="pt").to("cuda")
        
        # 推理
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # 获取 top_k 结果
        top_probs, top_indices = probs[0].topk(top_k)
        
        results = []
        for prob, idx in zip(top_probs.cpu().numpy(), top_indices.cpu().numpy()):
            label = self.model.config.id2label[idx]
            results.append({
                "label": label,
                "score": float(prob)
            })
        
        return results
    
    @modal.method()
    def batch_classify(self, images: list[bytes], top_k: int = 5) -> list[list[dict]]:
        """批量分类图像"""
        results = []
        for img_data in images:
            result = self.classify(img_data, top_k)
            results.append(result)
        return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def classify_api(data: dict):
    """
    图像分类 API
    
    POST /classify_api
    {
        "image": "base64_encoded_image",
        "top_k": 5
    }
    """
    try:
        image_data = base64.b64decode(data.get("image", ""))
        top_k = data.get("top_k", 5)
        
        classifier = ImageClassifier()
        results = classifier.classify.remote(image_data, top_k)
        
        return {
            "status": "success",
            "predictions": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    """演示图像分类"""
    from PIL import Image
    
    print("🖼️ 图像分类服务")
    print("=" * 50)
    
    # 创建测试图像
    test_img = Image.new("RGB", (224, 224), color=(255, 100, 100))
    buffer = io.BytesIO()
    test_img.save(buffer, format="JPEG")
    
    classifier = ImageClassifier()
    results = classifier.classify.remote(buffer.getvalue(), top_k=3)
    
    print("\n分类结果:")
    for r in results:
        print(f"  {r['label']}: {r['score']:.2%}")
    
    print("\n💡 提示: 支持 ImageNet 1000 类分类")

