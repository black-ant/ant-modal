# Modal Redis 服务器

在 Modal 上部署持久化的 Redis 服务器。

## 功能特点

✅ **持久化存储** - 使用 Modal Volume 保存数据  
✅ **AOF + RDB** - 双重持久化保证数据安全  
✅ **长期运行** - 24小时超时，适合生产环境  
✅ **完整示例** - 包含客户端使用示例  

## 脚本说明

### 1. redis_server.py - Redis 服务器
部署 Redis 服务器，数据持久化到 Volume。

**配置：**
- 端口: 6379
- 数据目录: /data
- 持久化: AOF + RDB
- 绑定: 0.0.0.0（允许外部访问）

### 2. redis_client.py - Redis 客户端
演示如何连接和使用 Redis 的各种功能。

**示例：**
- 字符串操作
- 列表、哈希、集合
- 缓存示例
- 队列示例

## 使用方法

### 部署 Redis 服务器

```bash
modal deploy redis_server.py
```

部署后会得到一个 URL，例如：
```
https://your-app--redis-server-serve-redis.modal.run
```

### 连接 Redis

使用 Redis 客户端连接：

```python
import redis

r = redis.Redis(
    host='your-app--redis-server-serve-redis.modal.run',
    port=6379,
    decode_responses=True
)

# 测试连接
r.ping()  # 返回 True

# 基本操作
r.set('key', 'value')
r.get('key')  # 返回 'value'
```

### 运行客户端示例

```bash
modal run redis_client.py --redis-url=redis://your-redis-url:6379
```

## Redis 操作示例

### 字符串操作
```python
r.set('name', 'Modal')
r.get('name')  # 'Modal'
r.incr('counter')  # 计数器
```

### 列表操作
```python
r.lpush('tasks', 'task1', 'task2')
r.lrange('tasks', 0, -1)  # ['task2', 'task1']
```

### 哈希操作
```python
r.hset('user:1', mapping={'name': 'Alice', 'age': '30'})
r.hgetall('user:1')  # {'name': 'Alice', 'age': '30'}
```

### 集合操作
```python
r.sadd('tags', 'python', 'redis')
r.smembers('tags')  # {'python', 'redis'}
```

### 有序集合
```python
r.zadd('scores', {'Alice': 100, 'Bob': 85})
r.zrevrange('scores', 0, -1, withscores=True)
```

### 缓存示例
```python
# 设置过期时间
r.setex('temp', 60, 'expires in 60 seconds')
r.ttl('temp')  # 返回剩余秒数
```

### 队列示例
```python
# 生产者
r.lpush('queue', 'task1')

# 消费者
task = r.brpop('queue', timeout=1)
```

## 持久化说明

Redis 使用两种持久化方式：

1. **RDB (快照)**
   - 每 900 秒至少 1 次修改
   - 每 300 秒至少 10 次修改
   - 每 60 秒至少 10000 次修改

2. **AOF (追加文件)**
   - 记录每个写操作
   - 重启时重放命令恢复数据

数据保存在 Modal Volume `redis-data` 中，重启后自动恢复。

## 注意事项

⚠️ **安全提示：**
- 生产环境建议配置密码认证
- 考虑使用 SSL/TLS 加密连接
- 限制访问 IP 范围

⚠️ **性能提示：**
- Modal 的网络延迟可能比本地 Redis 高
- 适合中小规模应用
- 大规模应用建议使用专业 Redis 服务

## 高级配置

如需自定义配置，修改 `redis_server.py` 中的 `redis_conf` 变量：

```python
redis_conf = """
# 添加密码
requirepass your_password

# 最大内存限制
maxmemory 256mb
maxmemory-policy allkeys-lru

# 其他配置...
"""
```

## 监控和管理

查看 Redis 信息：
```python
r.info()  # 服务器信息
r.dbsize()  # 键数量
r.keys('*')  # 所有键（生产环境慎用）
```

## 故障排查

1. **连接失败**
   - 检查 URL 是否正确
   - 确认服务已部署
   - 检查网络连接

2. **数据丢失**
   - 检查 Volume 是否正确挂载
   - 查看持久化配置
   - 检查日志输出

3. **性能问题**
   - 使用 `r.slowlog_get()` 查看慢查询
   - 检查键的数量和大小
   - 考虑使用连接池
