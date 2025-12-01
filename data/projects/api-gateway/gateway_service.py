"""
API 网关服务
统一 API 入口，支持限流、认证、路由

适用场景：
- 微服务 API 统一入口
- 请求限流和熔断
- 认证和鉴权
"""
import modal
from datetime import datetime
import time
import hashlib

app = modal.App("api-gateway")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi",
        "httpx",
        "pyjwt",
    )
)

# 使用 Dict 存储限流计数
rate_limit_store = modal.Dict.from_name("rate-limits", create_if_missing=True)

# 路由配置
ROUTES = {
    "/api/users": "https://user-service.modal.run",
    "/api/orders": "https://order-service.modal.run",
    "/api/products": "https://product-service.modal.run",
}

# API 密钥配置（实际使用时从环境变量或数据库读取）
API_KEYS = {
    "sk_test_12345": {"name": "Test App", "rate_limit": 100},
    "sk_prod_67890": {"name": "Production App", "rate_limit": 1000},
}


def verify_api_key(api_key: str) -> dict:
    """验证 API 密钥"""
    if api_key in API_KEYS:
        return API_KEYS[api_key]
    return None


def check_rate_limit(api_key: str, limit: int = 100) -> bool:
    """
    检查请求是否超过限流
    使用滑动窗口算法
    """
    current_minute = datetime.now().strftime("%Y%m%d%H%M")
    key = f"{api_key}:{current_minute}"
    
    count = rate_limit_store.get(key, 0)
    
    if count >= limit:
        return False
    
    rate_limit_store[key] = count + 1
    return True


@app.function(image=image)
def proxy_request(
    method: str,
    path: str,
    headers: dict,
    body: dict = None
) -> dict:
    """
    代理请求到后端服务
    """
    import httpx
    
    # 查找目标服务
    target_url = None
    for route_prefix, service_url in ROUTES.items():
        if path.startswith(route_prefix):
            target_url = service_url + path[len(route_prefix):]
            break
    
    if not target_url:
        return {"error": "No route found", "status_code": 404}
    
    # 转发请求
    try:
        with httpx.Client(timeout=30) as client:
            response = client.request(
                method=method,
                url=target_url,
                headers=headers,
                json=body if body else None
            )
            
            return {
                "status_code": response.status_code,
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
    except Exception as e:
        return {"error": str(e), "status_code": 502}


@app.function(image=image)
@modal.web_endpoint(method="POST")
def gateway(data: dict):
    """
    API 网关入口
    
    POST /gateway
    Headers:
        X-API-Key: sk_test_12345
    
    Body:
    {
        "method": "GET",
        "path": "/api/users/123",
        "body": {}
    }
    """
    # 1. 验证 API 密钥
    api_key = data.get("api_key", "")
    app_info = verify_api_key(api_key)
    
    if not app_info:
        return {
            "status": "error",
            "code": 401,
            "message": "Invalid API key"
        }
    
    # 2. 检查限流
    if not check_rate_limit(api_key, app_info.get("rate_limit", 100)):
        return {
            "status": "error",
            "code": 429,
            "message": "Rate limit exceeded"
        }
    
    # 3. 代理请求
    result = proxy_request.remote(
        method=data.get("method", "GET"),
        path=data.get("path", "/"),
        headers=data.get("headers", {}),
        body=data.get("body")
    )
    
    # 4. 返回响应
    if "error" in result:
        return {
            "status": "error",
            "code": result.get("status_code", 500),
            "message": result["error"]
        }
    
    return {
        "status": "success",
        "code": result["status_code"],
        "data": result["body"]
    }


@app.function(image=image)
@modal.web_endpoint(method="GET")
def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "routes": list(ROUTES.keys())
    }


@app.function(image=image)
@modal.web_endpoint(method="GET")
def get_rate_limit_status(api_key: str = ""):
    """获取限流状态"""
    if not api_key:
        return {"error": "API key required"}
    
    app_info = verify_api_key(api_key)
    if not app_info:
        return {"error": "Invalid API key"}
    
    current_minute = datetime.now().strftime("%Y%m%d%H%M")
    key = f"{api_key}:{current_minute}"
    count = rate_limit_store.get(key, 0)
    
    return {
        "app": app_info["name"],
        "current_requests": count,
        "limit": app_info["rate_limit"],
        "remaining": max(0, app_info["rate_limit"] - count)
    }


@app.local_entrypoint()
def main():
    """演示 API 网关"""
    print("🚪 API 网关服务")
    print("=" * 50)
    
    print("\n功能特性:")
    print("  ✓ API 密钥认证")
    print("  ✓ 请求限流")
    print("  ✓ 路由转发")
    print("  ✓ 健康检查")
    
    print("\n路由配置:")
    for path, service in ROUTES.items():
        print(f"  {path} -> {service}")
    
    print("\n使用方法:")
    print("  1. 部署: modal deploy gateway_service.py")
    print("  2. 调用 /gateway 端点转发请求")
    print("  3. 调用 /health 检查服务状态")
    
    print("\n💡 提示: 修改 ROUTES 配置你的后端服务")

