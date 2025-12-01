"""
LLM 对话服务
使用 Llama 3 或其他开源大语言模型提供对话服务
"""
import modal

app = modal.App("llm-chat")

# 构建镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers==4.36.0",
        "torch==2.1.0",
        "accelerate",
        "bitsandbytes",  # 用于量化
    )
)

# 模型缓存
model_volume = modal.Volume.from_name("llm-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A100",  # Llama 3 需要较大显存
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class LLMChat:
    @modal.enter()
    def load_model(self):
        """加载 Llama 3 模型"""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载 Llama 3 模型...")
        
        model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir="/models"
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            cache_dir="/models",
            load_in_8bit=True,  # 8bit 量化节省显存
        )
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 512,
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
        
        Returns:
            模型回复
        """
        # 应用聊天模板
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        print(f"💬 生成回复...")
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
        )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        print(f"✓ 回复生成完成")
        return response.strip()


@app.function(image=image)
@modal.web_endpoint(method="POST")
def chat_completion(data: dict):
    """
    OpenAI 兼容的聊天 API
    
    POST /chat_completion
    {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    """
    llm = LLMChat()
    
    response = llm.chat.remote(
        messages=data.get("messages", []),
        max_tokens=data.get("max_tokens", 512),
        temperature=data.get("temperature", 0.7),
        top_p=data.get("top_p", 0.9)
    )
    
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": response
            }
        }]
    }


@app.local_entrypoint()
def main(prompt: str = "介绍一下人工智能"):
    """
    本地测试
    
    使用方法:
    modal run llm_service.py --prompt="你的问题"
    """
    llm = LLMChat()
    
    messages = [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": prompt}
    ]
    
    response = llm.chat.remote(messages=messages)
    print(f"\n🤖 回复:\n{response}\n")
