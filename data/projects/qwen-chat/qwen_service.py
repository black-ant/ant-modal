"""
Qwen 通义千问对话服务
部署阿里通义千问大模型，支持对话和文本生成

适用场景：
- 需要中文能力强的对话服务
- 阿里云生态系统集成
- 需要长上下文支持
"""
import modal

app = modal.App("qwen-chat")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.40.0",
        "torch==2.1.0",
        "accelerate",
        "bitsandbytes",
        "tiktoken",
    )
)

model_volume = modal.Volume.from_name("qwen-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class QwenChat:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 Qwen 模型...")
        
        # Qwen2-7B-Instruct 或 Qwen1.5-14B-Chat
        model_name = "Qwen/Qwen2-7B-Instruct"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir="/models",
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            cache_dir="/models",
            trust_remote_code=True,
            load_in_8bit=True,
        )
        
        print("✓ Qwen 模型加载完成")
    
    @modal.method()
    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        对话生成
        
        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            max_tokens: 最大生成长度
            temperature: 温度参数
            top_p: nucleus sampling 参数
        """
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
        )
        
        generated_ids = outputs[0][len(inputs.input_ids[0]):]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        return response.strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_api(data: dict):
    """
    OpenAI 兼容的聊天 API
    
    POST /chat_api
    {
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 1024,
        "temperature": 0.7
    }
    """
    qwen = QwenChat()
    
    response = qwen.chat.remote(
        messages=data.get("messages", []),
        max_tokens=data.get("max_tokens", 1024),
        temperature=data.get("temperature", 0.7),
        top_p=data.get("top_p", 0.9)
    )
    
    return {
        "choices": [{
            "message": {"role": "assistant", "content": response}
        }],
        "model": "qwen2-7b-instruct"
    }


@app.local_entrypoint()
def main(prompt: str = "请介绍一下你自己"):
    qwen = QwenChat()
    
    messages = [
        {"role": "system", "content": "你是通义千问，一个由阿里云开发的AI助手。"},
        {"role": "user", "content": prompt}
    ]
    
    response = qwen.chat.remote(messages=messages)
    print(f"\n🤖 Qwen: {response}\n")

