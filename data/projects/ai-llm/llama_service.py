"""
Llama 3 对话服务
使用 Meta Llama 3 提供对话服务

适用场景：
- 通用对话和问答
- OpenAI 兼容 API
- 英文为主的场景
"""
import modal

app = modal.App("llama-chat")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.36.0",
        "torch==2.1.0",
        "accelerate",
        "bitsandbytes",
    )
)

model_volume = modal.Volume.from_name("llm-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class LlamaChat:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 Llama 3 模型...")
        
        model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir="/models"
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            cache_dir="/models",
            load_in_8bit=True,
        )
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def chat(self, messages: list[dict], max_tokens: int = 512, temperature: float = 0.7) -> str:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(**inputs, max_new_tokens=max_tokens, temperature=temperature, do_sample=True)
        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        return response.strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_api(data: dict):
    llm = LlamaChat()
    response = llm.chat.remote(
        messages=data.get("messages", []),
        max_tokens=data.get("max_tokens", 512),
        temperature=data.get("temperature", 0.7)
    )
    return {"choices": [{"message": {"role": "assistant", "content": response}}], "model": "llama-3-8b"}


@app.local_entrypoint()
def main(prompt: str = "Hello"):
    llm = LlamaChat()
    response = llm.chat.remote(messages=[{"role": "user", "content": prompt}])
    print(f"\n🤖 Llama: {response}\n")

