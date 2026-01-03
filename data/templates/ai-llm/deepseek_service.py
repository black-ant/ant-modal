"""
DeepSeek V3 翻译服务
部署 DeepSeek V3 模型进行翻译任务

适用场景：
- 高质量机器翻译
- 中英文互译
- 多语言支持
"""
import modal

app = modal.App("deepseek-v3-translation")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.0",
        "transformers==4.36.0",
        "accelerate",
        "bitsandbytes",
    )
)


@app.cls(
    image=image,
    gpu="H100",
    timeout=600,
    container_idle_timeout=300,
)
class DeepSeekV3Translator:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print("🤖 加载 DeepSeek V3 模型...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            "deepseek-ai/DeepSeek-V3",
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            "deepseek-ai/DeepSeek-V3",
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True,
        )
        
        print("✓ DeepSeek V3 模型加载完成")

    @modal.method()
    def translate(
        self, 
        text: str, 
        source_lang: str = "Chinese",
        target_lang: str = "English"
    ) -> str:
        prompt = f"""Translate the following {source_lang} text to {target_lang}. Only output the translation, no explanations.

{source_lang}: {text}
{target_lang}:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)
        
        outputs = self.model.generate(
            inputs, max_new_tokens=2048, temperature=0.3, do_sample=True, top_p=0.95
        )
        
        result = self.tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
        return result.strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def translate_api(data: dict):
    translator = DeepSeekV3Translator()
    result = translator.translate.remote(
        text=data.get("text", ""),
        source_lang=data.get("source_lang", "Chinese"),
        target_lang=data.get("target_lang", "English")
    )
    return {"status": "success", "translation": result}


@app.local_entrypoint()
def main():
    translator = DeepSeekV3Translator()
    result = translator.translate.remote("人工智能正在改变世界")
    print(f"翻译结果: {result}")

