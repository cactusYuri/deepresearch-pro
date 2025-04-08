"""
测试网络搜索功能
"""

import os
import json
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_research.tools import WebSearchTool

async def test_web_search():
    """测试网络搜索功能"""
    
    # 创建搜索工具实例
    search_tool = WebSearchTool()
    
    # 测试查询
    test_queries = [
        #"2024年人工智能领域的最新进展",
        #"深度学习在医疗领域的应用",
        "量子计算的商业应用案例"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"测试查询: {query}")
        print(f"{'='*50}")
        
        # 执行搜索
        try:
            results_json = await search_tool._arun(query)
            results = json.loads(results_json)
            
            # 打印结果
            print(f"找到 {len(results)} 条结果:")
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"标题: {result.get('title', '无标题')}")
                print(f"URL: {result.get('url', '无URL')}")
                print(f"摘要: {result.get('snippet', '无摘要')[:150]}...")
                
        except Exception as e:
            print(f"搜索出错: {str(e)}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_web_search()) 