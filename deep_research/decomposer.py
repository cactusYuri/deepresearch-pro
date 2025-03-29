"""
深度研究 Agent 问题分解器模块
负责将复杂问题分解为多个子任务
"""

import json
from typing import List, Dict, Any, Optional, Union
import asyncio
import sys
sys.path.append('..')
from LLMapi_service.gptservice import GPT

class ProblemDecomposer:
    """问题分解器，用于将复杂问题分解为子任务"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """初始化问题分解器
        
        Args:
            model: 使用的大语言模型
        """
        self.model = model
    
    async def decompose(self, problem: str, context: Dict = None) -> List[Dict]:
        """将问题分解为子任务
        
        Args:
            problem: 要分解的问题
            context: 问题上下文
            
        Returns:
            子任务列表，每个子任务包含 id, description, depends_on 字段
        """
        # 构建提示
        prompt = self._build_decomposition_prompt(problem, context)
        
        # 调用LLM进行分解
        subtasks = await self._call_llm_for_decomposition(prompt)
        
        return subtasks
    
    def _build_decomposition_prompt(self, problem: str, context: Dict = None) -> List[Dict]:
        """构建问题分解提示
        
        Args:
            problem: 要分解的问题
            context: 问题上下文
            
        Returns:
            提示消息列表
        """
        context_str = json.dumps(context, ensure_ascii=False) if context else "{}"
        
        messages = [
            {"role": "system", "content": """你是一个专业的问题分解专家。
请将复杂问题分解为多个独立的子任务，确保子任务：
1. 相对独立，可以并行解决
2. 有明确的依赖关系
3. 共同构成对原问题的完整解决方案

输出JSON格式数组，每个子任务包含以下字段：
1. id: 子任务唯一标识符（字符串）
2. description: 子任务详细描述
3. depends_on: 数组，表示依赖的其他子任务ID（如有）
"""},
            {"role": "user", "content": f"问题：{problem}\n上下文：{context_str}"}
        ]
        
        return messages
    
    async def _call_llm_for_decomposition(self, messages: List[Dict]) -> List[Dict]:
        """调用LLM进行问题分解
        
        Args:
            messages: 提示消息列表
            
        Returns:
            分解的子任务列表
        """
        response = await GPT(messages, selected_model=self.model)
        
        try:
            # 尝试将返回内容解析为JSON
            subtasks = json.loads(response["content"])
            if isinstance(subtasks, list):
                # 验证每个子任务的格式
                for task in subtasks:
                    if "id" not in task or "description" not in task:
                        # 如果格式不正确，使用默认格式
                        return self._get_default_subtasks(messages[1]["content"])
                return subtasks
            else:
                return self._get_default_subtasks(messages[1]["content"])
        except json.JSONDecodeError:
            # 如果解析失败，使用默认方式分解
            return self._get_default_subtasks(messages[1]["content"])
    
    def _get_default_subtasks(self, problem: str) -> List[Dict]:
        """当LLM分解失败时，使用默认方式分解问题
        
        Args:
            problem: 原始问题
            
        Returns:
            默认的子任务列表
        """
        # 简单地创建三个子任务
        return [
            {
                "id": "research",
                "description": f"搜集与'{problem}'相关的信息",
                "depends_on": []
            },
            {
                "id": "analyze",
                "description": f"分析'{problem}'的各个方面",
                "depends_on": ["research"]
            },
            {
                "id": "conclude",
                "description": f"总结'{problem}'的解决方案",
                "depends_on": ["analyze"]
            }
        ]

class TaskDependencyResolver:
    """任务依赖解析器，用于排序子任务"""
    
    @staticmethod
    def resolve_execution_order(tasks: List[Dict]) -> List[Dict]:
        """解析任务的执行顺序
        
        Args:
            tasks: 子任务列表
            
        Returns:
            按照依赖关系排序后的任务列表
        """
        # 创建任务ID到任务的映射
        task_map = {task["id"]: task for task in tasks}
        
        # 创建任务依赖图
        dependency_graph = {task["id"]: set(task.get("depends_on", [])) for task in tasks}
        
        # 拓扑排序
        sorted_ids = TaskDependencyResolver._topological_sort(dependency_graph)
        
        # 按照排序结果重新排列任务
        return [task_map[task_id] for task_id in sorted_ids if task_id in task_map]
    
    @staticmethod
    def _topological_sort(graph: Dict[str, set]) -> List[str]:
        """对任务进行拓扑排序
        
        Args:
            graph: 依赖关系图
            
        Returns:
            排序后的任务ID列表
        """
        # 计算入度
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1
        
        # 初始化队列，包含所有入度为0的节点
        queue = [node for node in in_degree if in_degree[node] == 0]
        sorted_result = []
        
        # BFS拓扑排序
        while queue:
            node = queue.pop(0)
            sorted_result.append(node)
            
            # 更新依赖于当前节点的所有节点
            dependencies = [n for n in graph if node in graph[n]]
            for dependency in dependencies:
                in_degree[dependency] -= 1
                if in_degree[dependency] == 0:
                    queue.append(dependency)
        
        # 检查是否存在环
        if len(sorted_result) != len(graph):
            # 有环，按原顺序返回
            return list(graph.keys())
        
        return sorted_result 