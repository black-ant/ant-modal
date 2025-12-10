"""
Opus-MT 轻量级翻译服务
使用 Helsinki-NLP 的 Opus-MT 模型进行翻译

优势：
- 极轻量级，模型仅 300MB 左右
- CPU 即可运行，无需 GPU（可选 GPU 加速）
- 推理速度极快
- 成本极低

适用场景：
- 预算有限的翻译服务
- 特定语言对的高频翻译
- 需要极快响应的场景
"""
import modal

app = modal.App("opus-mt-translation")

# 轻量级镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.36.0",
        "torch==2.1.0",
        "sentencepiece",
    )
)

model_volume = modal.Volume.from_name("opus-models", create_if_missing=True)


@app.cls(
    image=image,
    cpu=2.0,  # 使用 CPU，成本更低
    # gpu="T4",  # 如需更快速度可启用 GPU
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class OpusMTTranslator:
    """Opus-MT 翻译服务类"""
    
    @modal.enter()
    def load_models(self):
        """加载常用语言对的模型"""
        from transformers import MarianMTModel, MarianTokenizer
        
        print("🚀 加载 Opus-MT 翻译模型...")
        
        # 预加载常用语言对模型
        self.models = {}
        self.tokenizers = {}
        
        # 定义常用语言对
        language_pairs = [
            ("zh", "en"),  # 中译英
            ("en", "zh"),  # 英译中
            ("zh", "ja"),  # 中译日
            ("ja", "zh"),  # 日译中
            ("en", "ja"),  # 英译日
            ("ja", "en"),  # 日译英
        ]
        
        for src, tgt in language_pairs:
            model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
            try:
                print(f"  加载 {src}->{tgt} 模型...")
                tokenizer = MarianTokenizer.from_pretrained(
                    model_name,
                    cache_dir="/models"
                )
                model = MarianMTModel.from_pretrained(
                    model_name,
                    cache_dir="/models"
                )
                
                # 如果使用 GPU，移动到 GPU
                # model = model.to("cuda")
                
                self.models[f"{src}-{tgt}"] = model
                self.tokenizers[f"{src}-{tgt}"] = tokenizer
                print(f"  ✓ {src}->{tgt} 加载完成")
            except Exception as e:
                print(f"  ⚠ {src}->{tgt} 加载失败: {e}")
        
        print("✓ Opus-MT 模型加载完成")
    
    @modal.method()
    def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en"
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（zh, en, ja 等）
            target_lang: 目标语言代码
            
        Returns:
            翻译后的文本
        """
        pair_key = f"{source_lang}-{target_lang}"
        
        if pair_key not in self.models:
            return f"错误: 不支持 {source_lang} -> {target_lang} 翻译对"
        
        tokenizer = self.tokenizers[pair_key]
        model = self.models[pair_key]
        
        # 编码
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        
        # 如果使用 GPU
        # inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # 翻译
        translated = model.generate(**inputs, max_length=512)
        
        # 解码
        result = tokenizer.decode(translated[0], skip_special_tokens=True)
        
        return result.strip()
    
    @modal.method()
    def batch_translate(
        self,
        texts: list[str],
        source_lang: str = "zh",
        target_lang: str = "en"
    ) -> list[str]:
        """
        批量翻译（更高效）
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            翻译结果列表
        """
        pair_key = f"{source_lang}-{target_lang}"
        
        if pair_key not in self.models:
            return [f"错误: 不支持 {source_lang} -> {target_lang}"] * len(texts)
        
        tokenizer = self.tokenizers[pair_key]
        model = self.models[pair_key]
        
        # 批量编码
        inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
        
        # 批量翻译
        translated = model.generate(**inputs, max_length=512)
        
        # 批量解码
        results = [
            tokenizer.decode(t, skip_special_tokens=True)
            for t in translated
        ]
        
        return [r.strip() for r in results]
    
    @modal.method()
    def get_supported_pairs(self) -> list[str]:
        """获取支持的语言对列表"""
        return list(self.models.keys())


@app.function(image=image)
@modal.web_endpoint(method="POST")
def translate_api(data: dict):
    """
    翻译 API 端点
    
    POST /translate_api
    {
        "text": "你好，世界！",
        "source_lang": "zh",
        "target_lang": "en"
    }
    """
    translator = OpusMTTranslator()
    
    # 批量翻译
    if "texts" in data:
        translations = translator.batch_translate.remote(
            texts=data["texts"],
            source_lang=data.get("source_lang", "zh"),
            target_lang=data.get("target_lang", "en")
        )
        return {"translations": translations}
    
    # 单条翻译
    translation = translator.translate.remote(
        text=data["text"],
        source_lang=data.get("source_lang", "zh"),
        target_lang=data.get("target_lang", "en")
    )
    
    return {"translation": translation}


@app.function(image=image)
@modal.web_endpoint(method="GET")
def supported_languages():
    """获取支持的语言对"""
    translator = OpusMTTranslator()
    pairs = translator.get_supported_pairs.remote()
    return {"supported_pairs": pairs}


@app.local_entrypoint()
def main():
    """测试翻译功能"""
    translator = OpusMTTranslator()
    
    print("\n=== Opus-MT 翻译测试 ===\n")
    
    # 显示支持的语言对
    pairs = translator.get_supported_pairs.remote()
    print(f"支持的语言对: {', '.join(pairs)}\n")
    
    # 测试 1: 中译英
    text_zh = "人工智能正在改变世界。"
    result_en = translator.translate.remote(text_zh, "zh", "en")
    print(f"中文: {text_zh}")
    print(f"英文: {result_en}\n")
    
    # 测试 2: 英译中
    text_en = "Machine learning is amazing."
    result_zh = translator.translate.remote(text_en, "en", "zh")
    print(f"English: {text_en}")
    print(f"中文: {result_zh}\n")
    
    # 测试 3: 批量翻译
    texts = [
        "你好",
        "谢谢",
        "再见",
        "早上好"
    ]
    results = translator.batch_translate.remote(texts, "zh", "en")
    print("批量翻译:")
    for zh, en in zip(texts, results):
        print(f"  {zh} -> {en}")
    
    print("\n✓ 测试完成")
