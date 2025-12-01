"""
RabbitMQ 消息队列服务
部署消息队列，支持异步任务处理

适用场景：
- 异步任务处理
- 服务解耦
- 消息广播
"""
import modal
import subprocess
import time
import os

app = modal.App("rabbitmq-server")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("rabbitmq-server", "erlang")
    .pip_install("pika")
)

# RabbitMQ 数据目录
rabbitmq_volume = modal.Volume.from_name("rabbitmq-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/var/lib/rabbitmq": rabbitmq_volume},
    timeout=86400,
    cpu=2,
    memory=2048,
)
def start_rabbitmq_server():
    """
    启动 RabbitMQ 服务器
    """
    print("🐰 启动 RabbitMQ 服务器...")
    
    # 启动 RabbitMQ
    subprocess.run(["rabbitmq-server", "-detached"], check=True)
    time.sleep(10)
    
    # 启用管理插件
    subprocess.run(["rabbitmq-plugins", "enable", "rabbitmq_management"], check=True)
    
    # 添加用户
    try:
        subprocess.run([
            "rabbitmqctl", "add_user", "modal", "modal123"
        ], check=False)
        subprocess.run([
            "rabbitmqctl", "set_user_tags", "modal", "administrator"
        ], check=False)
        subprocess.run([
            "rabbitmqctl", "set_permissions", "-p", "/", "modal", ".*", ".*", ".*"
        ], check=False)
    except:
        pass
    
    print("✓ RabbitMQ 已启动")
    print("📌 连接信息:")
    print("   AMQP: amqp://modal:modal123@<host>:5672")
    print("   管理界面: http://<host>:15672")
    
    # 保持运行
    while True:
        time.sleep(60)
        rabbitmq_volume.commit()


@app.function(image=image)
def send_message(queue: str, message: str) -> bool:
    """发送消息到队列"""
    import pika
    
    credentials = pika.PlainCredentials("modal", "modal123")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost", 5672, "/", credentials)
    )
    channel = connection.channel()
    
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    
    connection.close()
    return True


@app.function(image=image)
def receive_messages(queue: str, count: int = 10) -> list[str]:
    """从队列接收消息"""
    import pika
    
    credentials = pika.PlainCredentials("modal", "modal123")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost", 5672, "/", credentials)
    )
    channel = connection.channel()
    
    channel.queue_declare(queue=queue, durable=True)
    
    messages = []
    for _ in range(count):
        method, properties, body = channel.basic_get(queue=queue, auto_ack=True)
        if body:
            messages.append(body.decode())
        else:
            break
    
    connection.close()
    return messages


@app.function(image=image)
@modal.web_endpoint(method="POST")
def queue_api(data: dict):
    """
    消息队列 API
    
    POST /queue_api
    {
        "action": "send",  // send, receive
        "queue": "task_queue",
        "message": "Hello"  // for send
    }
    """
    action = data.get("action", "receive")
    queue = data.get("queue", "default")
    
    try:
        if action == "send":
            send_message.remote(queue, data.get("message", ""))
            return {"status": "success", "action": "sent"}
        else:
            messages = receive_messages.remote(queue, data.get("count", 10))
            return {"status": "success", "messages": messages}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    print("🐰 RabbitMQ 消息队列服务")
    print("=" * 50)
    print("\n启动服务器:")
    print("  modal run rabbitmq_service.py::start_rabbitmq_server")
    print("\n发送/接收消息:")
    print("  使用 queue_api 端点")
    print("\n💡 适合异步任务和服务解耦")

