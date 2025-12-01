"""
Yi 零一万物对话服务
部署零一万物 Yi 系列大模型

适用场景：
- 需要双语（中英文）能力
- 长上下文场景（Yi 支持 200K 上下文）
- 高质量文本生成
"""
import modal

app = modal.App("yi-chat")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.40.0",
        "torch==2.1.0",
        "accelerate",
        "bitsandbytes",
        "sentencepiece",
    )
)

model_volume = modal.Volume.from_name("yi-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class YiChat:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 Yi 模型...")
        model_name = "01-ai/Yi-1.5-9B-Chat"
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir="/models", trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float16, device_map="auto", cache_dir="/models", trust_remote_code=True, load_in_8bit=True
        )
        print("✓ Yi 模型加载完成")
    
    @modal.method()
    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7) -> str:
        input_ids = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)
        
        outputs = self.model.generate(
            input_ids, max_new_tokens=max_tokens, temperature=temperature, do_sample=True, eos_token_id=self.tokenizer.eos_token_id
        )
        return self.tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True).strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_api(data: dict):
    yi = YiChat()
    response = yi.chat.remote(messages=data.get("messages", []), max_tokens=data.get("max_tokens", 1024))
    return {"choices": [{"message": {"role": "assistant", "content": response}}], "model": "yi-1.5-9b"}


@app.local_entrypoint()
def main(prompt: str = "你好"):
    yi = YiChat()
    response = yi.chat.remote(messages=[{"role": "user", "content": prompt}])
    print(f"\n🤖 Yi: {response}\n")

