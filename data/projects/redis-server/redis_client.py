"""
Redis 客户端示例
演示如何连接和使用 Modal 上的 Redis 服务
"""
import modal

app = modal.App("redis-client")

# 使用相同的镜像
image = modal.Image.debian_slim().pip_install("redis")


@app.function(image=image)
def redis_operations(redis_url: str):
    """
    执行各种 Redis 操作
    
    Args:
        redis_url: Redis 连接 URL，格式: redis://host:port
    """
    import redis
    
    print(f"连接到 Redis: {redis_url}")
    r = redis.from_url(redis_url, decode_responses=True)
    
    # 1. 字符串操作
    print("\n=== 字符串操作 ===")
    r.set("name", "Modal Redis")
    print(f"GET name: {r.get('name')}")
    
    # 2. 计数器
    print("\n=== 计数器 ===")
    r.incr("visits")
    print(f"访问次数: {r.get('visits')}")
    
    # 3. 列表操作
    print("\n=== 列表操作 ===")
    r.lpush("tasks", "task1", "task2", "task3")
    tasks = r.lrange("tasks", 0, -1)
    print(f"任务列表: {tasks}")
    
    # 4. 哈希操作
    print("\n=== 哈希操作 ===")
    r.hset("user:1", mapping={
        "name": "Alice",
        "age": "30",
        "city": "Beijing"
    })
    user = r.hgetall("user:1")
    print(f"用户信息: {user}")
    
    # 5. 集合操作
    print("\n=== 集合操作 ===")
    r.sadd("tags", "python", "modal", "redis")
    tags = r.smembers("tags")
    print(f"标签集合: {tags}")
    
    # 6. 有序集合
    print("\n=== 有序集合 ===")
    r.zadd("scores", {"Alice": 100, "Bob": 85, "Charlie": 92})
    top_scores = r.zrevrange("scores", 0, 2, withscores=True)
    print(f"排行榜: {top_scores}")
    
    # 7. 过期时间
    print("\n=== 过期时间 ===")
    r.setex("temp_key", 60, "这个键60秒后过期")
    ttl = r.ttl("temp_key")
    print(f"剩余时间: {ttl} 秒")
    
    # 8. 发布/订阅（示例）
    print("\n=== 发布消息 ===")
    r.publish("notifications", "Hello from Modal!")
    
    return {
        "success": True,
        "operations": "completed"
    }


@app.function(image=image)
def redis_cache_example(redis_url: str):
    """
    Redis 缓存示例
    """
    import redis
    import json
    import time
    
    r = redis.from_url(redis_url, decode_responses=True)
    
    def get_user_data(user_id: int):
        """模拟从数据库获取用户数据"""
        cache_key = f"user:{user_id}"
        
        # 尝试从缓存获取
        cached = r.get(cache_key)
        if cached:
            print(f"✓ 从缓存获取用户 {user_id}")
            return json.loads(cached)
        
        # 模拟数据库查询
        print(f"✗ 缓存未命中，查询数据库...")
        time.sleep(0.5)  # 模拟数据库延迟
        
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        }
        
        # 存入缓存，5分钟过期
        r.setex(cache_key, 300, json.dumps(user_data))
        
        return user_data
    
    # 测试缓存
    print("第一次查询（缓存未命中）:")
    user1 = get_user_data(1)
    print(user1)
    
    print("\n第二次查询（从缓存获取）:")
    user2 = get_user_data(1)
    print(user2)
    
    return {"success": True}


@app.function(image=image)
def redis_queue_example(redis_url: str):
    """
    Redis 队列示例
    """
    import redis
    import json
    
    r = redis.from_url(redis_url, decode_responses=True)
    
    # 生产者：添加任务到队列
    print("=== 生产者：添加任务 ===")
    tasks = [
        {"id": 1, "type": "email", "to": "user@example.com"},
        {"id": 2, "type": "sms", "to": "+1234567890"},
        {"id": 3, "type": "push", "to": "device_token"}
    ]
    
    for task in tasks:
        r.lpush("task_queue", json.dumps(task))
        print(f"✓ 添加任务: {task}")
    
    # 消费者：处理队列中的任务
    print("\n=== 消费者：处理任务 ===")
    while True:
        # 阻塞式获取任务（超时1秒）
        result = r.brpop("task_queue", timeout=1)
        if not result:
            print("队列为空")
            break
        
        _, task_json = result
        task = json.loads(task_json)
        print(f"✓ 处理任务: {task}")
    
    return {"success": True}


@app.local_entrypoint()
def main(redis_url: str = "redis://localhost:6379"):
    """
    本地入口
    
    使用方法:
    modal run redis_client.py --redis-url=redis://your-redis-url:6379
    """
    print("Redis 客户端示例")
    print("=" * 50)
    
    # 执行基本操作
    print("\n1. 基本操作:")
    redis_operations.remote(redis_url)
    
    # 缓存示例
    print("\n2. 缓存示例:")
    redis_cache_example.remote(redis_url)
    
    # 队列示例
    print("\n3. 队列示例:")
    redis_queue_example.remote(redis_url)
