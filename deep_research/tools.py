"""
深度研究 Agent 工具模块
包含网络搜索、知识库搜索等工具
"""

import os
import json
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Union
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_core.tools import BaseTool
from langchain.tools import Tool
from LLMapi_service.gptservice import GPT, is_deepseek_model

class WebSearchTool(BaseTool):
    """网络搜索工具，使用gpt-4o-mini-search-preview模型进行实际网络搜索"""
    
    name: str = "web_search"
    description: str = "执行网络搜索以找到有关特定查询的信息。使用GPT-4o mini搜索模型获取实时网络数据。"
    model: str = "gpt-4o-mini-search-preview"  # 使用带有网络搜索能力的模型
    
    async def _arun(self, query: str) -> str:
        """异步执行搜索"""
        results = await self.perform_search(query)
        return json.dumps(results, ensure_ascii=False)
    
    def _run(self, query: str) -> str:
        """执行搜索"""
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self.perform_search(query))
        return json.dumps(results, ensure_ascii=False)
    
    async def perform_search(self, query: str) -> List[Dict]:
        """使用gpt-4o-mini-search-preview模型执行实际网络搜索
        
        参数:
            query: 搜索查询
            
        返回:
            搜索结果列表
        """
        try:
            print(f"正在搜索: {query}")
            
            # 构建搜索指令和消息
            messages = [
                {"role": "system", "content": "你是一个专业的网络搜索助手。请使用你的搜索能力查找以下问题的相关信息，并返回结果。结果必须包含标题、URL和内容摘要，格式为JSON数组。"},
                {"role": "user", "content": f"请搜索以下内容并返回至少5个相关结果: {query}\n\n请确保返回JSON格式的结果，格式示例:\n[{{'title': '结果标题', 'url': 'https://example.com', 'snippet': '内容摘要...'}}]"}
            ]
            
            # 调用GPT-4o mini搜索模型
            response = await GPT(messages, selected_model=self.model)
            
            if not response or not isinstance(response, dict) or "content" not in response:
                return [{"error": "搜索响应无效", "query": query}]
            
            content = response["content"]
            
            # 提取JSON部分 - 可能在内容中的```json ```包裹的代码块中
            json_content = content
            if "```json" in content:
                # 提取JSON部分
                start_idx = content.find("```json") + 7
                end_idx = content.find("```", start_idx)
                if end_idx > start_idx:
                    json_content = content[start_idx:end_idx].strip()
            elif "```" in content:
                # 尝试从任何代码块中提取
                start_idx = content.find("```") + 3
                # 可能还有语言标识符
                if content[start_idx:].startswith("json"):
                    start_idx += 4
                end_idx = content.find("```", start_idx)
                if end_idx > start_idx:
                    json_content = content[start_idx:end_idx].strip()
            
            # 解析JSON结果
            try:
                results = json.loads(json_content)
                if not isinstance(results, list):
                    if isinstance(results, dict):
                        # 处理单个结果
                        results = [results]
                    else:
                        # 解析失败，返回原始内容
                        return [{"title": "搜索结果", "url": "", "snippet": content}]
                
                # 标准化结果格式
                standardized_results = []
                for item in results:
                    if isinstance(item, dict):
                        result = {
                            "title": item.get("title", "未知标题"),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", item.get("content", ""))
                        }
                        standardized_results.append(result)
                
                return standardized_results
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回原始内容
                print(f"JSON解析失败，原始内容: {content}")
                return [{"title": "搜索结果", "url": "", "snippet": content}]
            
        except Exception as e:
            print(f"搜索时出错: {str(e)}")
            return [{"error": str(e), "query": query}]

