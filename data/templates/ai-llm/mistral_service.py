"""
Mistral/Mixtral 对话服务
部署 Mistral 或 Mixtral MoE 模型

适用场景：
- 需要高性能推理
- 英文为主的对话场景
- MoE 架构的高效计算
"""
import modal

app = modal.App("mistral-chat")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.40.0",
        "torch==2.1.0",
        "accelerate",
        "bitsandbytes",
    )
)

model_volume = modal.Volume.from_name("mistral-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class MistralChat:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 Mistral 模型...")
        model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir="/models")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float16, device_map="auto", cache_dir="/models", load_in_8bit=True
        )
        print("✓ Mistral 模型加载完成")
    
    @modal.method()
    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7) -> str:
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"[INST] {msg['content']} [/INST]"
            elif msg["role"] == "assistant":
                prompt += f" {msg['content']}</s>"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs, max_new_tokens=max_tokens, temperature=temperature, do_sample=True, pad_token_id=self.tokenizer.eos_token_id
        )
        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_api(data: dict):
    mistral = MistralChat()
    response = mistral.chat.remote(messages=data.get("messages", []), max_tokens=data.get("max_tokens", 1024))
    return {"choices": [{"message": {"role": "assistant", "content": response}}], "model": "mistral-7b"}


@app.local_entrypoint()
def main(prompt: str = "Hello"):
    mistral = MistralChat()
    response = mistral.chat.remote(messages=[{"role": "user", "content": prompt}])
    print(f"\n🤖 Mistral: {response}\n")

