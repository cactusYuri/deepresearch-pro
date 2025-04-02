"""
深度研究 LLM Agent 主模块
实现基于 langchain 的递归研究系统
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
import asyncio
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.agents import AgentExecutor
from langchain.tools import Tool

# 导入WebSearchTool
from deep_research.tools import WebSearchTool

# 导入自定义的LLM接口
import sys
sys.path.append('..')
from LLMapi_service.gptservice import GPT

from deep_research.config import DEFAULT_MODEL

# 设置默认最大递归深度
DEFAULT_MAX_RECURSION_DEPTH = 3
# 设置任务的最小复杂度阈值
COMPLEXITY_THRESHOLD = 0.6

class DeepResearchNode:
    """深度研究节点，用于递归解决复杂问题"""
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        tools: List[BaseTool] = None,
        parent_node = None,
        node_id: str = "root",
        research_context: Dict = None,
        knowledge_base = None,
        depth: int = 0,
        max_recursion_depth: int = DEFAULT_MAX_RECURSION_DEPTH,
        model: str = DEFAULT_MODEL
    ):
        self.llm = llm
        self.tools = tools or []
        self.parent_node = parent_node
        self.node_id = node_id
        self.research_context = research_context or {}
        self.knowledge_base = knowledge_base
        self.child_nodes = []
        self.results = {}
        self.depth = depth  # 当前节点深度
        self.max_recursion_depth = max_recursion_depth  # 最大递归深度
        self.model = model
        
        # 初始化WebSearchTool
        # 检查传入的tools中是否有WebSearchTool
        self.web_search_tool = None
        for tool in self.tools:
            if isinstance(tool, WebSearchTool):
                self.web_search_tool = tool
                break
        
        # 如果没有找到WebSearchTool，创建一个新的
        if self.web_search_tool is None:
            self.web_search_tool = WebSearchTool()
    
    async def process_task(self, task: str, context: Dict = None) -> Dict:
        """处理任务，评估复杂度，决定是否需要拆分"""
        
        # 检查递归深度
        if self.depth >= self.max_recursion_depth:
            print(f"达到最大递归深度 {self.max_recursion_depth}，直接解决任务: {task}")
            solution = await self._solve_task(task, context or {})
            await self._store_in_knowledge_base(task, "max_depth_reached", None, solution)
            return {
                "task": task,
                "is_complex": False,
                "depth": self.depth,
                "solution": solution
            }
            
        # 合并上下文
        current_context = {
            "task": task,
            "parent_context": self.research_context,
        }
        if context:
            current_context.update(context)
            
        # 1. 检索增强阶段 - 仅在深度较浅时执行以节省API调用
        if self.depth <= 1:
            enhanced_context = await self._enhance_with_retrieval(task, current_context)
        else:
            enhanced_context = current_context
        
        # 2. 评估任务复杂度
        complexity_assessment = await self._assess_complexity(task, enhanced_context)
        
        print(f"任务复杂度评估 [{self.node_id}] - '{task[:50]}...': {complexity_assessment}")
        
        # 3. 根据复杂度决定是否需要拆分任务
        if complexity_assessment["is_complex"] and self.depth < self.max_recursion_depth:
            print(f"拆分复杂任务 [{self.node_id}]: {task[:50]}...")
            subtasks = await self._decompose_task(task, enhanced_context)
            
            # 限制子任务数量，防止过度分解
            if len(subtasks) > 5:
                subtasks = subtasks[:5]
                
            results = await self._process_subtasks(subtasks, enhanced_context)
            
            # 存储结果到知识库
            await self._store_in_knowledge_base(task, "complex", subtasks, results)
            
            # 在结果中包含任务细节
            solution_summary = await self._summarize_solutions(task, subtasks, results) 
            
            return {
                "task": task,
                "is_complex": True,
                "depth": self.depth,
                "subtasks": subtasks,
                "results": results,
                "summary": solution_summary
            }
        else:
            # 直接解决任务
            print(f"直接解决任务 [{self.node_id}]: {task[:50]}...")
            solution = await self._solve_task(task, enhanced_context)
            
            # 存储结果到知识库
            await self._store_in_knowledge_base(task, "simple", None, solution)
            
            return {
                "task": task,
                "is_complex": False,
                "depth": self.depth,
                "solution": solution
            }
    
    async def _summarize_solutions(self, task: str, subtasks: List[Dict], results: Dict) -> str:
        """总结子任务的解决方案"""
        
        # 如果子任务太多，限制数量以减少处理量
        summary_subtasks = subtasks[:3] if len(subtasks) > 3 else subtasks
        summary_results = {k: results[k] for k in [t["id"] for t in summary_subtasks] if k in results}
        
        # 构建提示
        messages = [
            {"role": "system", "content": """你是一位专业的研究综合专家。
