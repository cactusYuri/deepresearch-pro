"""
深度研究 Agent 输出整理系统
负责整理研究结果并生成结构化输出
"""

import json
import re
from typing import List, Dict, Any, Optional, Union
import asyncio
import sys
sys.path.append('..')
from LLMapi_service.gptservice import GPT

class OutputOrganizer:
    """输出整理器，将研究结果整理成结构化输出"""
    
    def __init__(self, model: str = "deepseek-chat"):
        """初始化输出整理器
        
        Args:
            model: 使用的大语言模型
        """
        self.model = model
    
    async def organize(self, query: str, research_results: Dict) -> Dict:
        """整理研究结果
        
        Args:
            query: 原始研究问题
            research_results: 研究结果
            
        Returns:
            整理后的输出
        """
        print("正在整理研究结果...")
        
        # 创建大纲
        outline = await self._create_outline(query, research_results)
        
        # 生成内容
        content = await self._generate_content(outline, research_results)
        
        return {
            "query": query,
            "outline": outline,
            "content": content
        }
    
    async def _create_outline(self, query: str, research_results: Dict) -> Dict:
        """创建研究报告大纲
        
        Args:
            query: 原始研究问题
            research_results: 研究结果
            
        Returns:
            大纲结构
        """
        # 构建提示
        messages = [
            {"role": "system", "content": """你是一个专业的研究报告组织者。
请为研究结果创建一个详细的大纲结构。大纲应该清晰、有条理，并涵盖所有重要内容。

请输出JSON格式，包含以下结构：
{
    "title": "报告标题",
    "sections": [
        {
            "id": "section_id",
            "title": "章节标题",
            "content_requirement": "本章节应该包含的内容描述",
            "subsections": [  // 可选，子章节
                {
                    "id": "subsection_id",
                    "title": "子章节标题",
                    "content_requirement": "子章节内容描述"
                },
                ...
            ]
        },
        ...
    ]
}

确保大纲结构符合研究内容，逻辑连贯，从问题描述到最终结论形成完整的研究报告。
"""}]
        
        # 添加用户提示
        user_prompt = f"研究问题：{query}\n"
        
        # 提取研究摘要或总结
        if research_results.get("is_complex", False) and "summary" in research_results:
            user_prompt += f"\n研究总结：{research_results['summary']}"
        elif "solution" in research_results:
            if isinstance(research_results["solution"], dict):
                user_prompt += f"\n研究内容：{research_results['solution'].get('solution', '')}"
            else:
                user_prompt += f"\n研究内容：{research_results['solution']}"
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            # 调用LLM创建大纲
            response = await GPT(messages, selected_model=self.model)
            
            # 尝试提取JSON内容
            content = response["content"]
            
            # 如果内容包含在代码块中，提取JSON部分
            if "```json" in content and "```" in content:
                json_part = content.split("```json")[1].split("```")[0].strip()
                content = json_part
            elif "```" in content and "```" in content:
                json_part = content.split("```")[1].split("```")[0].strip()
                content = json_part
            
            try:
                # 解析JSON
                outline = json.loads(content)
                
                # 验证大纲结构
                if "title" in outline and "sections" in outline and isinstance(outline["sections"], list):
                    return outline
            except json.JSONDecodeError:
                print(f"大纲JSON解析失败，使用默认大纲")
            
            # 解析失败，使用默认大纲
            return self._get_default_outline(query)
        except Exception as e:
            print(f"创建大纲时出错: {e}")
            # 如果解析失败，使用默认大纲
            return self._get_default_outline(query)
    
    def _get_default_outline(self, query: str) -> Dict:
        """生成默认大纲
        
        Args:
            query: 原始研究问题
            
        Returns:
            默认大纲结构
        """
        return {
            "title": f"关于「{query}」的深度研究",
            "sections": [
                {
                    "id": "introduction",
                    "title": "1. 引言",
                    "content_requirement": "介绍研究背景、目的和意义"
                },
                {
                    "id": "methodology",
                    "title": "2. 研究方法",
                    "content_requirement": "描述本次研究采用的方法和步骤"
                },
                {
                    "id": "findings",
                    "title": "3. 研究发现",
                    "content_requirement": "详细阐述研究的主要发现和结果"
                },
                {
                    "id": "analysis",
                    "title": "4. 分析与讨论",
                    "content_requirement": "对研究结果进行深入分析和讨论"
                },
                {
                    "id": "conclusion",
                    "title": "5. 结论",
                    "content_requirement": "总结研究结论，提出建议或展望"
                }
            ]
        }
    
    async def _generate_content(self, outline: Dict, research_results: Dict) -> Dict:
        """生成研究报告内容
        
        Args:
            outline: 大纲结构
            research_results: 研究结果
            
        Returns:
            生成的内容结构
        """
        content = {
            "title": outline["title"],
            "sections": []
        }
        
        print(f"生成报告内容，共 {len(outline['sections'])} 个章节...")
        
        # 生成每个章节的内容
        for i, section in enumerate(outline["sections"]):
            print(f"正在生成第 {i+1} 章: {section['title']}...")
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
        """生成单个章节的内容
        
        Args:
            section: 章节信息
            full_outline: 完整大纲
            research_results: 研究结果
            previous_sections: 已生成的前面章节
            section_index: 章节索引
            
        Returns:
            生成的章节内容
        """
        # 构建提示
        messages = [
            {"role": "system", "content": """你是一个专业的研究报告内容生成专家。
请根据大纲和研究结果，生成指定章节的内容。内容应详细、专业，并且与前面已生成的章节保持连贯性。

注意以下要点：
1. 内容要符合科学研究的规范，客观中立
2. 尽量使用事实和数据支持论点
3. 表达要清晰简洁，避免冗余
4. 格式应整洁，可使用适当的标题、列表等结构
5. 不要重复已经在前面章节中详细讨论过的内容
"""}]
        
        # 构建用户提示
        user_prompt = f"""
报告标题: {full_outline['title']}
当前章节: {section['title']}
章节要求: {section.get('content_requirement', '生成内容')}
当前是第 {section_index+1} 个章节，共 {len(full_outline['sections'])} 个章节。
"""

        # 为第一章节（通常是引言）提供更多研究背景
        if section_index == 0:
            # 提供完整的研究问题
            user_prompt += f"\n研究问题: {full_outline.get('title', '')}\n"
            
            # 添加研究结果摘要
            if "summary" in research_results:
                user_prompt += f"研究摘要: {research_results['summary']}\n"
            elif "solution" in research_results:
                if isinstance(research_results["solution"], dict):
                    user_prompt += f"研究摘要: {research_results['solution'].get('solution', '')}\n"
                else:
                    user_prompt += f"研究摘要: {research_results['solution']}\n"
        
        # 为分析章节提供更详细的研究结果
        elif section.get("id") in ["findings", "analysis"] or "发现" in section.get("title", "") or "分析" in section.get("title", ""):
            # 如果是复杂任务，提供子任务结果
            if research_results.get("is_complex", False) and "results" in research_results:
                # 找出最相关的子任务结果
                relevant_results = {}
                max_results = 3  # 最多包含3个子任务结果
                count = 0
                
                for task_id, result in research_results["results"].items():
                    if count >= max_results:
                        break
                        
                    # 查找任务描述
                    task_desc = None
                    for subtask in research_results.get("subtasks", []):
                        if subtask["id"] == task_id:
                            task_desc = subtask.get("description", "")
                            break
                    
                    # 获取任务结果
                    if task_desc:
                        # 尝试获取最合适的结果表示
                        if "summary" in result:
                            result_text = result["summary"]
                        elif "solution" in result:
                            if isinstance(result["solution"], dict):
                                result_text = result["solution"].get("solution", "")
                            else:
                                result_text = result["solution"]
                        else:
                            result_text = json.dumps(result, ensure_ascii=False)
                            
                        # 截断过长的结果
                        if len(result_text) > 500:
                            result_text = result_text[:500] + "..."
                            
                        relevant_results[task_desc] = result_text
                        count += 1
                
                # 添加到提示中
                if relevant_results:
                    user_prompt += "\n研究结果:\n"
                    for desc, res in relevant_results.items():
                        user_prompt += f"- {desc}: {res}\n"
            
            # 如果是简单任务，直接提供解决方案
            elif "solution" in research_results:
                if isinstance(research_results["solution"], dict):
                    user_prompt += f"\n研究结果: {research_results['solution'].get('solution', '')}\n"
                else:
                    user_prompt += f"\n研究结果: {research_results['solution']}\n"
        
        # 为结论章节提供完整的研究结果摘要
        elif section.get("id") in ["conclusion"] or "结论" in section.get("title", ""):
            if "summary" in research_results:
                user_prompt += f"\n研究总结: {research_results['summary']}\n"
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            # 调用LLM生成内容
            response = await GPT(messages, selected_model=self.model)
            
            section_content = {
                "id": section["id"],
                "title": section["title"],
                "content": response["content"]
            }
            
            # 如果有子章节，递归生成子章节内容
            if "subsections" in section and section["subsections"]:
                section_content["subsections"] = []
                
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
                        print(f"生成子章节 '{subsection.get('title', '')}' 时出错: {e}")
                        # 添加错误信息作为内容
                        section_content["subsections"].append({
                            "id": subsection.get("id", f"error_{i}"),
                            "title": subsection.get("title", "错误"),
                            "content": f"生成此部分内容时出现错误: {str(e)}"
                        })
            
            return section_content
        
        except Exception as e:
            print(f"生成章节 '{section.get('title', '')}' 时出错: {e}")
            return {
                "id": section["id"],
                "title": section["title"],
                "content": f"生成此章节内容时出错: {str(e)}"
            }
    
    def format_as_markdown(self, content: Dict) -> str:
        """将内容格式化为Markdown文本
        
        Args:
            content: 生成的内容结构
            
        Returns:
            Markdown格式的文本
        """
        markdown = f"# {content['title']}\n\n"
        
        for section in content["sections"]:
            markdown += self._format_section_as_markdown(section, 2)
        
        return markdown
    
    def _format_section_as_markdown(self, section: Dict, level: int) -> str:
        """递归地将章节格式化为Markdown
        
        Args:
            section: 章节内容
            level: 标题级别
            
        Returns:
            章节的Markdown文本
        """
        # 创建标题
        hashes = "#" * level
        markdown = f"{hashes} {section['title']}\n\n"
        
        # 添加内容
        if "content" in section and section["content"]:
            markdown += f"{section['content']}\n\n"
        
        # 递归添加子章节
        if "subsections" in section and section["subsections"]:
            for subsection in section["subsections"]:
                markdown += self._format_section_as_markdown(subsection, level + 1)
        
        return markdown
    
    def format_as_html(self, content: Dict) -> str:
        """将内容格式化为HTML文本
        
        Args:
            content: 生成的内容结构
            
        Returns:
            HTML格式的文本
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content['title']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #3498db;
            margin-top: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #2980b9;
            margin-top: 25px;
        }}
        h4 {{
            color: #1abc9c;
            margin-top: 20px;
        }}
        p {{
            margin-bottom: 15px;
        }}
        ul, ol {{
            margin-bottom: 15px;
        }}
        blockquote {{
            border-left: 4px solid #ccc;
            padding-left: 15px;
            color: #555;
            font-style: italic;
        }}
        code {{
            background-color: #f8f8f8;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <h1>{content['title']}</h1>
"""
        
        for section in content["sections"]:
            html += self._format_section_as_html(section, 2)
        
        html += """
</body>
</html>
"""
        
        return html
    
    def _format_section_as_html(self, section: Dict, level: int) -> str:
        """递归地将章节格式化为HTML
        
        Args:
            section: 章节内容
            level: 标题级别
            
        Returns:
            章节的HTML文本
        """
        # 创建标题
        html = f"<h{level}>{section['title']}</h{level}>\n"
        
        # 添加内容，将Markdown转换为HTML
        if "content" in section and section["content"]:
            content_html = section["content"]
            
            # 转换Markdown列表为HTML列表
            if re.search(r'(?m)^- .+$', content_html):
                # 匹配无序列表
                content_html = re.sub(r'(?m)^- (.+)$', r'<li>\1</li>', content_html)
                content_html = re.sub(r'(?s)<li>.*?</li>(\n<li>.*?</li>)*', r'<ul>\g<0></ul>', content_html)
            
            if re.search(r'(?m)^\d+\. .+$', content_html):
                # 匹配有序列表
                content_html = re.sub(r'(?m)^\d+\. (.+)$', r'<li>\1</li>', content_html)
                content_html = re.sub(r'(?s)<li>.*?</li>(\n<li>.*?</li>)*', r'<ol>\g<0></ol>', content_html)
            
            # 转换粗体
            content_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content_html)
            
            # 转换斜体
            content_html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content_html)
            
            # 转换换行和段落
            paragraphs = re.split(r'\n\n+', content_html)
            content_html = ""
            for p in paragraphs:
                if p.strip():
                    if not (p.startswith('<ul>') or p.startswith('<ol>') or p.startswith('<li>')):
                        content_html += f"<p>{p}</p>\n"
                    else:
                        content_html += f"{p}\n"
            
            html += content_html
        
        # 递归添加子章节
        if "subsections" in section and section["subsections"]:
            for subsection in section["subsections"]:
                html += self._format_section_as_html(subsection, level + 1)
        
        return html 