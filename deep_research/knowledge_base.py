"""
深度研究 Agent 知识库模块
使用向量数据库存储和检索知识
"""

import os
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Union
import numpy as np

# 引入向量数据库和嵌入相关库
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

class KnowledgeBase:
    """知识库，使用向量数据库存储和检索知识"""
    
    def __init__(self, storage_path: str = None, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """初始化知识库
        
        Args:
            storage_path: 知识库存储路径
            embedding_model: 用于文本嵌入的模型名称
        """
        self.storage_path = storage_path or "knowledge_base.json"
        self.entries = {}
        self.vector_store = None
        self.embedding_model_name = embedding_model
        
        # 初始化嵌入模型
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        
        # 加载或创建向量存储
        self._load_or_create_vector_store()
        
        # 加载已有知识库内容
        self._load_entries()
    
    def _load_or_create_vector_store(self):
        """加载或创建向量存储"""
        vector_store_path = os.path.dirname(self.storage_path) + "/vector_store"
        
        try:
            if os.path.exists(vector_store_path):
                print(f"正在加载向量存储: {vector_store_path}")
                self.vector_store = FAISS.load_local(vector_store_path, self.embeddings)
            else:
                print(f"创建新的向量存储")
                # 初始化空的向量存储
                self.vector_store = FAISS.from_documents(
                    [Document(page_content="初始化文档", metadata={"id": "init"})], 
                    self.embeddings
                )
                # 保存向量存储
                os.makedirs(os.path.dirname(vector_store_path), exist_ok=True)
                self.vector_store.save_local(vector_store_path)
        except Exception as e:
            print(f"初始化向量存储时出错: {e}")
            # 创建备用向量存储
            self.vector_store = FAISS.from_documents(
                [Document(page_content="初始化文档", metadata={"id": "init"})], 
                self.embeddings
            )
    
    def _load_entries(self):
        """加载已有知识库内容"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
                print(f"已加载 {len(self.entries)} 条知识库条目")
            except Exception as e:
                print(f"加载知识库时出错: {e}")
                self.entries = {}
        else:
            print("知识库文件不存在，创建新的知识库")
            self.entries = {}
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            self._save_entries()
    
    def _save_entries(self):
        """保存知识库内容到文件"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存知识库时出错: {e}")
    
    def add_entry(self, entry: Dict) -> str:
        """添加条目到知识库
        
        Args:
            entry: 知识库条目
            
        Returns:
            条目ID
        """
        # 为条目生成唯一ID
        entry_id = self._generate_id(entry)
        
        # 保存条目到知识库
        self.entries[entry_id] = entry
        self._save_entries()
        
        # 添加到向量存储
        try:
            text_content = self._extract_text_content(entry)
            document = Document(page_content=text_content, metadata={"id": entry_id, "entry": entry})
            self.vector_store.add_documents([document])
            
            # 保存向量存储
            vector_store_path = os.path.dirname(self.storage_path) + "/vector_store"
            os.makedirs(vector_store_path, exist_ok=True)
            self.vector_store.save_local(vector_store_path)
            
        except Exception as e:
            print(f"添加条目到向量存储时出错: {e}")
        
        return entry_id
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """使用向量搜索查询相关知识
        
        Args:
            query: 搜索查询
            top_k: 返回的最大结果数
            
        Returns:
            搜索结果列表
        """
        if not self.vector_store:
            return []
        
        try:
            # 向量相似度搜索
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # 格式化结果
            formatted_results = []
            for doc, score in results:
                entry_id = doc.metadata.get("id")
                if entry_id and entry_id in self.entries:
                    formatted_results.append({
                        "id": entry_id,
                        "content": self.entries[entry_id],
                        "relevance_score": float(score),
                        "relevance": "high" if float(score) > 0.8 else "medium"
                    })
            
            return formatted_results
        
        except Exception as e:
            print(f"向量搜索时出错: {e}")
            # 回退到关键词搜索
            return self._fallback_keyword_search(query, top_k)
    
    def _fallback_keyword_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """回退到关键词搜索
        
        Args:
            query: 搜索查询
            top_k: 返回的最大结果数
            
        Returns:
            搜索结果列表
        """
        results = []
        query_lower = query.lower()
        
        for entry_id, entry in self.entries.items():
            entry_str = json.dumps(entry, ensure_ascii=False).lower()
            if query_lower in entry_str:
                results.append({
                    "id": entry_id,
                    "content": entry,
                    "relevance": "high" if query_lower in entry_str[:100] else "medium"
                })
        
        # 按相关性排序，返回前top_k个结果
        results.sort(key=lambda x: 0 if x["relevance"] == "high" else 1)
        return results[:top_k]
    
    def _generate_id(self, entry: Dict) -> str:
        """为知识库条目生成唯一ID
        
        Args:
            entry: 知识库条目
            
        Returns:
            唯一ID
        """
        # 使用条目内容的哈希值作为ID
        if isinstance(entry, dict) and "task" in entry:
            # 使用任务内容作为哈希基础
            content = str(entry["task"])
            hash_obj = hashlib.md5(content.encode())
            return hash_obj.hexdigest()[:12]
        else:
            # 生成随机UUID
            return str(uuid.uuid4())[:12]
    
    def _extract_text_content(self, entry: Dict) -> str:
        """从条目中提取文本内容用于向量化
        
        Args:
            entry: 知识库条目
            
        Returns:
            用于向量化的文本内容
        """
        # 尝试提取最有意义的内容
        text_parts = []
        
        if isinstance(entry, dict):
            # 添加任务描述
            if "task" in entry:
                text_parts.append(f"任务: {entry['task']}")
            
            # 添加解决方案
            if "solution" in entry:
                if isinstance(entry["solution"], dict):
                    solution_text = entry["solution"].get("solution", "")
                    text_parts.append(f"解决方案: {solution_text}")
                else:
                    text_parts.append(f"解决方案: {entry['solution']}")
            
            # 添加总结
            if "summary" in entry:
                text_parts.append(f"总结: {entry['summary']}")
                
            # 处理子任务结果
            if "results" in entry and isinstance(entry["results"], dict):
                for task_id, result in entry["results"].items():
                    if isinstance(result, dict) and "solution" in result:
                        text_parts.append(f"子任务 {task_id}: {result['solution']}")
        
        # 如果没有提取到有意义的内容，使用整个条目作为文本
        if not text_parts:
            return json.dumps(entry, ensure_ascii=False)
        
        return "\n".join(text_parts)

    def get_entry(self, entry_id: str) -> Optional[Dict]:
        """获取指定ID的条目
        
        Args:
            entry_id: 条目ID
            
        Returns:
            知识条目，如果不存在则返回None
        """
        return self.entries.get(entry_id)
    
    def get_all_entries(self) -> Dict[str, Dict]:
        """获取所有条目
        
        Returns:
            所有知识条目的字典，键为条目ID
        """
        return self.entries
    
    def clear(self) -> None:
        """清空知识库"""
        self.entries = {}
        
        # 如果设置了存储路径，则保存空知识库到本地
        if self.storage_path:
            self.save_to_disk()
    
    def get_statistics(self) -> Dict:
        """获取知识库统计信息
        
        Returns:
            统计信息，包括条目数量、最新条目时间等
        """
        stats = {
            "total_entries": len(self.entries),
            "latest_timestamp": 0,
            "earliest_timestamp": float('inf') if self.entries else 0,
            "entry_types": {}
        }
        
        for entry_id, entry in self.entries.items():
            # 更新最新/最早时间戳
            timestamp = entry.get("timestamp", 0)
            stats["latest_timestamp"] = max(stats["latest_timestamp"], timestamp)
            if timestamp > 0:
                stats["earliest_timestamp"] = min(stats["earliest_timestamp"], timestamp)
            
            # 统计条目类型
            entry_type = entry.get("task_type", "unknown")
            stats["entry_types"][entry_type] = stats["entry_types"].get(entry_type, 0) + 1
        
        # 如果没有条目，将最早时间戳设为0
        if stats["earliest_timestamp"] == float('inf'):
            stats["earliest_timestamp"] = 0
        
        return stats 