请总结多个子任务的研究结果，形成一个连贯、全面的综合解决方案。
你的总结应该简洁明了，突出关键发现，并确保逻辑连贯。
"""},
            {"role": "user", "content": f"""
原始任务: {task}
子任务及结果:
{json.dumps(summary_results, ensure_ascii=False, indent=2)}

请提供一个综合性总结，整合所有子任务的关键发现。
"""}
        ]
        
        response = await GPT(messages, selected_model=self.model)
        return response["content"]
    
    async def _enhance_with_retrieval(self, task: str, context: Dict) -> Dict:
        """通过检索增强上下文"""
        enhanced_context = context.copy()
        
        # 为节省API调用，只有在前两级节点才执行检索
        if self.depth <= 1:
            try:
                # 使用实际的WebSearchTool进行网络搜索
                web_search_results = await self._web_search(task)
                if web_search_results:
                    enhanced_context["web_search"] = web_search_results
                    
                # 知识库搜索增强 
                kb_search_results = await self._knowledge_base_search(task)
                if kb_search_results:
                    enhanced_context["kb_search"] = kb_search_results
            except Exception as e:
                print(f"检索增强阶段出错: {e}")
            
        return enhanced_context
    
    async def _web_search(self, query: str) -> List[Dict]:
        """执行网络搜索"""
        try:
            print(f"使用WebSearchTool执行搜索: {query}")
            # 调用WebSearchTool进行实际搜索
            search_results_json = await self.web_search_tool._arun(query)
            # 解析JSON结果
            search_results = json.loads(search_results_json)
            
            print(f"搜索结果: {len(search_results)} 条")
            return search_results
        except Exception as e:
            print(f"网络搜索出错: {e}")
            # 出错时返回空结果
            return []
    
    async def _knowledge_base_search(self, query: str) -> List[Dict]:
        """在知识库中搜索相关信息"""
        if not self.knowledge_base:
            return []
            
        # 简单实现关键词匹配
        results = []
        query_lower = query.lower()
        
        for entry_id, entry in self.knowledge_base.items():
            entry_str = json.dumps(entry, ensure_ascii=False).lower()
            if query_lower in entry_str:
                results.append({"id": entry_id, "entry": entry})
                
        return results[:3]  # 限制结果数量
    
    async def _assess_complexity(self, task: str, context: Dict) -> Dict:
        """评估任务复杂度"""
        # 如果已经到达较深层级，默认为简单任务
        if self.depth >= self.max_recursion_depth - 1:
            return {"is_complex": False, "reasoning": "达到最大允许深度，视为简单任务"}
        
        # 调用LLM评估任务复杂度
        messages = [
            {"role": "system", "content": """你是一个任务复杂度评估专家。
请评估给定任务的复杂度，判断是否需要进一步分解为子任务。

任务复杂度的判断标准：
1. 是否需要多步骤解决
2. 是否涉及多个不同领域或角度
3. 是否需要收集和分析大量信息
4. 是否存在多个相互关联的子问题

请以JSON格式回答：
{
    "is_complex": true或false,
    "reasoning": "你的解释...",
    "complexity_score": 0.1到1.0之间的数值（越高越复杂）
}
"""},
            {"role": "user", "content": f"""
