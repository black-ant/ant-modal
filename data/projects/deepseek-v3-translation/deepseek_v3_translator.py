import modal

app = modal.App("deepseek-v3-translation")

# 定义镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.0",
        "transformers==4.36.0",
        "accelerate",
        "bitsandbytes",  # 用于INT4量化
    )
)


@app.cls(
    image=image,
    gpu="H100",  # 或 "A100:2" 表示2个A100
    timeout=600,
    scaledown_window=300,
)
class DeepSeekV3Translator:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            "deepseek-ai/DeepSeek-V3",
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            "deepseek-ai/DeepSeek-V3",
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True,
            # load_in_4bit=True,  # 如果用A100可启用
        )

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
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)
        
        outputs = self.model.generate(
            inputs,
            max_new_tokens=2048,
            temperature=0.3,
            do_sample=True,
            top_p=0.95,
        )
        
        result = self.tokenizer.decode(
            outputs[0][len(inputs[0]):],
            skip_special_tokens=True
        )
        
        return result.strip()


# 使用示例
@app.local_entrypoint()
def main():
    translator = DeepSeekV3Translator()
    
    # 中译英
    result = translator.translate.remote(
        "人工智能正在改变世界",
        source_lang="Chinese",
        target_lang="English"
    )
    print(f"翻译结果: {result}")
