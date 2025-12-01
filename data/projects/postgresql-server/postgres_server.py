"""
Modal PostgreSQL 数据库服务器
在 Modal 上部署持久化的 PostgreSQL 数据库
"""
import modal

app = modal.App("postgresql-server")

# 持久化 Volume
postgres_volume = modal.Volume.from_name("postgres-data", create_if_missing=True)

# 构建包含 PostgreSQL 的镜像
image = (
    modal.Image.debian_slim()
    .apt_install("postgresql", "postgresql-contrib")
    .pip_install("psycopg2-binary")
)


@app.function(
    image=image,
    volumes={"/var/lib/postgresql/data": postgres_volume},
    timeout=86400,
)
@modal.web_server(5432, startup_timeout=120)
def serve_postgres():
    """启动 PostgreSQL 服务器"""
    import subprocess
    import os
    
    print("🚀 启动 PostgreSQL 服务器...")
    
    # 初始化数据库（如果需要）
    data_dir = "/var/lib/postgresql/data"
    if not os.path.exists(f"{data_dir}/PG_VERSION"):
        print("初始化数据库...")
        subprocess.run([
            "su", "-", "postgres", "-c",
            f"initdb -D {data_dir}"
        ])
    
    # 配置允许远程连接
    with open(f"{data_dir}/postgresql.conf", "a") as f:
        f.write("\nlisten_addresses = '*'\n")
    
    with open(f"{data_dir}/pg_hba.conf", "a") as f:
        f.write("\nhost all all 0.0.0.0/0 md5\n")
    
    # 启动 PostgreSQL
    subprocess.Popen([
        "su", "-", "postgres", "-c",
        f"postgres -D {data_dir}"
    ])
    
    print("✓ PostgreSQL 已启动")


@app.function(image=image)
def create_database(host: str, dbname: str, user: str = "postgres", password: str = ""):
    """创建数据库"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database="postgres"
    )
    conn.autocommit = True
    
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE {dbname}")
    
    conn.close()
    return {"success": True, "database": dbname}


@app.local_entrypoint()
def main():
    print("PostgreSQL 服务器模板")
    print("部署: modal deploy postgres_server.py")
