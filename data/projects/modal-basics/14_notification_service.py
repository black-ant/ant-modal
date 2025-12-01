"""
14 - 多渠道通知服务
业务场景：活动期间需要快速发送大量用户通知

解决的问题：
- 促销活动需要给 10 万用户发送通知，本地发送要几小时
- 不同用户偏好不同渠道（邮件、短信、推送）
- 需要追踪发送状态和失败重试

这个例子展示：
- 并行发送大量通知
- 多渠道路由（邮件/短信/推送）
- 发送状态追踪
- 失败重试机制
"""
import modal
import time
from datetime import datetime
import json
from typing import Literal

app = modal.App("notification-service")

# 存储发送记录
send_records = modal.Dict.from_name("notification-records", create_if_missing=True)


@app.function()
def send_email(recipient: str, subject: str, content: str) -> dict:
    """
    发送邮件通知
    
    实际场景中集成：
    - SendGrid / Mailgun / AWS SES
    - SMTP 服务器
    """
    # 模拟发送延迟
    time.sleep(0.1)
    
    # 模拟 95% 成功率
    import random
    success = random.random() < 0.95
    
    # 实际发送代码示例（使用 SendGrid）：
    # import sendgrid
    # sg = sendgrid.SendGridAPIClient(api_key='YOUR_API_KEY')
    # message = Mail(
    #     from_email='noreply@example.com',
    #     to_emails=recipient,
    #     subject=subject,
    #     html_content=content
    # )
    # response = sg.send(message)
    
    return {
        "channel": "email",
        "recipient": recipient,
        "status": "sent" if success else "failed",
        "timestamp": datetime.now().isoformat(),
        "error": None if success else "SMTP connection timeout"
    }


@app.function()
def send_sms(phone: str, message: str) -> dict:
    """
    发送短信通知
    
    实际场景中集成：
    - Twilio / 阿里云短信 / 腾讯云短信
    """
    # 模拟发送延迟
    time.sleep(0.1)
    
    import random
    success = random.random() < 0.98
    
    # 实际发送代码示例（使用 Twilio）：
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # message = client.messages.create(
    #     body=message,
    #     from_='+1234567890',
    #     to=phone
    # )
    
    return {
        "channel": "sms",
        "recipient": phone,
        "status": "sent" if success else "failed",
        "timestamp": datetime.now().isoformat(),
        "error": None if success else "Invalid phone number"
    }


@app.function()
def send_push(device_token: str, title: str, body: str) -> dict:
    """
    发送 APP 推送通知
    
    实际场景中集成：
    - Firebase Cloud Messaging (FCM)
    - Apple Push Notification Service (APNS)
    - 极光推送 / 个推
    """
    # 模拟发送延迟
    time.sleep(0.05)
    
    import random
    success = random.random() < 0.90
    
    # 实际发送代码示例（使用 FCM）：
    # import firebase_admin
    # from firebase_admin import messaging
    # message = messaging.Message(
    #     notification=messaging.Notification(title=title, body=body),
    #     token=device_token
    # )
    # response = messaging.send(message)
    
    return {
        "channel": "push",
        "recipient": device_token,
        "status": "sent" if success else "failed",
        "timestamp": datetime.now().isoformat(),
        "error": None if success else "Invalid device token"
    }


@app.function()
def send_notification(
    user: dict,
    notification: dict,
    channel: Literal["email", "sms", "push", "auto"] = "auto"
) -> dict:
    """
    发送单个通知
    
    参数：
    - user: 用户信息 {"id": "user123", "email": "...", "phone": "...", "device_token": "...", "preferred_channel": "..."}
    - notification: 通知内容 {"title": "...", "content": "...", "sms_content": "..."}
    - channel: 发送渠道，auto 表示按用户偏好选择
    """
    # 确定发送渠道
    if channel == "auto":
        channel = user.get("preferred_channel", "email")
    
    # 根据渠道发送
    if channel == "email" and user.get("email"):
        result = send_email.remote(
            user["email"],
            notification["title"],
            notification["content"]
        )
    elif channel == "sms" and user.get("phone"):
        result = send_sms.remote(
            user["phone"],
            notification.get("sms_content", notification["title"])
        )
    elif channel == "push" and user.get("device_token"):
        result = send_push.remote(
            user["device_token"],
            notification["title"],
            notification.get("push_body", notification["content"][:100])
        )
    else:
        result = {
            "channel": channel,
            "recipient": user.get("id"),
            "status": "skipped",
            "timestamp": datetime.now().isoformat(),
            "error": f"No valid {channel} contact info"
        }
    
    result["user_id"] = user.get("id")
    return result


