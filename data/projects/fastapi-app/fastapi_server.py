"""
Modal FastAPI Web 应用
快速部署 RESTful API 服务
"""
import modal

app = modal.App("fastapi-app")

image = modal.Image.debian_slim().pip_install(
    "fastapi[all]",
    "uvicorn",
    "pydantic"
)


@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    """FastAPI 应用"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional
    
    web_app = FastAPI(
        title="Modal FastAPI Demo",
        description="在 Modal 上运行的 FastAPI 应用",
        version="1.0.0"
    )
    
    # 数据模型
    class Item(BaseModel):
        id: Optional[int] = None
        name: str
        description: Optional[str] = None
        price: float
        
    # 内存数据库
    items_db = {}
    next_id = 1
    
    @web_app.get("/")
    def read_root():
        return {
            "message": "Welcome to Modal FastAPI!",
            "endpoints": ["/items", "/items/{id}", "/health"]
        }
    
    @web_app.get("/health")
    def health_check():
        return {"status": "healthy"}
    
    @web_app.get("/items", response_model=List[Item])
    def list_items():
        return list(items_db.values())
    
    @web_app.get("/items/{item_id}", response_model=Item)
    def get_item(item_id: int):
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        return items_db[item_id]
    
    @web_app.post("/items", response_model=Item)
    def create_item(item: Item):
        nonlocal next_id
        item.id = next_id
        items_db[next_id] = item
        next_id += 1
        return item
    
    @web_app.put("/items/{item_id}", response_model=Item)
    def update_item(item_id: int, item: Item):
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        item.id = item_id
        items_db[item_id] = item
        return item
    
    @web_app.delete("/items/{item_id}")
    def delete_item(item_id: int):
        if item_id not in items_db:
            raise HTTPException(status_code=404, detail="Item not found")
        del items_db[item_id]
        return {"message": "Item deleted"}
    
    return web_app
