"""
ChatGLM 智谱对话服务
部署智谱 GLM 系列模型，支持中文对话

适用场景：
- 需要优秀中文理解能力
- 代码生成和分析
- 多轮对话场景
"""
import modal

app = modal.App("chatglm-chat")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.40.0",
        "torch==2.1.0",
        "accelerate",
        "sentencepiece",
    )
)

model_volume = modal.Volume.from_name("chatglm-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class ChatGLM:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 ChatGLM 模型...")
        model_name = "THUDM/glm-4-9b-chat"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir="/models", trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            cache_dir="/models",
            trust_remote_code=True,
        )
        self.model.eval()
        print("✓ ChatGLM 模型加载完成")
    
    @modal.method()
    def chat(self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7) -> str:
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_tensors="pt", return_dict=True
        ).to(self.model.device)
        
        import torch
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=True, temperature=temperature)
            outputs = outputs[:, inputs['input_ids'].shape[1]:]
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_api(data: dict):
    glm = ChatGLM()
    response = glm.chat.remote(messages=data.get("messages", []), max_tokens=data.get("max_tokens", 1024))
    return {"choices": [{"message": {"role": "assistant", "content": response}}], "model": "glm-4-9b"}


@app.local_entrypoint()
def main(prompt: str = "你好"):
    glm = ChatGLM()
    response = glm.chat.remote(messages=[{"role": "user", "content": prompt}])
    print(f"\n🤖 ChatGLM: {response}\n")

