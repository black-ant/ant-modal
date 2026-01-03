"""
企业知识库智能检索
业务场景：企业积累了大量文档，但员工难以快速找到需要的信息

解决的问题：
- 传统关键词搜索找不到语义相关的内容
- 员工花大量时间翻找文档，效率低下
- 新人 onboarding 需要频繁问同事基础问题

这个例子展示：
- 文档向量化存储
- 语义搜索（理解问题含义）
- 相关文档推荐
- 支持增量更新文档库
"""
import modal
import json
from datetime import datetime

app = modal.App("embedding-knowledge-base")

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
kb_volume = modal.Volume.from_name("knowledge-base", create_if_missing=True)


# 示例知识库文档（实际场景从数据库/文件系统加载）
SAMPLE_DOCUMENTS = [
    {
        "id": "doc_001",
        "title": "员工请假流程",
        "content": "员工请假需要提前在 OA 系统提交申请，1-3天由直属领导审批，3天以上需要部门总监审批。病假需要提供医院证明。",
        "category": "人事制度"
    },
    {
        "id": "doc_002",
        "title": "报销制度说明",
        "content": "差旅报销需要在出差结束后7天内提交，需要提供发票、行程单等凭证。住宿标准：一线城市500元/晚，其他城市300元/晚。",
        "category": "财务制度"
    },
    {
        "id": "doc_003",
        "title": "代码审查规范",
        "content": "所有代码提交前必须经过 Code Review。PR 需要至少一位同事审批。审查重点包括：代码风格、逻辑正确性、性能影响、安全隐患。",
        "category": "研发规范"
    },
    {
        "id": "doc_004",
        "title": "会议室预约指南",
        "content": "会议室通过企业微信日历预约。大会议室（10人以上）需要提前1天预约。预约后未使用会被记录，影响后续预约权限。",
        "category": "行政管理"
    },
    {
        "id": "doc_005",
        "title": "新人入职指南",
        "content": "入职第一天需要到 HR 处领取工卡、电脑等办公用品。第一周需要完成：企业文化培训、部门介绍、导师 1v1、系统权限开通。",
        "category": "人事制度"
    },
    {
        "id": "doc_006",
        "title": "VPN 使用说明",
        "content": "远程办公需要使用 VPN 连接公司网络。下载地址：内网 IT 服务页面。首次使用需要申请 VPN 账号，审批后 IT 会发送配置信息。",
        "category": "IT支持"
    },
    {
        "id": "doc_007",
        "title": "年假政策",
        "content": "员工入职满一年后享有5天带薪年假。工龄每增加一年增加1天，上限15天。年假可以累积到次年3月底，过期作废。",
        "category": "人事制度"
    },
    {
        "id": "doc_008",
        "title": "项目立项流程",
        "content": "新项目需要填写立项申请书，包括项目背景、目标、资源需求、时间计划。经技术评审会和业务评审会通过后正式立项。",
        "category": "项目管理"
    },
]


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume, "/kb": kb_volume},
    timeout=600,
)
class KnowledgeBase:
    @modal.enter()
    def load_model(self):
        from sentence_transformers import SentenceTransformer
        import numpy as np
        import os
        
        print("🔤 加载嵌入模型...")
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            cache_folder="/models"
        )
        
        # 尝试加载已有的文档索引
        self.documents = []
        self.embeddings = None
        
        index_path = "/kb/index.json"
        embeddings_path = "/kb/embeddings.npy"
        
        if os.path.exists(index_path) and os.path.exists(embeddings_path):
            print("📚 加载已有知识库索引...")
            with open(index_path, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
            self.embeddings = np.load(embeddings_path)
            print(f"✓ 已加载 {len(self.documents)} 个文档")
        else:
            print("📝 知识库为空，需要先导入文档")
        
        print("✓ 初始化完成")
    
    @modal.method()
    def index_documents(self, documents: list[dict]) -> dict:
        """
        索引文档到知识库
        
        Args:
            documents: 文档列表 [{"id": "...", "title": "...", "content": "...", "category": "..."}]
        """
        import numpy as np
        
        print(f"📚 索引 {len(documents)} 个文档...")
        
        # 合并现有文档
        existing_ids = {doc["id"] for doc in self.documents}
        new_docs = [d for d in documents if d["id"] not in existing_ids]
        
        if not new_docs:
            return {"status": "no_new_documents", "total": len(self.documents)}
        
        # 生成新文档的嵌入
        texts = [f"{d['title']}. {d['content']}" for d in new_docs]
        new_embeddings = self.model.encode(texts, convert_to_numpy=True)
        
        # 合并
        self.documents.extend(new_docs)
        
        if self.embeddings is not None:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        else:
            self.embeddings = new_embeddings
        
        # 保存到 Volume
        with open("/kb/index.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        np.save("/kb/embeddings.npy", self.embeddings)
        
        kb_volume.commit()
        
        print(f"✓ 新增 {len(new_docs)} 个文档，总计 {len(self.documents)} 个")
        
        return {
            "status": "success",
            "new_documents": len(new_docs),
            "total_documents": len(self.documents)
        }
    
    @modal.method()
    def search(
        self,
        query: str,
        top_k: int = 5,
        category: str = None,
        min_score: float = 0.3
    ) -> list[dict]:
        """
        语义搜索知识库
        
        Args:
            query: 搜索问题
            top_k: 返回前 k 个结果
            category: 限定分类（可选）
            min_score: 最小相似度阈值
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        if not self.documents or self.embeddings is None:
            return []
        
        print(f"🔍 搜索: {query}")
        
        # 生成查询嵌入
        query_embedding = self.model.encode([query])[0]
        
        # 计算相似度
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            self.embeddings
        )[0]
        
        # 筛选和排序
        results = []
        for i, score in enumerate(similarities):
            doc = self.documents[i]
            
            # 分类过滤
            if category and doc.get("category") != category:
                continue
            
            # 分数过滤
            if score < min_score:
                continue
            
            results.append({
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "category": doc.get("category", ""),
                "score": float(score)
            })
        
        # 排序并返回 top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    @modal.method()
    def get_related_documents(self, doc_id: str, top_k: int = 3) -> list[dict]:
        """
        获取相关文档推荐
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        # 找到目标文档
        target_idx = None
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                target_idx = i
                break
        
        if target_idx is None:
            return []
        
        # 计算与其他文档的相似度
        similarities = cosine_similarity(
            self.embeddings[target_idx].reshape(1, -1),
            self.embeddings
        )[0]
        
        # 排序（排除自身）
        results = []
        for i, score in enumerate(similarities):
            if i == target_idx:
                continue
            results.append({
                "id": self.documents[i]["id"],
                "title": self.documents[i]["title"],
                "category": self.documents[i].get("category", ""),
                "score": float(score)
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


@app.function(image=image)
@modal.web_endpoint(method="POST")
def kb_search_api(data: dict):
    """
    知识库搜索 API
    
    POST /kb_search_api
    {
        "query": "如何申请年假？",
        "top_k": 5,
        "category": "人事制度"  // 可选
    }
    """
    kb = KnowledgeBase()
    
    results = kb.search.remote(
        query=data.get("query", ""),
        top_k=data.get("top_k", 5),
        category=data.get("category")
    )
    
    return {
        "status": "success",
        "query": data.get("query"),
        "results": results
    }


@app.function(image=image)
@modal.web_endpoint(method="POST")
def kb_index_api(data: dict):
    """
    索引文档 API
    
    POST /kb_index_api
    {
        "documents": [
            {"id": "doc_new", "title": "...", "content": "...", "category": "..."}
        ]
    }
    """
    kb = KnowledgeBase()
    result = kb.index_documents.remote(data.get("documents", []))
    return result


@app.local_entrypoint()
def main():
    """演示知识库检索"""
    print("📚 企业知识库智能检索")
    print("=" * 50)
    
    kb = KnowledgeBase()
    
    # 1. 索引示例文档
    print("\n1️⃣ 索引示例文档...")
    result = kb.index_documents.remote(SAMPLE_DOCUMENTS)
    print(f"   结果: {result}")
    
    # 2. 测试语义搜索
    test_queries = [
        "我想请几天假，需要走什么流程？",
        "出差住酒店有什么标准？",
        "新同事刚来公司要做什么？",
        "怎么在家远程办公？",
    ]
    
    print("\n2️⃣ 测试语义搜索:")
    
    for query in test_queries:
        print(f"\n❓ 问题: {query}")
        results = kb.search.remote(query, top_k=2)
        
        for i, r in enumerate(results, 1):
            print(f"   {i}. [{r['score']:.3f}] {r['title']}")
            print(f"      {r['content'][:60]}...")
    
    # 3. 测试相关文档推荐
    print("\n3️⃣ 相关文档推荐:")
    related = kb.get_related_documents.remote("doc_001", top_k=3)
    print("   与「员工请假流程」相关的文档:")
    for r in related:
        print(f"   - [{r['score']:.3f}] {r['title']}")
    
    print("\n💡 提示:")
    print("1. 实际使用时从数据库/文件系统加载文档")
    print("2. 支持增量更新，无需全量重建索引")
    print("3. 可配合 LLM 实现问答式知识库")

