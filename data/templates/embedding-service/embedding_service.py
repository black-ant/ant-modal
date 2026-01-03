"""
文本嵌入服务
使用 Sentence Transformers 生成文本向量
用于语义搜索、相似度计算等
"""
import modal

app = modal.App("embedding-service")

# 构建镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "sentence-transformers",
        "torch==2.1.0",
    )
)

# 模型缓存
model_volume = modal.Volume.from_name("embedding-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume},
    timeout=600,
)
class EmbeddingService:
    @modal.enter()
    def load_model(self):
        """加载嵌入模型"""
        from sentence_transformers import SentenceTransformer
        
        print("🔤 加载嵌入模型...")
        
        # 使用多语言模型
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            cache_folder="/models"
        )
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        生成文本嵌入向量
        
        Args:
            texts: 文本列表
        
        Returns:
            嵌入向量列表
        """
        print(f"🔤 生成 {len(texts)} 个文本的嵌入向量...")
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        print("✓ 嵌入向量生成完成")
        return embeddings.tolist()
    
    @modal.method()
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
        
        Returns:
            相似度分数 (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        embeddings = self.model.encode([text1, text2])
        similarity = cosine_similarity(
            embeddings[0].reshape(1, -1),
            embeddings[1].reshape(1, -1)
        )[0][0]
        
        return float(similarity)
    
    @modal.method()
    def search(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5
    ) -> list[dict]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前 k 个结果
        
        Returns:
            相似文档列表
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        print(f"🔍 在 {len(documents)} 个文档中搜索...")
        
        # 生成嵌入
        query_embedding = self.model.encode([query])[0]
        doc_embeddings = self.model.encode(documents)
        
        # 计算相似度
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            doc_embeddings
        )[0]
        
        # 排序并返回 top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = [
            {
                "index": int(idx),
                "text": documents[idx],
                "score": float(similarities[idx])
            }
            for idx in top_indices
        ]
        
        print(f"✓ 找到 {len(results)} 个相关文档")
        return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def embed_texts(data: dict):
    """
    Web API: 生成嵌入向量
    
    POST /embed_texts
    {
        "texts": ["text1", "text2", ...]
    }
    """
    service = EmbeddingService()
    embeddings = service.encode.remote(data["texts"])
    return {"embeddings": embeddings}


@app.function(image=image)
@modal.web_endpoint(method="POST")
def semantic_search(data: dict):
    """
    Web API: 语义搜索
    
    POST /semantic_search
    {
        "query": "search query",
        "documents": ["doc1", "doc2", ...],
        "top_k": 5
    }
    """
    service = EmbeddingService()
    results = service.search.remote(
        query=data["query"],
        documents=data["documents"],
        top_k=data.get("top_k", 5)
    )
    return {"results": results}


@app.local_entrypoint()
def main():
    """本地测试"""
    service = EmbeddingService()
    
    # 测试文档
    documents = [
        "人工智能正在改变世界",
        "机器学习是AI的一个分支",
        "今天天气很好",
        "深度学习使用神经网络",
        "我喜欢吃披萨"
    ]
    
    query = "AI技术的发展"
    
    print(f"查询: {query}\n")
    results = service.search.remote(query, documents, top_k=3)
    
    print("搜索结果:")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['score']:.3f}] {result['text']}")
