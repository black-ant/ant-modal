"""
MinIO 对象存储服务
部署 S3 兼容的对象存储服务

适用场景：
- 文件/图片/视频存储
- S3 API 兼容
- 大文件上传下载
"""
import modal
import subprocess
import time
import os

app = modal.App("minio-storage")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .run_commands(
        "curl -O https://dl.min.io/server/minio/release/linux-amd64/minio",
        "chmod +x minio",
        "mv minio /usr/local/bin/",
    )
    .pip_install("minio", "boto3")
)

# MinIO 数据目录
minio_volume = modal.Volume.from_name("minio-data", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/data": minio_volume},
    timeout=86400,
    cpu=2,
    memory=4096,
)
def start_minio_server():
    """
    启动 MinIO 服务器
    """
    print("🚀 启动 MinIO 服务器...")
    
    # 设置 MinIO 凭据
    os.environ["MINIO_ROOT_USER"] = "minioadmin"
    os.environ["MINIO_ROOT_PASSWORD"] = "minioadmin123"
    
    # 启动 MinIO
    process = subprocess.Popen([
        "minio", "server", "/data",
        "--address", ":9000",
        "--console-address", ":9001"
    ])
    
    time.sleep(5)
    
    print("✓ MinIO 已启动")
    print("📌 连接信息:")
    print("   API Endpoint: http://<host>:9000")
    print("   Console: http://<host>:9001")
    print("   Access Key: minioadmin")
    print("   Secret Key: minioadmin123")
    
    # 保持运行
    while True:
        time.sleep(60)
        minio_volume.commit()


@app.function(image=image)
def upload_file(bucket: str, object_name: str, data: bytes) -> dict:
    """
    上传文件到 MinIO
    """
    from minio import Minio
    import io
    
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    # 确保 bucket 存在
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    
    # 上传文件
    client.put_object(
        bucket,
        object_name,
        io.BytesIO(data),
        len(data)
    )
    
    return {
        "bucket": bucket,
        "object": object_name,
        "size": len(data)
    }


@app.function(image=image)
def download_file(bucket: str, object_name: str) -> bytes:
    """
    从 MinIO 下载文件
    """
    from minio import Minio
    
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    response = client.get_object(bucket, object_name)
    data = response.read()
    response.close()
    
    return data


@app.function(image=image)
def list_objects(bucket: str, prefix: str = "") -> list:
    """
    列出 bucket 中的对象
    """
    from minio import Minio
    
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    objects = []
    for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
        objects.append({
            "name": obj.object_name,
            "size": obj.size,
            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
        })
    
    return objects


@app.function(image=image)
@modal.web_endpoint(method="POST")
def storage_api(data: dict):
    """
    MinIO 存储 API
    
    POST /storage_api
    {
        "action": "list",  // upload, download, list
        "bucket": "mybucket",
        "object": "path/to/file",
        "data": "base64_encoded_data"  // for upload
    }
    """
    import base64
    
    action = data.get("action", "list")
    bucket = data.get("bucket", "default")
    
    try:
        if action == "list":
            objects = list_objects.remote(bucket, data.get("prefix", ""))
            return {"status": "success", "objects": objects}
        
        elif action == "upload":
            file_data = base64.b64decode(data.get("data", ""))
            result = upload_file.remote(bucket, data["object"], file_data)
            return {"status": "success", "result": result}
        
        elif action == "download":
            file_data = download_file.remote(bucket, data["object"])
            return {
                "status": "success",
                "data": base64.b64encode(file_data).decode()
            }
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    print("📦 MinIO 对象存储服务")
    print("=" * 50)
    print("\n启动服务器:")
    print("  modal run minio_service.py::start_minio_server")
    print("\n使用 storage_api 端点管理文件")
    print("\n💡 S3 兼容，可使用 AWS SDK 连接")

