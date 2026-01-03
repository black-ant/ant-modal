"""
Modal Redis 服务器
在 Modal 上部署一个持久化的 Redis 服务器
"""
import modal
import subprocess
import time

app = modal.App("redis-server")

# 创建持久化 Volume 用于存储 Redis 数据
redis_volume = modal.Volume.from_name("redis-data", create_if_missing=True)

# 构建包含 Redis 的镜像
image = (
    modal.Image.debian_slim()
    .apt_install("redis-server")
    .pip_install("redis")  # Python Redis 客户端
)


@app.function(
    image=image,
    volumes={"/data": redis_volume},
    timeout=86400,  # 24小时
    allow_concurrent_inputs=100,
)
@modal.web_server(6379, startup_timeout=60)
def serve_redis():
    """
    启动 Redis 服务器
    数据持久化到 /data 目录
    """
    print("🚀 启动 Redis 服务器...")
    
    # Redis 配置
    redis_conf = """
# Redis 配置
bind 0.0.0.0
port 6379
dir /data
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"
"""
    
    # 写入配置文件
    with open("/tmp/redis.conf", "w") as f:
        f.write(redis_conf)
    
    print("✓ Redis 配置已生成")
    print("✓ 数据目录: /data")
    print("✓ 持久化: AOF + RDB")
    
    # 启动 Redis
    cmd = [
        "redis-server",
        "/tmp/redis.conf"
    ]
    
    subprocess.Popen(cmd)
    print("✓ Redis 服务器已启动")


@app.function(image=image)
def test_redis(host: str, port: int = 6379):
    """
    测试 Redis 连接
    
    Args:
        host: Redis 服务器地址
        port: Redis 端口
    """
    import redis
    
    try:
        # 连接 Redis
        r = redis.Redis(host=host, port=port, decode_responses=True)
        
        # 测试 PING
        response = r.ping()
        print(f"✓ PING: {response}")
        
        # 测试 SET/GET
        r.set("test_key", "Hello from Modal!")
        value = r.get("test_key")
        print(f"✓ SET/GET: {value}")
        
        # 测试计数器
        r.incr("counter")
        counter = r.get("counter")
        print(f"✓ Counter: {counter}")
        
        # 获取服务器信息
        info = r.info("server")
        print(f"✓ Redis 版本: {info['redis_version']}")
        
        return {
            "success": True,
            "message": "Redis 连接测试成功",
            "version": info['redis_version']
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.local_entrypoint()
def main():
    """
    本地入口
    
    使用方法:
    modal deploy redis_server.py  # 部署服务
    modal run redis_server.py     # 测试连接
    """
    print("Redis 服务器模板")
    print("=" * 50)
    print("部署: modal deploy redis_server.py")
    print("测试: modal run redis_server.py")
