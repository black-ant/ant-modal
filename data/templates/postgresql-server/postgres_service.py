"""
PostgreSQL 数据库服务
在 Modal 上部署持久化的 PostgreSQL 数据库

适用场景：
- 需要关系型数据库
- 复杂查询和事务支持
- 数据持久化存储
"""
import modal
import subprocess
import time
import os

app = modal.App("postgresql-server")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("postgresql", "postgresql-contrib")
    .pip_install("psycopg2-binary")
)

# PostgreSQL 数据目录
pg_volume = modal.Volume.from_name("postgresql-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/var/lib/postgresql/data": pg_volume},
    timeout=86400,  # 24小时
    cpu=2,
    memory=4096,
)
def start_postgres_server():
    """
    启动 PostgreSQL 服务器
    
    数据持久化到 Volume，重启后数据不丢失
    """
    data_dir = "/var/lib/postgresql/data/pgdata"
    
    # 初始化数据库（如果是第一次启动）
    if not os.path.exists(f"{data_dir}/PG_VERSION"):
        print("📦 初始化 PostgreSQL 数据库...")
        os.makedirs(data_dir, exist_ok=True)
        os.chown(data_dir, 999, 999)  # postgres 用户
        
        subprocess.run([
            "sudo", "-u", "postgres",
            "initdb", "-D", data_dir
        ], check=True)
        
        # 配置允许远程连接
        with open(f"{data_dir}/pg_hba.conf", "a") as f:
            f.write("\nhost all all 0.0.0.0/0 md5\n")
        
        with open(f"{data_dir}/postgresql.conf", "a") as f:
            f.write("\nlisten_addresses = '*'\n")
        
        pg_volume.commit()
        print("✓ 数据库初始化完成")
    
    # 启动 PostgreSQL
    print("🚀 启动 PostgreSQL 服务器...")
    subprocess.run([
        "sudo", "-u", "postgres",
        "pg_ctl", "-D", data_dir, "-l", "/tmp/pg.log", "start"
    ], check=True)
    
    # 等待启动
    time.sleep(3)
    
    # 创建默认用户和数据库
    try:
        subprocess.run([
            "sudo", "-u", "postgres", "psql",
            "-c", "CREATE USER modal WITH PASSWORD 'modal123' SUPERUSER;"
        ], check=False)
        subprocess.run([
            "sudo", "-u", "postgres", "psql",
            "-c", "CREATE DATABASE modaldb OWNER modal;"
        ], check=False)
    except:
        pass
    
    print("✓ PostgreSQL 已启动")
    print("📌 连接信息:")
    print("   Host: <Modal Function URL>")
    print("   Port: 5432")
    print("   User: modal")
    print("   Password: modal123")
    print("   Database: modaldb")
    
    # 保持运行
    while True:
        time.sleep(60)
        pg_volume.commit()


@app.function(image=image)
def execute_query(query: str, database: str = "modaldb") -> list:
    """
    执行 SQL 查询
    
    Args:
        query: SQL 查询语句
        database: 数据库名
    
    Returns:
        查询结果列表
    """
    import psycopg2
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="modal",
        password="modal123",
        database=database
    )
    
    cursor = conn.cursor()
    cursor.execute(query)
    
    if cursor.description:
        results = cursor.fetchall()
    else:
        results = []
        conn.commit()
    
    cursor.close()
    conn.close()
    
    return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def query_api(data: dict):
    """
    SQL 查询 API
    
    POST /query_api
    {
        "query": "SELECT * FROM users LIMIT 10",
        "database": "modaldb"
    }
    """
    try:
        results = execute_query.remote(
            query=data.get("query", ""),
            database=data.get("database", "modaldb")
        )
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    print("🐘 PostgreSQL 服务")
    print("=" * 50)
    print("\n启动服务器:")
    print("  modal run postgres_service.py::start_postgres_server")
    print("\n执行查询:")
    print("  使用 query_api 端点发送 SQL")
    print("\n💡 提示: 数据保存在 postgresql-data Volume 中")