任务：{task}
当前深度：{self.depth}
递归上限：{self.max_recursion_depth}

上下文：
{json.dumps(context, ensure_ascii=False, indent=2)}

请评估该任务的复杂度。
"""}
        ]
        
        try:
            response = await GPT(messages, selected_model=self.model)
            content = response["content"]
            
            # 尝试解析JSON
            try:
                # 如果内容被包裹在代码块中，提取JSON部分
                if "```json" in content and "```" in content:
                    json_part = content.split("```json")[1].split("```")[0].strip()
                    assessment = json.loads(json_part)
                elif "```" in content:
                    json_part = content.split("```")[1].split("```")[0].strip()
                    assessment = json.loads(json_part)
                else:
                    assessment = json.loads(content)
                
                # 验证评估结果
                if "is_complex" in assessment:
                    # 如果复杂度分数低于阈值，则视为简单任务
                    if "complexity_score" in assessment and float(assessment["complexity_score"]) < COMPLEXITY_THRESHOLD:
                        assessment["is_complex"] = False
                    return assessment
            except (json.JSONDecodeError, ValueError):
                print(f"评估结果解析失败: {content}")
            
            # 简单规则：如果回答中包含"复杂"或"需要分解"等关键词，则视为复杂任务
            is_complex = any(keyword in content.lower() for keyword in ["complex", "complicated", "multiple", "分解", "复杂", "多个"])
            reasoning = "基于关键词判断的备选复杂度评估"
            
            return {
                "is_complex": is_complex,
                "reasoning": reasoning,
                "complexity_score": 0.7 if is_complex else 0.3
            }
        except Exception as e:
            print(f"评估任务复杂度时出错: {e}")
            # 出错时，如果在较深层级，倾向于视为简单任务
            return {
                "is_complex": self.depth < 1,
                "reasoning": f"评估出错，基于深度判断: {str(e)}",
                "complexity_score": 0.5
            }
    
    async def _decompose_task(self, task: str, context: Dict) -> List[Dict]:
        """将复杂任务分解为多个子任务"""
        # 调用LLM分解任务
        messages = [
            {"role": "system", "content": """你是一位专业的任务分解专家。
请将复杂的研究任务分解为多个更小、更具体的子任务。每个子任务应该:
1. 足够具体，可以独立解决
2. 共同涵盖原始任务的所有方面
3. 彼此之间有最小的重叠
4. 按照逻辑顺序排列

以JSON数组格式输出子任务列表，每个子任务包含:
[
    {
        "id": "task1",  // 任务唯一标识符
        "description": "子任务的具体描述",
        "requires": []  // 可选，依赖的其他任务ID列表
    },
    ...
]
仅输出JSON数组，无需额外说明。
"""},
            {"role": "user", "content": f"""
需要分解的任务: {task}

上下文信息:
{json.dumps(context, ensure_ascii=False, indent=2)}

