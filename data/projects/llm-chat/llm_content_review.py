"""
内容审核助手
业务场景：UGC 平台需要快速审核大量用户发布的内容

解决的问题：
- 每天数万条内容，人工审核不过来
- 违规内容影响平台安全和合规
- 审核标准不一致，质量难以保证

这个例子展示：
- 多维度内容安全检测
- 批量并行审核提升效率
- 自动分类和打标签
- 可疑内容标记人工复审
"""
import modal
import json
from datetime import datetime
from enum import Enum

app = modal.App("llm-content-review")

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

# 审核维度
REVIEW_DIMENSIONS = [
    "违法违规",      # 涉及违法内容
    "色情低俗",      # 色情、低俗内容
    "暴力血腥",      # 暴力、血腥描述
    "政治敏感",      # 政治敏感话题
    "广告营销",      # 未经授权的广告
    "虚假信息",      # 谣言、虚假信息
    "人身攻击",      # 侮辱、诽谤他人
    "隐私泄露",      # 包含个人隐私信息
]


@app.cls(
    image=image,
    gpu="A100",
    volumes={"/models": model_volume},
    timeout=600,
    container_idle_timeout=300,
)
class ContentReviewer:
    @modal.enter()
    def load_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("🔍 加载审核模型...")
        
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
    def review_content(self, content: str, content_type: str = "text") -> dict:
        """
        审核单条内容
        
        Args:
            content: 待审核内容
            content_type: 内容类型 (text/title/comment)
        
        Returns:
            审核结果
        """
        system_prompt = f"""你是一个内容安全审核专家。请分析以下{content_type}内容，检查是否存在违规问题。

审核维度：
{chr(10).join(f'- {dim}' for dim in REVIEW_DIMENSIONS)}

请按以下JSON格式返回结果：
{{
    "passed": true/false,
    "risk_level": "safe/low/medium/high",
    "violations": ["违规类型1", "违规类型2"],
    "reason": "简短说明",
    "suggestion": "处理建议"
}}

只返回JSON，不要其他内容。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请审核以下内容：\n\n{content}"}
        ]
        
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.1,  # 低温度确保输出稳定
            do_sample=True,
        )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        ).strip()
        
        # 解析 JSON 结果
        try:
            # 尝试提取 JSON
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                result = json.loads(json_str)
            else:
                result = {
                    "passed": True,
                    "risk_level": "safe",
                    "violations": [],
                    "reason": "无明显违规",
                    "suggestion": "可以通过"
                }
        except json.JSONDecodeError:
            result = {
                "passed": True,
                "risk_level": "low",
                "violations": [],
                "reason": "解析异常，默认通过",
                "suggestion": "建议人工复审"
            }
        
        result["content_preview"] = content[:50] + "..." if len(content) > 50 else content
        result["reviewed_at"] = datetime.now().isoformat()
        
        return result


@app.function(image=image, timeout=1200)
def batch_review(contents: list[dict]) -> dict:
    """
    批量审核内容
    
    Args:
        contents: 内容列表 [{"id": "1", "content": "...", "type": "text"}]
    
    Returns:
        批量审核结果
    """
    reviewer = ContentReviewer()
    
    results = {
        "total": len(contents),
        "passed": 0,
        "rejected": 0,
        "need_review": 0,
        "details": []
    }
    
    print(f"🔍 开始批量审核 {len(contents)} 条内容")
    
    for i, item in enumerate(contents, 1):
        print(f"  审核进度: {i}/{len(contents)}")
        
        review_result = reviewer.review_content.remote(
            content=item["content"],
            content_type=item.get("type", "text")
        )
        
        review_result["content_id"] = item.get("id", str(i))
        
        # 统计
        if review_result["passed"]:
            if review_result["risk_level"] in ["low", "medium"]:
                results["need_review"] += 1
            else:
                results["passed"] += 1
        else:
            results["rejected"] += 1
        
        results["details"].append(review_result)
    
    print(f"\n📊 审核完成:")
    print(f"   通过: {results['passed']}")
    print(f"   拒绝: {results['rejected']}")
    print(f"   需复审: {results['need_review']}")
    
    return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def review_api(data: dict):
    """
    内容审核 API
    
    POST /review_api
    {
        "content": "要审核的内容",
        "type": "text",  // text/title/comment
        "id": "content_123"
    }
    
    或批量审核：
    {
        "batch": [
            {"id": "1", "content": "内容1", "type": "text"},
            {"id": "2", "content": "内容2", "type": "comment"}
        ]
    }
    """
    if "batch" in data:
        result = batch_review.remote(data["batch"])
        return {"status": "success", "batch_result": result}
    else:
        reviewer = ContentReviewer()
        result = reviewer.review_content.remote(
            content=data.get("content", ""),
            content_type=data.get("type", "text")
        )
        result["content_id"] = data.get("id")
        return {"status": "success", "result": result}


@app.local_entrypoint()
def main():
    """演示内容审核"""
    print("🔍 内容审核助手演示")
    print("=" * 50)
    
    # 测试内容
    test_contents = [
        {"id": "1", "content": "今天天气真好，分享一下我的早餐照片~", "type": "text"},
        {"id": "2", "content": "这个产品太垃圾了，千万别买！骗子公司！", "type": "comment"},
        {"id": "3", "content": "关注我，免费领取iPhone15！加微信xxx", "type": "text"},
        {"id": "4", "content": "分享一个超实用的学习方法，帮助我提高了效率", "type": "text"},
    ]
    
    results = batch_review.remote(test_contents)
    
    print("\n📋 详细结果:")
    for detail in results["details"]:
        status = "✅ 通过" if detail["passed"] else "❌ 拒绝"
        print(f"\n{status} [{detail['content_id']}] {detail['content_preview']}")
        print(f"   风险等级: {detail['risk_level']}")
        if detail["violations"]:
            print(f"   违规类型: {', '.join(detail['violations'])}")
        print(f"   说明: {detail['reason']}")
    
    print("\n💡 提示:")
    print("1. 可根据业务调整 REVIEW_DIMENSIONS")
    print("2. 对接数据库记录审核结果")
    print("3. medium/high 风险建议人工复审")

