"""
深度研究 Agent 主程序入口
提供命令行接口和示例用法
"""

import os
import json
import argparse
import asyncio
import traceback
from typing import Dict, List, Any, Optional
import sys
sys.path.append('..')

from deep_research.agent import DeepResearchAgent
from deep_research.knowledge_base import KnowledgeBase
from deep_research.output_organizer import OutputOrganizer

async def run_research(
    query: str, 
    model: str = "deepseek-chat", 
    output_dir: str = "output", 
    output_format: str = "markdown",
    max_depth: int = 3
):
    """
    执行深度研究并保存结果
    
    Args:
        query: 研究问题
        model: 使用的模型
        output_dir: 输出目录
        output_format: 输出格式，可选值: markdown, html, json
        max_depth: 最大递归研究深度
    """
    print(f"开始研究: {query}")
    print(f"使用模型: {model}")
    print(f"最大研究深度: {max_depth}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化知识库
    kb_path = os.path.join(output_dir, "knowledge_base.json")
    kb = KnowledgeBase(storage_path=kb_path)
    
    # 创建研究Agent并执行研究
    agent = DeepResearchAgent(model=model, max_recursion_depth=max_depth)
    agent.knowledge_base = kb.entries
    
    try:
        # 执行研究
        results = await agent.research(query)
        
        # 保存原始研究结果
        with open(os.path.join(output_dir, "raw_results.json"), "w", encoding="utf-8") as f:
            json.dump(results["raw_results"], f, ensure_ascii=False, indent=2)
        
        # 使用输出整理器格式化结果
        organizer = OutputOrganizer(model=model)
        
        # 根据输出格式保存结果
        if output_format == "markdown" or output_format == "all":
            markdown = organizer.format_as_markdown(results["content"])
            with open(os.path.join(output_dir, "research_report.md"), "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"Markdown 报告已保存至: {os.path.join(output_dir, 'research_report.md')}")
        
        if output_format == "html" or output_format == "all":
            html = organizer.format_as_html(results["content"])
            with open(os.path.join(output_dir, "research_report.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"HTML 报告已保存至: {os.path.join(output_dir, 'research_report.html')}")
        
        if output_format == "json" or output_format == "all":
            with open(os.path.join(output_dir, "research_content.json"), "w", encoding="utf-8") as f:
                json.dump(results["content"], f, ensure_ascii=False, indent=2)
            print(f"JSON 内容已保存至: {os.path.join(output_dir, 'research_content.json')}")
        
        print("研究完成!")
        return results
    
    except Exception as e:
        print(f"研究过程中发生错误: {e}")
        traceback.print_exc()
        
        # 保存错误信息
        error_file = os.path.join(output_dir, "error_log.txt")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"研究问题: {query}\n")
            f.write(f"错误信息: {str(e)}\n")
            f.write(f"详细堆栈:\n{traceback.format_exc()}")
        
        print(f"错误信息已保存至: {error_file}")
        raise

def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description="深度研究 LLM Agent")
    parser.add_argument("query", type=str, help="研究问题")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="使用的LLM模型")
    parser.add_argument("--output-dir", type=str, default="output", help="输出目录")
    parser.add_argument("--output-format", type=str, default="all", 
                        choices=["markdown", "html", "json", "all"], 
                        help="输出格式")
    parser.add_argument("--max-depth", type=int, default=3, 
                        help="最大递归研究深度，值越大研究越深入但API调用也越多")
    
    args = parser.parse_args()
    
    # 执行研究
    try:
        asyncio.run(run_research(
            query=args.query,
            model=args.model,
            output_dir=args.output_dir,
            output_format=args.output_format,
            max_depth=args.max_depth
        ))
    except KeyboardInterrupt:
        print("\n研究被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 命令行调用方式
    if len(sys.argv) > 1:
        main()
    else:
        # 直接运行示例
        try:
            asyncio.run(run_research(
                query="探索人工智能在医疗领域的最新应用和发展趋势",
                model="deepseek-chat",
                output_dir="output",
                output_format="all",
                max_depth=3  # 设置默认深度
            ))
        except KeyboardInterrupt:
            print("\n研究被用户中断")
        except Exception as e:
            print(f"发生错误: {e}")
            sys.exit(1) 