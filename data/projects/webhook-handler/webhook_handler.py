"""
Modal Webhook 处理器
接收和处理来自第三方服务的 Webhook 事件
"""
import modal
from datetime import datetime

app = modal.App("webhook-handler")

image = modal.Image.debian_slim().pip_install("fastapi[all]", "requests")


@app.function(image=image)
@modal.asgi_app()
def webhook_app():
    """Webhook 处理应用"""
    from fastapi import FastAPI, Request, HTTPException
    from typing import Dict, Any
    import json
    
    web_app = FastAPI(title="Modal Webhook Handler")
    
    # 存储最近的事件（实际应用中应使用数据库）
    recent_events = []
    MAX_EVENTS = 100
    
    @web_app.get("/")
    def root():
        return {
            "service": "Webhook Handler",
            "endpoints": {
                "github": "POST /webhooks/github",
                "stripe": "POST /webhooks/stripe",
                "generic": "POST /webhooks/generic",
                "events": "GET /events"
            }
        }
    
    @web_app.post("/webhooks/github")
    async def github_webhook(request: Request):
        """处理 GitHub Webhook"""
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event")
        
        print(f"📦 GitHub Event: {event_type}")
        
        # 根据事件类型处理
        if event_type == "push":
            print(f"  Push to {payload.get('repository', {}).get('name')}")
            print(f"  Commits: {len(payload.get('commits', []))}")
        elif event_type == "pull_request":
            action = payload.get('action')
            pr_number = payload.get('number')
            print(f"  PR #{pr_number} {action}")
        
        # 记录事件
        event = {
            "source": "github",
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": payload
        }
        recent_events.append(event)
        if len(recent_events) > MAX_EVENTS:
            recent_events.pop(0)
        
        return {"status": "received", "event": event_type}
    
    @web_app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        """处理 Stripe Webhook"""
        payload = await request.json()
        event_type = payload.get("type")
        
        print(f"💳 Stripe Event: {event_type}")
        
        # 处理不同的 Stripe 事件
        if event_type == "payment_intent.succeeded":
            amount = payload.get("data", {}).get("object", {}).get("amount")
            print(f"  Payment succeeded: ${amount/100}")
        elif event_type == "customer.subscription.created":
            print(f"  New subscription created")
        
        event = {
            "source": "stripe",
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": payload
        }
        recent_events.append(event)
        if len(recent_events) > MAX_EVENTS:
            recent_events.pop(0)
        
        return {"status": "received", "event": event_type}
    
    @web_app.post("/webhooks/generic")
    async def generic_webhook(request: Request):
        """通用 Webhook 处理器"""
        payload = await request.json()
        
        print(f"🔔 Generic Webhook received")
        print(f"  Payload: {json.dumps(payload, indent=2)}")
        
        event = {
            "source": "generic",
            "type": "webhook",
            "timestamp": datetime.now().isoformat(),
            "data": payload
        }
        recent_events.append(event)
        if len(recent_events) > MAX_EVENTS:
            recent_events.pop(0)
        
        return {"status": "received", "timestamp": event["timestamp"]}
    
    @web_app.get("/events")
    def list_events(limit: int = 10):
        """获取最近的事件"""
        return {
            "events": recent_events[-limit:],
            "total": len(recent_events)
        }
    
    @web_app.get("/events/{source}")
    def list_events_by_source(source: str, limit: int = 10):
        """按来源获取事件"""
        filtered = [e for e in recent_events if e["source"] == source]
        return {
            "events": filtered[-limit:],
            "total": len(filtered)
        }
    
    return web_app


@app.function(image=image)
def process_webhook_async(event_data: Dict[str, Any]):
    """异步处理 Webhook 事件"""
    import time
    
    print(f"⚙️  异步处理事件: {event_data.get('type')}")
    
    # 模拟耗时处理
    time.sleep(2)
    
    print(f"✓ 事件处理完成")
    return {"status": "processed", "event": event_data}
