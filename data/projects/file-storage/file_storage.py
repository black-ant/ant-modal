"""
Modal 文件存储服务
使用 Volume 实现文件上传、下载和管理
"""
import modal
from pathlib import Path

app = modal.App("file-storage")

# 文件存储 Volume
storage_volume = modal.Volume.from_name("file-storage", create_if_missing=True)

image = modal.Image.debian_slim().pip_install("fastapi[all]", "python-multipart")


@app.function(
    image=image,
    volumes={"/storage": storage_volume}
)
@modal.asgi_app()
def file_storage_app():
    """文件存储 API"""
    from fastapi import FastAPI, File, UploadFile, HTTPException
    from fastapi.responses import FileResponse
    import os
    import shutil
    from datetime import datetime
    
    web_app = FastAPI(title="Modal File Storage")
    
    STORAGE_PATH = "/storage"
    
    @web_app.get("/")
    def root():
        return {
            "service": "Modal File Storage",
            "endpoints": {
                "upload": "POST /upload",
                "download": "GET /files/{filename}",
                "list": "GET /files",
                "delete": "DELETE /files/{filename}"
            }
        }
    
    @web_app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        """上传文件"""
        try:
            file_path = os.path.join(STORAGE_PATH, file.filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 提交到 Volume
            storage_volume.commit()
            
            return {
                "filename": file.filename,
                "size": os.path.getsize(file_path),
                "uploaded_at": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @web_app.get("/files")
    def list_files():
        """列出所有文件"""
        files = []
        for filename in os.listdir(STORAGE_PATH):
            file_path = os.path.join(STORAGE_PATH, filename)
            if os.path.isfile(file_path):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    ).isoformat()
                })
        return {"files": files, "count": len(files)}
    
    @web_app.get("/files/{filename}")
    def download_file(filename: str):
        """下载文件"""
        file_path = os.path.join(STORAGE_PATH, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path, filename=filename)
    
    @web_app.delete("/files/{filename}")
    def delete_file(filename: str):
        """删除文件"""
        file_path = os.path.join(STORAGE_PATH, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        os.remove(file_path)
        storage_volume.commit()
        
        return {"message": f"File {filename} deleted"}
    
    return web_app


@app.function(
    image=image,
    volumes={"/storage": storage_volume}
)
def batch_upload(files: list[bytes], filenames: list[str]):
    """批量上传文件"""
    import os
    
    results = []
    for file_data, filename in zip(files, filenames):
        file_path = os.path.join("/storage", filename)
        with open(file_path, "wb") as f:
            f.write(file_data)
        results.append({
            "filename": filename,
            "size": len(file_data)
        })
    
    storage_volume.commit()
    return {"uploaded": len(results), "files": results}
