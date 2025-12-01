"""
智能客服机器人
业务场景：电商/SaaS 平台需要 24/7 响应客户咨询

解决的问题：
- 人工客服成本高，每月支出数十万
- 夜间和节假日无法响应，流失潜在客户
- 重复问题占比 80%，人工回答效率低

这个例子展示：
- 基于企业知识库的问答
- 多轮对话上下文管理
- 自动识别需要转人工的场景
- 对话记录存储与分析
"""
import modal
import json
from datetime import datetime

app = modal.App("llm-customer-service")

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
conversation_dict = modal.Dict.from_name("cs-conversations", create_if_missing=True)

# 企业知识库（实际场景中从数据库或向量库获取）
KNOWLEDGE_BASE = {
    "退款政策": "我们支持7天无理由退款。请在订单详情页提交退款申请，审核通过后3-5个工作日到账。",
    "发货时间": "订单支付成功后，我们会在24小时内发货。偏远地区可能需要48小时。",
    "运费规则": "满99元包邮，不满99元收取10元运费。偏远地区（新疆、西藏、青海）需额外支付20元。",
    "会员权益": "会员可享受：1. 专属9折优惠 2. 每月10元无门槛券 3. 优先发货 4. 专属客服通道",
    "支付方式": "支持微信支付、支付宝、银行卡、花呗分期等多种支付方式。",
    "换货流程": "收到商品7天内，商品未使用且包装完好，可申请换货。请联系客服获取换货地址。",
}

# 需要转人工的关键词
ESCALATION_KEYWORDS = ["投诉", "经理", "人工", "退款失败", "骗子", "举报", "工商", "律师"]


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class CustomerServiceBot:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🤖 加载客服模型...")
        
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
    
    def search_knowledge(self, query: str) -> str:
        """在知识库中搜索相关信息"""
        query_lower = query.lower()
        
        # 简单关键词匹配（实际场景用向量搜索）
        for topic, answer in KNOWLEDGE_BASE.items():
            if any(kw in query_lower for kw in topic.lower().split()):
                return f"【知识库】{topic}：{answer}"
        
        return ""
    
    def check_escalation(self, message: str) -> bool:
        """检查是否需要转人工"""
        return any(kw in message for kw in ESCALATION_KEYWORDS)
    
    @modal.method()
    def chat(
        self,
        session_id: str,
        user_message: str,
        history: list[dict] = None
    ) -> dict:
        """
        处理客服对话
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            history: 对话历史
        
        Returns:
            回复和状态信息
        """
        if history is None:
            history = []
        
        # 检查是否需要转人工
        if self.check_escalation(user_message):
            return {
                "response": "非常抱歉给您带来不便，我已为您转接人工客服，请稍候...",
                "status": "escalated",
                "reason": "检测到需要人工处理的关键词"
            }
        
        # 搜索知识库
        knowledge = self.search_knowledge(user_message)
        
        # 构建系统提示
        system_prompt = """你是一个专业、友好的客服助手。请遵循以下规则：
1. 回答要简洁明了，控制在100字以内
2. 对客户保持礼貌和耐心
3. 如果有相关知识库内容，优先使用知识库回答
4. 如果无法解答，诚实告知并建议联系人工客服
5. 不要编造信息"""
        
        if knowledge:
            system_prompt += f"\n\n参考信息：\n{knowledge}"
        
        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-6:])  # 保留最近 3 轮对话
        messages.append({"role": "user", "content": user_message})
        
        # 生成回复
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        ).strip()
        
        return {
            "response": response,
            "status": "bot_replied",
            "knowledge_used": bool(knowledge)
        }


@app.function(image=image)
def save_conversation(session_id: str, message: dict):
    """保存对话记录"""
    history = conversation_dict.get(session_id, [])
    history.append({
        **message,
        "timestamp": datetime.now().isoformat()
    })
    conversation_dict[session_id] = history


@app.function(image=image)
@modal.web_endpoint(method="POST")
def customer_service_api(data: dict):
    """
    客服 API 端点
    
    POST /customer_service_api
    {
        "session_id": "user_12345",
        "message": "请问怎么退款？",
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """
    session_id = data.get("session_id", "anonymous")
    user_message = data.get("message", "")
    history = data.get("history", [])
    
    bot = CustomerServiceBot()
    result = bot.chat.remote(session_id, user_message, history)
    
    # 保存对话
    save_conversation.remote(session_id, {
        "role": "user",
        "content": user_message
    })
    save_conversation.remote(session_id, {
        "role": "assistant",
        "content": result["response"],
        "status": result["status"]
    })
    
    return {
        "session_id": session_id,
        "reply": result["response"],
        "status": result["status"],
        "knowledge_used": result.get("knowledge_used", False)
    }


@app.local_entrypoint()
def main():
    """模拟客服对话"""
    print("🤖 智能客服机器人演示")
    print("=" * 50)
    
    bot = CustomerServiceBot()
    
    # 测试对话
    test_conversations = [
        "你好，请问怎么退款？",
        "需要多久到账？",
        "运费怎么算？",
        "我要投诉！",  # 触发转人工
    ]
    
    history = []
    session_id = "test_session"
    
    for user_msg in test_conversations:
        print(f"\n👤 用户: {user_msg}")
        
        result = bot.chat.remote(session_id, user_msg, history)
        
        print(f"🤖 客服: {result['response']}")
        print(f"   状态: {result['status']}")
        
        if result["status"] == "escalated":
            print("   ⚠️ 已转人工客服")
            break
        
        # 更新历史
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": result["response"]})
    
    print("\n💡 提示:")
    print("1. 更新 KNOWLEDGE_BASE 添加企业知识库")
    print("2. 对接向量数据库实现语义搜索")
    print("3. 集成到现有客服系统（如网页聊天组件）")