请将此任务分解为3-5个更小、更具体的子任务。
"""}
        ]
        
        try:
            response = await GPT(messages, selected_model=self.model)
            content = response["content"]
            
            # 尝试解析JSON
            try:
                # 如果内容被代码块包装，提取JSON部分
                if "```json" in content and "```" in content:
                    json_part = content.split("```json")[1].split("```")[0].strip()
                    subtasks = json.loads(json_part)
                elif "```" in content:
                    json_part = content.split("```")[1].split("```")[0].strip()
                    subtasks = json.loads(json_part)
                else:
                    subtasks = json.loads(content)
                
                # 验证子任务
                if not isinstance(subtasks, list):
                    raise ValueError("子任务应为数组")
                    
                for task in subtasks:
                    if not isinstance(task, dict):
                        raise ValueError("子任务应为对象")
                    if "id" not in task or "description" not in task:
                        raise ValueError("子任务缺少id或description字段")
                
                return subtasks
            except (json.JSONDecodeError, ValueError) as e:
                print(f"任务分解结果解析错误: {e}")
                # 尝试使用正则表达式提取
                import re
                matches = re.findall(r'"id":\s*"([^"]+)"[^}]*"description":\s*"([^"]+)"', content)
                if matches:
                    print("使用正则表达式提取子任务")
                    return [{"id": f"task{i+1}", "description": desc, "requires": []} 
                            for i, (_, desc) in enumerate(matches)]
                
                # 如果还是失败，使用简单方法创建子任务
                print("使用简单方法创建子任务")
                return [
                    {"id": "task1", "description": f"深入研究'{task}'的背景和上下文", "requires": []},
                    {"id": "task2", "description": f"分析'{task}'的核心问题和挑战", "requires": []},
                    {"id": "task3", "description": f"提供关于'{task}'的解决方案和建议", "requires": []}
                ]
        except Exception as e:
            print(f"分解任务时出错: {e}")
            return [
                {"id": "task1", "description": f"深入研究'{task}'的背景和上下文", "requires": []},
                {"id": "task2", "description": f"分析'{task}'的核心问题和挑战", "requires": []},
                {"id": "task3", "description": f"提供关于'{task}'的解决方案和建议", "requires": []}
            ]
    
    async def _process_subtasks(self, subtasks: List[Dict], context: Dict) -> Dict:
        """处理子任务列表"""
        results = {}
        
        for i, subtask in enumerate(subtasks):
            task_id = subtask["id"]
            task_desc = subtask["description"]
            
            print(f"处理子任务 {i+1}/{len(subtasks)}: {task_desc[:50]}...")
            
            # 创建子节点
            child_node = DeepResearchNode(
                llm=self.llm,
                tools=self.tools,  # 传递tools
                parent_node=self,
                node_id=f"{self.node_id}_{task_id}",
                research_context=context,
                knowledge_base=self.knowledge_base,
                depth=self.depth + 1,
                max_recursion_depth=self.max_recursion_depth
            )
            
            # 将子节点添加到当前节点的子节点列表
            self.child_nodes.append(child_node)
            
            # 处理子任务
            try:
                subtask_result = await child_node.process_task(task_desc)
                results[task_id] = subtask_result
            except Exception as e:
                print(f"处理子任务 {task_id} 时出错: {e}")
                results[task_id] = {
                    "error": str(e),
                    "task": task_desc
                }
        
        return results
    
    async def _solve_task(self, task: str, context: Dict) -> Dict:
        """解决不需要拆分的简单任务"""
        print(f"直接解决任务: {task[:100]}...")
        
        # 调用LLM解决任务
        messages = [
            {"role": "system", "content": """你是一位专业的研究助手。
你的任务是针对给定问题，提供全面而深入的回答。

你应该:
1. 分析问题的各个方面
2. 提供具体、详细的信息
3. 引用相关事实和数据
4. 在适当的情况下考虑不同观点
5. 提供清晰的结论或建议

确保你的回答全面、准确、有洞察力，并且对研究人员有帮助。
"""},
            {"role": "user", "content": f"""
任务: {task}

上下文信息:
{json.dumps(context, ensure_ascii=False, indent=2)}

