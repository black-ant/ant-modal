"""
相似商品推荐服务
业务场景：电商平台需要根据用户描述推荐相似商品

解决的问题：
- 用户搜索"保暖的冬天穿的外套"，关键词搜索找不到
- 商品太多，用户难以发现符合需求的商品
- 需要提升商品曝光和转化率

这个例子展示：
- 商品描述向量化
- 基于语义的相似商品搜索
- 用户需求匹配推荐
"""
import modal
import json
from datetime import datetime

app = modal.App("embedding-similar-product")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "sentence-transformers",
        "torch==2.1.0",
        "numpy",
        "scikit-learn",
    )
)

model_volume = modal.Volume.from_name("embedding-models", create_if_missing=True)

# 示例商品库
SAMPLE_PRODUCTS = [
    {"id": "P001", "name": "羽绒服男款加厚", "desc": "冬季保暖羽绒服，90%白鹅绒填充，防风防水面料", "price": 599, "category": "男装"},
    {"id": "P002", "name": "棉衣女中长款", "desc": "韩版时尚棉衣，加厚保暖，修身显瘦设计", "price": 399, "category": "女装"},
    {"id": "P003", "name": "运动跑鞋透气款", "desc": "轻便透气运动鞋，减震防滑，适合跑步健身", "price": 299, "category": "运动"},
    {"id": "P004", "name": "保暖内衣套装", "desc": "发热纤维保暖内衣，贴身舒适，冬季必备", "price": 159, "category": "内衣"},
    {"id": "P005", "name": "毛呢大衣女", "desc": "双面羊绒大衣，优雅气质，秋冬百搭款", "price": 899, "category": "女装"},
    {"id": "P006", "name": "冲锋衣户外", "desc": "三合一冲锋衣，防风防雨，适合登山徒步", "price": 459, "category": "户外"},
    {"id": "P007", "name": "休闲运动裤", "desc": "宽松舒适运动裤，弹力面料，居家运动皆可", "price": 129, "category": "运动"},
    {"id": "P008", "name": "雪地靴女", "desc": "加绒保暖雪地靴，防滑底，冬天温暖脚不冷", "price": 259, "category": "女鞋"},
]


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume},
    timeout=600,
)
class ProductRecommender:
    @modal.enter()
    def load_model(self):
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        print("🔤 加载嵌入模型...")
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            cache_folder="/models"
        )
        
        # 预计算商品嵌入
        self.products = SAMPLE_PRODUCTS
        texts = [f"{p['name']} {p['desc']}" for p in self.products]
        self.embeddings = self.model.encode(texts, convert_to_numpy=True)
        
        print(f"✓ 已索引 {len(self.products)} 个商品")
    
    @modal.method()
    def search_by_description(
        self,
        query: str,
        top_k: int = 5,
        category: str = None,
        max_price: float = None
    ) -> list[dict]:
        """
        根据用户描述搜索商品
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_embedding = self.model.encode([query])[0]
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            self.embeddings
        )[0]
        
        results = []
        for i, score in enumerate(similarities):
            p = self.products[i]
            
            if category and p["category"] != category:
                continue
            if max_price and p["price"] > max_price:
                continue
            
            results.append({
                "id": p["id"],
                "name": p["name"],
                "description": p["desc"],
                "price": p["price"],
                "category": p["category"],
                "score": float(score)
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    @modal.method()
    def find_similar(self, product_id: str, top_k: int = 3) -> list[dict]:
        """
        找到相似商品
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        idx = None
        for i, p in enumerate(self.products):
            if p["id"] == product_id:
                idx = i
                break
        
        if idx is None:
            return []
        
        similarities = cosine_similarity(
            self.embeddings[idx].reshape(1, -1),
            self.embeddings
        )[0]
        
        results = []
        for i, score in enumerate(similarities):
            if i == idx:
                continue
            p = self.products[i]
            results.append({
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "score": float(score)
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


@app.function(image=image)
@modal.web_endpoint(method="POST")
def recommend_api(data: dict):
    """
    商品推荐 API
    
    POST /recommend_api
    {
        "query": "冬天保暖的外套",
        "top_k": 5,
        "max_price": 500
    }
    """
    recommender = ProductRecommender()
    results = recommender.search_by_description.remote(
        query=data.get("query", ""),
        top_k=data.get("top_k", 5),
        category=data.get("category"),
        max_price=data.get("max_price")
    )
    return {"status": "success", "results": results}


@app.local_entrypoint()
def main():
    """演示商品推荐"""
    print("🛒 相似商品推荐服务")
    print("=" * 50)
    
    recommender = ProductRecommender()
    
    queries = [
        "冬天保暖的衣服",
        "跑步穿的鞋子",
        "户外爬山穿的",
    ]
    
    for query in queries:
        print(f"\n🔍 搜索: {query}")
        results = recommender.search_by_description.remote(query, top_k=3)
        for r in results:
            print(f"   [{r['score']:.3f}] {r['name']} ¥{r['price']}")
    
    print("\n💡 提示: 接入真实商品库后即可上线使用")