@app.function()
def batch_send_notifications(
    users: list[dict],
    notification: dict,
    channel: str = "auto"
) -> dict:
    """
    批量发送通知（并行处理）
    
    返回发送统计
    """
    # 并行发送所有通知
    results = list(send_notification.starmap([
        (user, notification, channel) for user in users
    ]))
    
    # 统计结果
    stats = {
        "total": len(results),
        "sent": sum(1 for r in results if r["status"] == "sent"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "by_channel": {},
        "failed_users": []
    }
    
    for result in results:
        ch = result["channel"]
        if ch not in stats["by_channel"]:
            stats["by_channel"][ch] = {"sent": 0, "failed": 0}
        
        if result["status"] == "sent":
            stats["by_channel"][ch]["sent"] += 1
        elif result["status"] == "failed":
            stats["by_channel"][ch]["failed"] += 1
            stats["failed_users"].append({
                "user_id": result.get("user_id"),
                "channel": ch,
                "error": result.get("error")
            })
    
    return stats


@app.function()
def retry_failed_notifications(failed_users: list[dict], notification: dict) -> dict:
    """
    重试发送失败的通知
    
    尝试使用备用渠道发送
    """
    retry_results = []
    
    for failed in failed_users:
        # 获取用户信息（实际中从数据库查询）
        # 这里简化处理，尝试换一个渠道
        backup_channels = ["email", "sms", "push"]
        original_channel = failed.get("channel")
        
        # 移除失败的渠道，尝试其他渠道
        backup_channels.remove(original_channel) if original_channel in backup_channels else None
        
        for channel in backup_channels:
            # 模拟用户数据
            mock_user = {
                "id": failed["user_id"],
                "email": f"{failed['user_id']}@example.com",
                "phone": "+1234567890",
                "device_token": "device_token_xxx"
            }
            
            result = send_notification.remote(mock_user, notification, channel)
            
            if result["status"] == "sent":
                retry_results.append({
                    "user_id": failed["user_id"],
                    "status": "sent",
                    "retry_channel": channel
                })
                break
        else:
            retry_results.append({
                "user_id": failed["user_id"],
                "status": "failed",
                "message": "All channels failed"
            })
    
    return {
        "total_retried": len(retry_results),
        "success": sum(1 for r in retry_results if r["status"] == "sent"),
        "failed": sum(1 for r in retry_results if r["status"] == "failed"),
        "details": retry_results
    }


@app.function()
@modal.web_endpoint(method="POST")
def send_notification_api(request: dict) -> dict:
    """
    POST /send_notification_api
    
    Web API 端点，接收通知发送请求
    
    请求格式：
    {
        "users": [{"id": "user1", "email": "...", ...}],
        "notification": {"title": "...", "content": "..."},
        "channel": "auto"
    }
    """
    users = request.get("users", [])
    notification = request.get("notification", {})
    channel = request.get("channel", "auto")
    
    if not users or not notification:
        return {"status": "error", "message": "Missing users or notification"}
    
    stats = batch_send_notifications.remote(users, notification, channel)
    
    return {
        "status": "success",
        "stats": stats
    }


@app.local_entrypoint()
def main():
    """
    演示批量通知发送
    
    使用方法：
    - 运行演示：modal run 14_notification_service.py
    - 部署服务：modal deploy 14_notification_service.py
    """
    print("📬 多渠道通知服务")
    print("=" * 50)
    
    # 模拟用户数据
    print("\n👥 准备用户数据...")
    users = []
    channels = ["email", "sms", "push"]
    
    for i in range(100):  # 模拟 100 个用户
        users.append({
            "id": f"user_{i:04d}",
            "email": f"user{i}@example.com",
            "phone": f"+1555{i:07d}",
            "device_token": f"device_token_{i}",
            "preferred_channel": channels[i % 3]
        })
    
    print(f"   已准备 {len(users)} 个用户")
    
    # 创建通知内容
    notification = {
        "title": "🎉 双十一大促开始啦！",
        "content": """
        <h1>年度最大促销活动</h1>
        <p>全场商品低至 5 折，更有满减优惠等你来拿！</p>
        <p>活动时间：11月11日 00:00 - 23:59</p>
        <a href="https://example.com/sale">立即抢购</a>
        """,
        "sms_content": "【XX商城】双十一大促开始！全场5折起，点击 https://example.com/s/1 抢购",
        "push_body": "全场5折起，立即打开APP抢购！"
    }
    
    print(f"\n📝 通知内容: {notification['title']}")
    
    # 批量发送
    print(f"\n🚀 开始批量发送通知...")
    start_time = time.time()
    
    stats = batch_send_notifications.remote(users, notification, "auto")
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 发送统计:")
    print(f"   总数: {stats['total']}")
    print(f"   成功: {stats['sent']} ✅")
    print(f"   失败: {stats['failed']} ❌")
    print(f"   跳过: {stats['skipped']} ⏭️")
    print(f"   耗时: {elapsed:.2f} 秒")
    
    print(f"\n📱 按渠道统计:")
    for channel, channel_stats in stats["by_channel"].items():
        print(f"   {channel}: {channel_stats['sent']} 成功, {channel_stats['failed']} 失败")
    
    # 重试失败的通知
    if stats["failed_users"]:
        print(f"\n🔄 重试失败的 {len(stats['failed_users'])} 个通知...")
        retry_stats = retry_failed_notifications.remote(
            stats["failed_users"][:10],  # 只重试前 10 个演示
            notification
        )
        print(f"   重试成功: {retry_stats['success']}")
        print(f"   仍然失败: {retry_stats['failed']}")
    
    print("\n" + "=" * 50)
    print("💡 提示:")
    print("1. send_email/send_sms/send_push: 替换为实际的发送服务")
    print("2. batch_send_notifications: 并行发送，支持 10 万级用户")
    print("3. retry_failed_notifications: 自动重试失败的通知")
    print("4. 部署 API 后可通过 HTTP 调用发送通知")

