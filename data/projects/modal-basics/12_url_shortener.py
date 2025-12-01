"""
12 - 短链接生成与追踪服务
业务场景：营销活动需要可追踪的短链接

解决的问题：
- 营销链接太长，在短信/社交媒体中显示不友好
- 无法追踪链接的点击数据和来源
- 需要随时查看链接的访问统计

这个例子展示：
- Web API 创建和访问短链接
- Dict 存储链接映射
- 访问统计和追踪
- 重定向功能实现
"""
import modal
import hashlib
import json
from datetime import datetime
from fastapi import Response
from fastapi.responses import RedirectResponse

app = modal.App("url-shortener")

# 使用 Dict 存储短链接映射
url_mapping = modal.Dict.from_name("url-mappings", create_if_missing=True)
click_stats = modal.Dict.from_name("url-click-stats", create_if_missing=True)


def generate_short_code(url: str, length: int = 6) -> str:
    """
    生成短链接码
    使用 URL 的 MD5 哈希的前 N 位
    """
    hash_obj = hashlib.md5(url.encode())
    return hash_obj.hexdigest()[:length]


@app.function()
@modal.web_endpoint(method="POST")
def create_short_url(request: dict) -> dict:
    """
    POST /create_short_url
    创建短链接
    
    请求格式：
    {
        "url": "https://example.com/very/long/url/here",
        "custom_code": "optional-custom-code",  // 可选
        "campaign": "summer-sale"  // 可选，用于追踪来源
    }
    
    响应格式：
    {
        "status": "success",
        "short_code": "abc123",
        "short_url": "https://your-app--redirect.modal.run/abc123",
        "original_url": "..."
    }
    """
    original_url = request.get("url")
    if not original_url:
        return {"status": "error", "message": "URL is required"}
    
    # 检查是否提供自定义短码
    custom_code = request.get("custom_code")
    if custom_code:
        # 检查自定义码是否已被使用
        existing = url_mapping.get(custom_code)
        if existing and existing["url"] != original_url:
            return {"status": "error", "message": "Custom code already in use"}
        short_code = custom_code
    else:
        short_code = generate_short_code(original_url)
    
    # 存储映射
    url_data = {
        "url": original_url,
        "created_at": datetime.now().isoformat(),
        "campaign": request.get("campaign", "default"),
        "clicks": 0
    }
    url_mapping[short_code] = url_data
    
    # 初始化点击统计
    click_stats[short_code] = {
        "total_clicks": 0,
        "daily_clicks": {},
        "referrers": {},
        "user_agents": {}
    }
    
    return {
        "status": "success",
        "short_code": short_code,
        "short_url": f"https://your-modal-app--redirect.modal.run/{short_code}",
        "original_url": original_url,
        "campaign": request.get("campaign", "default")
    }


@app.function()
@modal.web_endpoint(method="GET")
def redirect(code: str, referer: str = "", user_agent: str = "") -> Response:
    """
    GET /redirect?code=abc123
    访问短链接，重定向到原始 URL
    
    同时记录访问统计
    """
    url_data = url_mapping.get(code)
    
    if not url_data:
        return Response(
            content="Short URL not found",
            status_code=404
        )
    
    # 更新访问统计
    stats = click_stats.get(code, {
        "total_clicks": 0,
        "daily_clicks": {},
        "referrers": {},
        "user_agents": {}
    })
    
    # 总点击数
    stats["total_clicks"] += 1
    
    # 按日统计
    today = datetime.now().strftime("%Y-%m-%d")
    stats["daily_clicks"][today] = stats["daily_clicks"].get(today, 0) + 1
    
    # 来源统计
    if referer:
        stats["referrers"][referer] = stats["referrers"].get(referer, 0) + 1
    
    # 保存统计
    click_stats[code] = stats
    
    # 更新映射中的点击数
    url_data["clicks"] = stats["total_clicks"]
    url_mapping[code] = url_data
    
    # 执行重定向
    return RedirectResponse(url=url_data["url"], status_code=302)


@app.function()
@modal.web_endpoint(method="GET")
def get_stats(code: str) -> dict:
    """
    GET /get_stats?code=abc123
    获取短链接的访问统计
    """
    url_data = url_mapping.get(code)
    if not url_data:
        return {"status": "error", "message": "Short URL not found"}
    
    stats = click_stats.get(code, {})
    
    return {
        "status": "success",
        "short_code": code,
        "original_url": url_data["url"],
        "campaign": url_data.get("campaign", "default"),
        "created_at": url_data["created_at"],
        "statistics": {
            "total_clicks": stats.get("total_clicks", 0),
            "daily_clicks": stats.get("daily_clicks", {}),
            "top_referrers": dict(sorted(
                stats.get("referrers", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }
    }


@app.function()
@modal.web_endpoint(method="GET")
def list_urls(campaign: str = "") -> dict:
    """
    GET /list_urls?campaign=summer-sale
    列出所有短链接（可按活动筛选）
    """
    # 注意：Dict 没有直接遍历所有 key 的方法
    # 实际场景中建议使用数据库或 Volume 存储
    # 这里返回使用说明
    return {
        "status": "info",
        "message": "使用 get_stats?code=xxx 查看单个链接统计",
        "tip": "生产环境建议使用数据库存储以支持列表查询"
    }


@app.local_entrypoint()
def main():
    """
    演示短链接服务
    
    使用方法：
    - 测试运行：modal run 12_url_shortener.py
    - 部署服务：modal deploy 12_url_shortener.py
    """
    print("🔗 短链接生成与追踪服务")
    print("=" * 50)
    
    # 演示创建短链接
    test_urls = [
        {
            "url": "https://example.com/products/summer-sale-2024?utm_source=email&utm_medium=newsletter&utm_campaign=summer",
            "campaign": "summer-sale"
        },
        {
            "url": "https://example.com/blog/how-to-use-modal-for-serverless?ref=twitter",
            "campaign": "social-media"
        },
        {
            "url": "https://example.com/register?promo=SAVE20",
            "custom_code": "save20",
            "campaign": "promo"
        }
    ]
    
    print("\n📝 创建短链接:\n")
    
    created_codes = []
    for test_data in test_urls:
        result = create_short_url.remote(test_data)
        
        if result["status"] == "success":
            print(f"✅ 原始链接: {test_data['url'][:50]}...")
            print(f"   短链接码: {result['short_code']}")
            print(f"   活动标签: {result['campaign']}")
            print()
            created_codes.append(result["short_code"])
    
    # 模拟一些访问
    print("📊 模拟访问统计...\n")
    
    for code in created_codes:
        # 模拟 3 次访问
        for _ in range(3):
            redirect.remote(code=code, referer="https://twitter.com", user_agent="Mozilla/5.0")
    
    # 查看统计
    print("📈 访问统计:\n")
    
    for code in created_codes:
        stats = get_stats.remote(code=code)
        if stats["status"] == "success":
            print(f"短码: {code}")
            print(f"  总点击: {stats['statistics']['total_clicks']}")
            print(f"  活动: {stats['campaign']}")
            print()
    
    print("\n💡 提示:")
    print("1. 部署后会得到 4 个 API 端点")
    print("2. create_short_url: 创建短链接")
    print("3. redirect: 访问短链接（自动重定向）")
    print("4. get_stats: 查看访问统计")
    print("5. 生产环境建议用数据库替代 Dict 存储")