class KnowledgeBaseSearchTool(BaseTool):
    """知识库搜索工具"""
    
    name: str = "knowledge_base_search"
    description: str = "在本地知识库中搜索相关信息。使用向量数据库进行语义搜索。"
    
    def __init__(self, knowledge_base: Dict = None):
        """初始化知识库搜索工具
        
        Args:
            knowledge_base: 知识库对象
        """
        super().__init__()
        self.knowledge_base = knowledge_base or {}
    
    async def _arun(self, query: str) -> str:
        """异步执行知识库搜索"""
        results = await self.search_knowledge_base(query)
        return json.dumps(results, ensure_ascii=False)
    
    def _run(self, query: str) -> str:
        """执行知识库搜索"""
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self.search_knowledge_base(query))
        return json.dumps(results, ensure_ascii=False)
    
    async def search_knowledge_base(self, query: str, top_k: int = 5) -> List[Dict]:
        """在知识库中执行向量搜索
        
        Args:
            query: 搜索查询
            top_k: 返回结果的最大数量
            
        Returns:
            搜索结果列表
        """
        # 如果知识库为空，返回空结果
        if not hasattr(self.knowledge_base, 'search'):
            print("警告: 知识库对象没有search方法，使用传统的字典搜索")
            return self._fallback_search(query, top_k)
        
        try:
            # 调用知识库的向量搜索方法
            results = self.knowledge_base.search(query, top_k=top_k)
            
            if not results and hasattr(self.knowledge_base, '_fallback_keyword_search'):
                # 如果向量搜索没有结果，尝试关键词搜索
                results = self.knowledge_base._fallback_keyword_search(query, top_k)
                
            return results
            
        except Exception as e:
            print(f"知识库搜索时出错: {e}")
            return self._fallback_search(query, top_k)
    
    def _fallback_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """回退到传统的字典搜索方法
        
        Args:
            query: 搜索查询
            top_k: 返回结果的最大数量
            
        Returns:
            搜索结果列表
        """
        results = []
        query_lower = query.lower()
        
        # 如果知识库是字典类型
        if isinstance(self.knowledge_base, dict):
            kb_entries = self.knowledge_base
        # 如果知识库是对象且有entries属性
        elif hasattr(self.knowledge_base, 'entries'):
            kb_entries = self.knowledge_base.entries
        else:
            return []
            
        for entry_id, entry in kb_entries.items():
            entry_str = json.dumps(entry, ensure_ascii=False).lower()
            if query_lower in entry_str:
                results.append({
                    "id": entry_id,
                    "content": entry,
                    "relevance": "high" if query_lower in entry_str[:100] else "medium"
                })
                
        # 按相关性排序
        results.sort(key=lambda x: 0 if x["relevance"] == "high" else 1)
        
        return results[:top_k]

class KnowledgeBaseStorageTool(BaseTool):
    """知识库存储工具"""
    
    name: str = "knowledge_base_storage"
    description: str = "将信息存储到知识库中。"
    
    def __init__(self, knowledge_base: Dict = None):
        """初始化知识库存储工具
        
        Args:
            knowledge_base: 知识库对象
        """
        super().__init__()
        self.knowledge_base = knowledge_base or {}
    
    async def _arun(self, entry: str) -> str:
        """异步存储到知识库"""
        try:
            entry_dict = json.loads(entry)
            result = await self.store_in_knowledge_base(entry_dict)
            return result
        except json.JSONDecodeError:
            return "错误：输入必须是有效的JSON字符串"
    
    def _run(self, entry: str) -> str:
        """存储到知识库"""
        loop = asyncio.get_event_loop()
        try:
            entry_dict = json.loads(entry)
            result = loop.run_until_complete(self.store_in_knowledge_base(entry_dict))
            return result
        except json.JSONDecodeError:
            return "错误：输入必须是有效的JSON字符串"
    
    async def store_in_knowledge_base(self, entry: Dict) -> str:
        """将条目存储到知识库
        
        Args:
            entry: 要存储的知识条目
            
        Returns:
            存储结果消息
        """
        if not entry.get("id"):
            entry["id"] = f"entry_{len(self.knowledge_base) + 1}"
        
        entry_id = entry["id"]
        self.knowledge_base[entry_id] = entry
        
        return f"成功存储条目，ID: {entry_id}"

def get_default_tools(knowledge_base: Dict = None) -> List[BaseTool]:
    """获取默认工具集
    
    Args:
        knowledge_base: 可选的知识库对象
        
    Returns:
        工具列表
    """
    kb = knowledge_base or {}
    
    return [
        WebSearchTool(),
        KnowledgeBaseSearchTool(knowledge_base=kb),
        KnowledgeBaseStorageTool(knowledge_base=kb)
    ] 