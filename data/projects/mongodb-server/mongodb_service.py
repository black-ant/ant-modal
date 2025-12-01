"""
MongoDB 文档数据库服务
在 Modal 上部署持久化的 MongoDB 数据库

适用场景：
- 灵活的文档存储
- JSON 数据原生支持
- 快速开发和迭代
"""
import modal
import subprocess
import time
import os

app = modal.App("mongodb-server")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .run_commands(
        "apt-get update",
        "apt-get install -y gnupg curl",
        "curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor",
        "echo 'deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main' | tee /etc/apt/sources.list.d/mongodb-org-7.0.list",
        "apt-get update",
        "apt-get install -y mongodb-org",
    )
    .pip_install("pymongo")
)

# MongoDB 数据目录
mongo_volume = modal.Volume.from_name("mongodb-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/data/db": mongo_volume},
    timeout=86400,
    cpu=2,
    memory=4096,
)
def start_mongodb_server():
    """
    启动 MongoDB 服务器
    """
    print("🚀 启动 MongoDB 服务器...")
    
    # 创建数据目录
    os.makedirs("/data/db", exist_ok=True)
    
    # 启动 MongoDB
    process = subprocess.Popen([
        "mongod",
        "--dbpath", "/data/db",
        "--bind_ip_all",
        "--port", "27017"
    ])
    
    time.sleep(5)
    
    print("✓ MongoDB 已启动")
    print("📌 连接信息:")
    print("   URI: mongodb://<Modal Function URL>:27017")
    
    # 保持运行
    while True:
        time.sleep(60)
        mongo_volume.commit()


@app.function(image=image)
def execute_operation(
    database: str,
    collection: str,
    operation: str,
    data: dict = None,
    query: dict = None
) -> dict:
    """
    执行 MongoDB 操作
    
    Args:
        database: 数据库名
        collection: 集合名
        operation: 操作类型 (insert, find, update, delete)
        data: 插入/更新的数据
        query: 查询条件
    """
    from pymongo import MongoClient
    
    client = MongoClient("mongodb://localhost:27017")
    db = client[database]
    coll = db[collection]
    
    if operation == "insert":
        if isinstance(data, list):
            result = coll.insert_many(data)
            return {"inserted_ids": [str(id) for id in result.inserted_ids]}
        else:
            result = coll.insert_one(data)
            return {"inserted_id": str(result.inserted_id)}
    
    elif operation == "find":
        results = list(coll.find(query or {}))
        for r in results:
            r["_id"] = str(r["_id"])
        return {"documents": results}
    
    elif operation == "update":
        result = coll.update_many(query or {}, {"$set": data})
        return {"modified_count": result.modified_count}
    
    elif operation == "delete":
        result = coll.delete_many(query or {})
        return {"deleted_count": result.deleted_count}
    
    else:
        return {"error": f"Unknown operation: {operation}"}


@app.function(image=image)
@modal.web_endpoint(method="POST")
def mongo_api(data: dict):
    """
    MongoDB 操作 API
    
    POST /mongo_api
    {
        "database": "mydb",
        "collection": "users",
        "operation": "find",
        "query": {"age": {"$gt": 18}}
    }
    """
    try:
        result = execute_operation.remote(
            database=data.get("database", "test"),
            collection=data.get("collection", "test"),
            operation=data.get("operation", "find"),
            data=data.get("data"),
            query=data.get("query")
        )
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    print("🍃 MongoDB 服务")
    print("=" * 50)
    print("\n启动服务器:")
    print("  modal run mongodb_service.py::start_mongodb_server")
    print("\n使用 mongo_api 端点执行操作")
    print("\n💡 提示: 数据保存在 mongodb-data Volume 中")