请提供详细的解答。
"""}
        ]
        
        try:
            response = await GPT(messages, selected_model=self.model)
            solution = {
                "solution": response["content"],
                "context": context
            }
            return solution
        except Exception as e:
            print(f"解决任务时出错: {e}")
            return {"solution": f"解决任务时出错: {str(e)}", "context": context}
    
    async def _store_in_knowledge_base(self, task: str, task_type: str, subtasks: Optional[List] = None, results: Any = None):
        """将研究结果存储到知识库"""
        if not self.knowledge_base:
            return
            
        try:
            import time
            entry = {
                "node_id": self.node_id,
                "task": task,
                "task_type": task_type,
                "depth": self.depth,
                "subtasks": subtasks,
                "results": results,
                "timestamp": time.time()
            }
            
            # 使用节点ID作为条目ID
            self.knowledge_base[self.node_id] = entry
        except Exception as e:
            print(f"存储知识库时出错: {e}")

class DeepResearchAgent:
    """深度研究代理，管理整个研究流程"""
    
    def __init__(
        self, 
        model: str = DEFAULT_MODEL,
        max_recursion_depth: int = DEFAULT_MAX_RECURSION_DEPTH,
        knowledge_base: Dict = None
    ):
        """初始化深度研究代理
        
        Args:
            model: 使用的大语言模型名称
            max_recursion_depth: 研究的最大递归深度
        """
        self.model = model
        self.knowledge_base = knowledge_base or {}
        self.max_recursion_depth = max_recursion_depth
        self.root_node = None
        # 创建工具实例
        self.tools = [
            WebSearchTool(),  # 添加网络搜索工具
        ]
        # 添加进度回调函数和当前进度状态
        self.progress_callback = None
        self.current_progress = {
            "status": "initialized",
            "progress": 0,
            "message": "已初始化研究代理",
            "detail": {}
        }
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def update_progress(self, progress: int, message: str, detail: Dict = None):
        """更新进度信息并调用回调函数"""
        self.current_progress = {
            "status": "running", 
            "progress": progress,
            "message": message,
            "detail": detail or {}
        }
        
        if self.progress_callback:
            self.progress_callback(self.current_progress)
    
    async def research(self, query: str) -> Dict:
        """执行深度研究流程"""
        # 更新状态：开始研究
        self.update_progress(5, f"开始研究: {query[:50]}...", {"query": query})
        
        print(f"开始研究: {query}")
        print(f"使用模型: {self.model}")
        print(f"最大递归深度: {self.max_recursion_depth}")
        
        # 创建根研究节点
        self.root_node = DeepResearchNode(
            node_id="root",
            knowledge_base=self.knowledge_base,
            depth=0,
            max_recursion_depth=self.max_recursion_depth,  # 传递最大递归深度
            tools=self.tools  # 传递tools
        )
        
        # 通知前台开始处理核心问题
        self.update_progress(10, f"分析主要研究问题", {"node": "root"})
        
        # 执行研究
        research_results = await self.root_node.process_task(query)
        
        # 更新状态：研究完成，开始整理
        self.update_progress(75, "主要研究完成，开始整理结果", 
                            {"completed_nodes": 1, "total_depth": research_results.get("depth", 0)})
        
        # 整理输出
        output = await self._organize_output(query, research_results)
        
        # 更新状态：完成
        self.update_progress(95, "研究报告生成完成", 
                           {"sections": len(output.get("content", {}).get("sections", []))})
        
        return output

    async def _organize_output(self, query: str, research_results: Dict) -> Dict:
        """整理研究结果"""
        # 更新状态
        self.update_progress(80, "创建研究报告大纲", {})
        
        print("整理研究结果...")
        
        # 创建大纲
        outline = await self._create_outline(query, research_results)
        
        # 更新状态
        self.update_progress(85, "根据大纲生成完整内容", 
                           {"sections": len(outline.get("sections", []))})
        
        # 生成具体内容
        content = await self._generate_content(outline, research_results)
        
        return {
            "query": query,
            "outline": outline,
            "content": content,
            "raw_results": research_results
        }
        
    async def _create_outline(self, query: str, research_results: Dict) -> Dict:
        """创建输出大纲"""
        # 更新状态
        self.update_progress(82, "分析研究结果，构建报告框架", {})
        
        # 调用LLM生成大纲
        messages = [
            {"role": "system", "content": """你是专业的研究人员，需要创建一个实际的研究报告大纲。
