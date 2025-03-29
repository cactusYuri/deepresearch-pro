"""
测试研究报告内容生成
"""

import os
import json
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_research.agent import DeepResearchAgent

async def test_report_generation():
    """测试研究报告内容生成"""
    
    # 创建测试目录
    output_dir = "test_report_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建Agent实例
    agent = DeepResearchAgent(model="deepseek-chat")
    
    # 测试查询
    query = "大语言模型在教育领域的应用"
    
    print(f"开始测试查询：{query}")
    print("=" * 50)
    
    # 执行研究
    try:
        # 限制生成的章节数，加快测试速度
        results = await agent.research(query)
        
        # 保存结果
        with open(os.path.join(output_dir, "test_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 打印报告标题
        print(f"报告标题：{results['content']['title']}")
        print("-" * 50)
        
        # 打印章节标题和部分内容
        for section in results['content']['sections']:
            section_title = section.get('title', '无标题')
            section_content = section.get('content', '无内容')
            
            print(f"章节：{section_title}")
            # 显示内容的前200个字符
            content_preview = section_content[:200] + "..." if len(section_content) > 200 else section_content
            print(f"内容预览：{content_preview}")
            print("-" * 50)
            
        print(f"完整报告已保存至 {os.path.join(output_dir, 'test_results.json')}")
        
    except Exception as e:
        print(f"测试出错：{str(e)}")
    
    print("测试完成!")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_report_generation()) 