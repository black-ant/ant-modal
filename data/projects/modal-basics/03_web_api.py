"""
03 - Web API 服务
学习目标：将函数暴露为 HTTP API

这个例子展示：
- 如何创建 Web 端点
- 如何处理 HTTP 请求
- 如何返回 JSON 响应
"""
import modal

app = modal.App("web-api-demo")


@app.function()
@modal.web_endpoint(method="GET")
def hello_api(name: str = "Guest"):
    """
    GET /hello_api?name=YourName
    
    一个简单的 HTTP GET 端点
    """
    return {
        "message": f"Hello, {name}!",
        "status": "success",
        "tip": "这是一个运行在 Modal 云端的 API"
    }


@app.function()
@modal.web_endpoint(method="POST")
def calculate_api(data: dict):
    """
    POST /calculate_api
    Body: {"operation": "add", "a": 10, "b": 20}
    
    一个处理 POST 请求的端点
    """
    operation = data.get("operation", "add")
    a = data.get("a", 0)
    b = data.get("b", 0)
    
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "Error: Division by zero"
    }
    
    result = operations.get(operation, "Unknown operation")
    
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }


@app.local_entrypoint()
def main():
    """
    部署后，你会得到两个 URL：
    - https://your-app--hello-api.modal.run?name=Alice
    - https://your-app--calculate-api.modal.run
    
    使用方法:
    1. modal deploy 03_web_api.py
    2. 访问返回的 URL
    3. 或使用 curl/Postman 测试
    """
    print("🌐 Web API 服务")
    print("=" * 50)
    print("部署命令: modal deploy 03_web_api.py")
    print("\n部署后你会得到两个 API 端点:")
    print("1. GET  /hello_api?name=YourName")
    print("2. POST /calculate_api")
    print("\n💡 提示: 这些 API 会自动扩展，处理任意数量的请求")
