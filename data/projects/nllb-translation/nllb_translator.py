"""
NLLB 多语言翻译服务
使用 Meta 的 NLLB (No Language Left Behind) 模型进行翻译

优势：
- 支持 200+ 种语言互译
- 专门的翻译模型，效果优于通用 LLM
- 资源需求低，T4 显卡即可运行
- 推理速度快，成本低

适用场景：
- 多语言翻译服务
- 成本敏感的翻译任务
- 需要快速响应的翻译 API
"""
import modal

app = modal.App("nllb-translation")

# 轻量级镜像配置
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.36.0",
        "torch==2.1.0",
        "sentencepiece",
        "sacremoses",
    )
)

# 持久化存储模型
model_volume = modal.Volume.from_name("nllb-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",  # T4 显卡足够，成本低
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class NLLBTranslator:
    """NLLB 翻译服务类"""
    
    @modal.enter()
    def load_model(self):
        """加载 NLLB 模型"""
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch
        
        print("🌍 加载 NLLB 翻译模型...")
        
        # 使用 NLLB-200-distilled-600M 版本（轻量级）
        # 如需更高质量可用 NLLB-200-1.3B 或 NLLB-200-3.3B
        model_name = "facebook/nllb-200-distilled-600M"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir="/models",
            src_lang="zho_Hans"  # 默认源语言：简体中文
        )
        
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            cache_dir="/models",
        ).to("cuda")
        
        # 常用语言代码映射
        self.lang_codes = {
            "zh": "zho_Hans",      # 简体中文
            "zh-tw": "zho_Hant",   # 繁体中文
            "en": "eng_Latn",      # 英语
            "ja": "jpn_Jpan",      # 日语
            "ko": "kor_Hang",      # 韩语
            "fr": "fra_Latn",      # 法语
            "de": "deu_Latn",      # 德语
            "es": "spa_Latn",      # 西班牙语
            "ru": "rus_Cyrl",      # 俄语
            "ar": "arb_Arab",      # 阿拉伯语
            "pt": "por_Latn",      # 葡萄牙语
            "it": "ita_Latn",      # 意大利语
            "th": "tha_Thai",      # 泰语
            "vi": "vie_Latn",      # 越南语
            "id": "ind_Latn",      # 印尼语
        }
        
        print("✓ NLLB 模型加载完成")
    
    @modal.method()
    def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        max_length: int = 512
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（如 zh, en, ja）
            target_lang: 目标语言代码
            max_length: 最大生成长度
            
        Returns:
            翻译后的文本
        """
        # 转换语言代码
        src_code = self.lang_codes.get(source_lang, source_lang)
        tgt_code = self.lang_codes.get(target_lang, target_lang)
        
        # 设置源语言
        self.tokenizer.src_lang = src_code
        
        # 编码输入
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to("cuda")
        
        # 生成翻译
        translated_tokens = self.model.generate(
            **inputs,
            forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_code],
            max_length=max_length,
            num_beams=5,  # 使用 beam search 提高质量
            early_stopping=True
        )
        
        # 解码输出
        translation = self.tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True
        )[0]
        
        return translation.strip()
    
    @modal.method()
    def batch_translate(
        self,
        texts: list[str],
        source_lang: str = "zh",
        target_lang: str = "en"
    ) -> list[str]:
        """
        批量翻译
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            翻译结果列表
        """
        results = []
        for text in texts:
            translation = self.translate(text, source_lang, target_lang)
            results.append(translation)
        return results


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
    
    或批量翻译：
    {
        "texts": ["你好", "世界"],
        "source_lang": "zh",
        "target_lang": "en"
    }
    """
    translator = NLLBTranslator()
    
    # 批量翻译
    if "texts" in data:
        translations = translator.batch_translate.remote(
            texts=data["texts"],
            source_lang=data.get("source_lang", "zh"),
            target_lang=data.get("target_lang", "en")
        )
        return {
            "translations": translations,
            "count": len(translations)
        }
    
    # 单条翻译
    translation = translator.translate.remote(
        text=data["text"],
        source_lang=data.get("source_lang", "zh"),
        target_lang=data.get("target_lang", "en")
    )
    
    return {
        "translation": translation,
        "source_lang": data.get("source_lang", "zh"),
        "target_lang": data.get("target_lang", "en")
    }


@app.local_entrypoint()
def main():
    """测试翻译功能"""
    translator = NLLBTranslator()
    
    print("\n=== NLLB 翻译测试 ===\n")
    
    # 测试 1: 中译英
    text_zh = "人工智能正在改变世界，机器学习让计算机能够从数据中学习。"
    result_en = translator.translate.remote(text_zh, "zh", "en")
    print(f"中文: {text_zh}")
    print(f"英文: {result_en}\n")
    
    # 测试 2: 英译日
    text_en = "Machine learning is a subset of artificial intelligence."
    result_ja = translator.translate.remote(text_en, "en", "ja")
    print(f"English: {text_en}")
    print(f"日本語: {result_ja}\n")
    
    # 测试 3: 中译法
    text_zh2 = "今天天气很好。"
    result_fr = translator.translate.remote(text_zh2, "zh", "fr")
    print(f"中文: {text_zh2}")
    print(f"Français: {result_fr}\n")
    
    # 测试 4: 批量翻译
    texts = [
        "你好",
        "谢谢",
        "再见"
    ]
    results = translator.batch_translate.remote(texts, "zh", "en")
    print("批量翻译:")
    for zh, en in zip(texts, results):
        print(f"  {zh} -> {en}")
    
    print("\n✓ 测试完成")
