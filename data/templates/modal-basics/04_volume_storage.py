"""
04 - 持久化存储 (Volume)
学习目标：理解如何在 Modal 中持久化数据

这个例子展示：
- 如何创建和使用 Volume
- 如何在容器间共享数据
- 数据持久化的最佳实践
"""
import modal
from datetime import datetime

app = modal.App("volume-storage-demo")

# 创建一个持久化的 Volume
storage = modal.Volume.from_name("demo-storage", create_if_missing=True)


@app.function(volumes={"/data": storage})
def write_file(filename: str, content: str):
    """
    写入文件到 Volume
    数据会持久化保存
    """
    filepath = f"/data/{filename}"
    
    with open(filepath, "w") as f:
        f.write(content)
        f.write(f"\n\n写入时间: {datetime.now()}")
    
    # 重要：提交更改到 Volume
    storage.commit()
    
    return f"✅ 文件已保存: {filepath}"


@app.function(volumes={"/data": storage})
def read_file(filename: str) -> str:
    """
    从 Volume 读取文件
    """
    filepath = f"/data/{filename}"
    
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"❌ 文件不存在: {filename}"


@app.function(volumes={"/data": storage})
def list_files() -> list:
    """
    列出 Volume 中的所有文件
    """
    import os
    
    if not os.path.exists("/data"):
        return []
    
    files = []
    for filename in os.listdir("/data"):
        filepath = os.path.join("/data", filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            files.append({
                "name": filename,
                "size": size,
                "path": filepath
            })
    
    return files


@app.local_entrypoint()
def main(action: str = "demo"):
    """
    演示 Volume 的使用
    
    使用方法:
    modal run 04_volume_storage.py --action=demo
    modal run 04_volume_storage.py --action=list
    """
    if action == "demo":
        print("📁 Volume 存储演示\n")
        
        # 写入文件
        print("1️⃣ 写入文件...")
        result = write_file.remote("hello.txt", "Hello from Modal Volume!")
        print(f"   {result}\n")
        
        # 读取文件
        print("2️⃣ 读取文件...")
        content = read_file.remote("hello.txt")
        print(f"   内容: {content}\n")
        
        # 列出文件
        print("3️⃣ 列出所有文件...")
        files = list_files.remote()
        for file in files:
            print(f"   - {file['name']} ({file['size']} bytes)")
        
        print("\n💡 提示: 这些文件会永久保存，即使容器重启也不会丢失")
    
    elif action == "list":
        files = list_files.remote()
        print(f"📁 Volume 中有 {len(files)} 个文件:")
        for file in files:
            print(f"  - {file['name']} ({file['size']} bytes)")