请基于研究问题和研究结果，创建一个结构化的研究报告大纲，这个大纲将用于生成完整的研究报告内容。
输出应为JSON格式，包含以下结构：
{
    "title": "研究报告实际标题",
    "sections": [
        {
            "id": "section1",
            "title": "章节实际标题",
            "content_requirement": "本节实际内容方向的简要描述",
            "subsections": [...]  // 可选，子章节结构与sections相同
        },
        ...
    ]
}
重要：这不是写作指南，而是要生成一个会被直接用于生成实际研究报告的大纲。
"""},
            {"role": "user", "content": f"研究问题：{query}"}
        ]
        
        # 添加简化的研究结果概述
        if "summary" in research_results:
            messages[1]["content"] += f"\n\n研究结果概述：{research_results['summary']}"
        elif "solution" in research_results:
            messages[1]["content"] += f"\n\n研究结果概述：{research_results['solution']}"
        
        try:
            response = await GPT(messages, selected_model=self.model)
            
            # 解析JSON
            content = response.get("content", "{}")
            try:
                outline = json.loads(content)
            except json.JSONDecodeError:
                print(f"大纲格式错误，尝试修复...")
                # 尝试提取JSON部分
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    try:
                        outline = json.loads(json_match.group(1))
                    except:
                        print("修复失败，使用默认大纲")
                        outline = {"title": "研究报告", "sections": []}
                else:
                    print("无法提取JSON，使用默认大纲")
                    outline = {"title": "研究报告", "sections": []}
            
            return outline
        except Exception as e:
            print(f"创建大纲时出错: {e}")
            return {"title": f"关于'{query}'的研究", "sections": []}

    async def _generate_content(self, outline: Dict, research_results: Dict) -> Dict:
        """生成大纲内容"""
        content = {
            "title": outline["title"],
            "sections": []
        }
        
        # 处理任务依赖
        # 创建依赖任务映射
        task_dependencies = {}
        task_results = {}
        
        if "results" in research_results and "subtasks" in research_results:
            # 创建任务ID到任务描述的映射
            task_map = {task["id"]: task for task in research_results.get("subtasks", [])}
            
            # 检查任务是否完成，如果没有完成，使用简化处理
            for task_id, task_info in task_map.items():
                if task_id not in research_results.get("results", {}):
                    print(f"警告：任务 {task_id} 的依赖尚未完成，使用简化处理")
                    # 为未完成的任务创建简化结果
                    task_result = {
                        "task": task_info.get("description", "未知任务"),
                        "is_complex": False,
                        "solution": f"此部分内容基于简化处理生成，因为原始任务 '{task_info.get('description', '未知任务')}' 尚未完成。"
                    }
                    research_results.setdefault("results", {})[task_id] = task_result
        
        # 按顺序生成每个部分的内容
        current_section = 0
        total_sections = len(outline.get("sections", []))
        
        # 生成每个章节的内容
        for i, section in enumerate(outline["sections"]):
            # 更新进度
            progress = 85 + int(10 * i / max(1, total_sections))
            self.update_progress(progress, f"生成报告章节: {section.get('title', '章节')}", 
                                {"section": i+1, "total": total_sections})
            
            section_content = await self._generate_section_content(
                section, 
                outline,
                research_results,
                content["sections"],
                i
            )
            content["sections"].append(section_content)
        
        return content
    
    async def _generate_section_content(self, section: Dict, full_outline: Dict, research_results: Dict, previous_sections: List, section_index: int) -> Dict:
        """生成单个章节的内容"""
        # 调用LLM生成章节内容
        messages = [
            {"role": "system", "content": """你是专业的研究人员，正在撰写一份研究报告的具体章节内容。
请生成详实、专业、有深度的研究报告章节内容，不要包含写作指南或说明。
请直接输出可以放入研究报告的完整章节内容，包括观点、数据、分析和结论。
确保内容与前面章节连贯，不要重复已有内容，也不要包含如"本章将讨论..."之类的元描述。
输出应当是可以直接用于研究报告的最终内容。
"""}
        ]
        
        # 构建用户提示，根据节点位置提供不同级别的详细信息
        user_prompt = f"""
请撰写以下研究报告章节的实际内容：

