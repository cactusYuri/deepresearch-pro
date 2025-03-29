"""
深度研究 Agent 测试示例
提供一个简单的测试脚本，展示系统的基本用法
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 添加父目录到路径中，以便导入deep_research
sys.path.append('..')

from agent import DeepResearchAgent
from main import run_research

async def test_simple_research():
    """运行一个简单的研究示例"""
    print("==== 简单研究示例 ====")
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"output/test_simple_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 执行简单研究
    query = "量子计算的基本原理和应用场景"
    
    try:
        # 使用默认模型(deepseek-chat)
        result = await run_research(
            query=query,
            output_dir=output_dir,
            output_format="all"
        )
        
        print(f"\n研究完成，结果已保存至: {output_dir}")
        
        # 显示研究报告标题和章节
        if "content" in result and "title" in result["content"]:
            print(f"\n报告标题: {result['content']['title']}")
            print("\n章节列表:")
            for i, section in enumerate(result["content"].get("sections", [])):
                print(f"{i+1}. {section.get('title', '未命名章节')}")
        
    except Exception as e:
        print(f"研究过程中发生错误: {e}")

async def test_complex_research():
    """运行一个更复杂的研究示例"""
    print("\n==== 复杂研究示例 ====")
    
    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"output/test_complex_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 执行复杂研究
    query = "生成式人工智能对知识产权和创意产业的影响分析"
    
    try:
        # 直接使用DeepResearchAgent进行研究
        agent = DeepResearchAgent(model="deepseek-chat")
        results = await agent.research(query)
        
        # 保存研究结果
        with open(os.path.join(output_dir, "raw_results.json"), "w", encoding="utf-8") as f:
            json.dump(results["raw_results"], f, ensure_ascii=False, indent=2)
        
        # 显示研究摘要
        if "raw_results" in results:
            if results["raw_results"].get("is_complex", False):
                print("\n这是一个复杂研究，包含多个子任务:")
                for subtask in results["raw_results"].get("subtasks", []):
                    print(f"- {subtask.get('description', '未命名任务')}")
                
                if "summary" in results["raw_results"]:
                    print("\n研究摘要:")
                    print(results["raw_results"]["summary"][:500] + "..." if len(results["raw_results"]["summary"]) > 500 else results["raw_results"]["summary"])
            else:
                print("\n这是一个简单研究，直接给出解决方案:")
                solution = results["raw_results"].get("solution", {}).get("solution", "")
                print(solution[:500] + "..." if len(solution) > 500 else solution)
        
        print(f"\n研究完成，结果已保存至: {output_dir}")
        
    except Exception as e:
        print(f"研究过程中发生错误: {e}")

async def main():
    """主函数，运行所有测试示例"""
    print("深度研究 Agent 测试示例")
    print("------------------------")
    
    # 运行简单研究示例
    await test_simple_research()
    
    # 运行复杂研究示例
    await test_complex_research()
    
    print("\n所有测试完成!")

if __name__ == "__main__":
    asyncio.run(main()) 