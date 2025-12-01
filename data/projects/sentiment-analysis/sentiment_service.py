"""
情感分析服务
分析文本情感倾向（正面/负面/中性）

适用场景：
- 用户评论分析
- 舆情监控
- 客户反馈处理
"""
import modal

app = modal.App("sentiment-analysis")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers",
        "torch==2.1.0",
    )
)

model_volume = modal.Volume.from_name("sentiment-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume},
    timeout=300,
)
class SentimentAnalyzer:
    @modal.enter()
    def load_model(self):
        from transformers import pipeline
        
        print("😊 加载情感分析模型...")
        
        # 中文情感分析模型
        self.classifier = pipeline(
            "sentiment-analysis",
            model="uer/roberta-base-finetuned-jd-binary-chinese",
            model_kwargs={"cache_dir": "/models"},
            device=0
        )
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def analyze(self, text: str) -> dict:
        """
        分析单条文本的情感
        
        Args:
            text: 待分析文本
        
        Returns:
            {"label": "positive/negative", "score": 0.95}
        """
        result = self.classifier(text[:512])[0]  # 限制长度
        
        # 映射标签
        label_map = {
            "positive": "正面",
            "negative": "负面",
            "LABEL_0": "负面",
            "LABEL_1": "正面"
        }
        
        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "label": label_map.get(result["label"], result["label"]),
            "score": result["score"]
        }
    
    @modal.method()
    def batch_analyze(self, texts: list[str]) -> list[dict]:
        """批量分析文本情感"""
        results = []
        for text in texts:
            result = self.analyze(text)
            results.append(result)
        return results
    
    @modal.method()
    def analyze_with_summary(self, texts: list[str]) -> dict:
        """
        批量分析并生成汇总报告
        """
        results = self.batch_analyze(texts)
        
        positive_count = sum(1 for r in results if "正面" in r["label"])
        negative_count = sum(1 for r in results if "负面" in r["label"])
        
        return {
            "total": len(results),
            "positive": positive_count,
            "negative": negative_count,
            "positive_ratio": positive_count / len(results) if results else 0,
            "details": results
        }


@app.function(image=image)
@modal.web_endpoint(method="POST")
def sentiment_api(data: dict):
    """
    情感分析 API
    
    POST /sentiment_api
    {
        "text": "这个产品太棒了！",
        // 或批量:
        "texts": ["评论1", "评论2"]
    }
    """
    analyzer = SentimentAnalyzer()
    
    try:
        if "texts" in data:
            result = analyzer.analyze_with_summary.remote(data["texts"])
        else:
            result = analyzer.analyze.remote(data.get("text", ""))
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    """演示情感分析"""
    print("😊 情感分析服务")
    print("=" * 50)
    
    test_texts = [
        "这个产品质量非常好，下次还会购买！",
        "发货太慢了，等了一个星期才到",
        "包装一般，但是东西还可以",
        "客服态度很好，帮我解决了问题",
        "完全不值这个价格，太失望了",
    ]
    
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze_with_summary.remote(test_texts)
    
    print(f"\n📊 分析汇总:")
    print(f"   总计: {result['total']} 条")
    print(f"   正面: {result['positive']} ({result['positive_ratio']:.1%})")
    print(f"   负面: {result['negative']}")
    
    print(f"\n📝 详细结果:")
    for r in result["details"]:
        emoji = "👍" if "正面" in r["label"] else "👎"
        print(f"   {emoji} [{r['label']}] {r['text'][:30]}...")
    
    print("\n💡 提示: 适合中文评论/反馈分析")