报告标题: {full_outline['title']}
当前章节: {section['title']}
章节要求: {section.get('content_requirement', '详细阐述研究发现')}
"""

        # 为不同章节添加适当的研究结果信息
        if section_index == 0:  # 第一章节（通常是背景和介绍）
            # 提供简化的研究摘要
            if "summary" in research_results:
                user_prompt += f"\n研究背景: {research_results['summary'][:500]}"
            elif "solution" in research_results and isinstance(research_results['solution'], dict):
                user_prompt += f"\n研究背景: {research_results['solution'].get('solution', '')[:500]}"
            elif "solution" in research_results:
                user_prompt += f"\n研究背景: {research_results['solution'][:500]}"
                
        elif "results" in research_results and research_results.get("is_complex", False):
            # 对于后续章节，提供一些相关子任务的结果 
            relevant_results = {}
            subtask_count = 0
            
            # 从research_results中寻找与本章节最相关的子任务结果
            for task_id, task_result in research_results["results"].items():
                # 只选取3个最相关的子任务
                if subtask_count >= 3:
                    break
                    
                subtask_desc = ""
                for subtask in research_results.get("subtasks", []):
                    if subtask["id"] == task_id:
                        subtask_desc = subtask.get("description", "")
                        break
                
                # 添加到相关结果中
                if subtask_desc:
                    result_content = task_result.get("summary", "") or (
                        task_result.get("solution", {}).get("solution", "") 
                        if isinstance(task_result.get("solution"), dict) 
                        else task_result.get("solution", "")
                    )
                    relevant_results[subtask_desc] = result_content
                    subtask_count += 1
            
            # 添加到提示中
            if relevant_results:
                user_prompt += "\n研究内容相关信息:"
                for desc, result in relevant_results.items():
                    truncated_result = result[:300] + "..." if len(result) > 300 else result
                    user_prompt += f"\n- {desc}: {truncated_result}"
        
        # 添加前面章节的简要内容摘要，帮助保持连贯性
        if previous_sections:
            user_prompt += "\n\n前面章节简要内容摘要:"
            for prev_section in previous_sections[-2:]:  # 最多包含前2个章节
                prev_title = prev_section.get("title", "")
                prev_content = prev_section.get("content", "")
                if prev_content:
                    # 提取前100个字符作为摘要
                    prev_summary = prev_content[:100] + "..." if len(prev_content) > 100 else prev_content
                    user_prompt += f"\n- {prev_title}: {prev_summary}"
        
        user_prompt += "\n\n请直接输出此章节的完整内容，不要包含任何写作指南、元描述或非研究内容的文本。"
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            # 调用模型生成内容
            response = await GPT(messages, selected_model=self.model)
            
            section_content = {
                "id": section["id"],
                "title": section["title"],
                "content": response["content"]
            }
            
            # 如果有子章节，递归生成子章节内容
            if "subsections" in section and section["subsections"]:
                section_content["subsections"] = []
                
                # 递归处理子章节
                for i, subsection in enumerate(section["subsections"]):
                    try:
                        subsection_content = await self._generate_section_content(
                            subsection,
                            full_outline,
                            research_results,
                            section_content.get("subsections", []),
                            i
                        )
                        section_content["subsections"].append(subsection_content)
                    except Exception as e:
                        print(f"生成子章节内容时出错: {e}")
                        # 添加错误信息作为子章节内容
                        section_content["subsections"].append({
                            "id": subsection.get("id", f"error_{i}"),
                            "title": subsection.get("title", "错误章节"),
                            "content": f"生成此章节内容时出错: {str(e)}"
                        })
            
            return section_content
        except Exception as e:
            print(f"生成章节内容时出错: {e}")
            # 返回错误信息作为章节内容
            return {
                "id": section["id"],
                "title": section["title"],
                "content": f"生成此章节内容时出错: {str(e)}"
            }

# 使用示例
async def main():
    agent = DeepResearchAgent(model="deepseek-chat")
    result = await agent.research("探索人工智能在医疗领域的最新应用")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 