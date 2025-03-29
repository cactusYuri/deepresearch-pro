# 深度研究 LLM Agent

一个基于 langchain 的递归深度研究 AI 代理系统，能够进行深入研究并生成结构化报告。

## 功能特点

- **递归研究系统**：对复杂问题进行分解，并递归地解决子问题
- **检索增强**：通过网络搜索和知识库搜索增强研究能力
- **问题拆解**：自动将复杂问题分解为多个子任务
- **结构化输出**：生成包含大纲和详细内容的研究报告
- **多种输出格式**：支持 Markdown、HTML 和 JSON 格式的输出

## 系统架构

该系统由以下主要模块组成：

1. **研究系统**
   - 检索增强模块：网络搜索和知识库搜索
   - 问题拆解模块：将问题分解为 JSON 格式的子任务
   - 解决模块：解决具体子任务

2. **整理输出系统**
   - 大纲节点：生成研究报告大纲
   - 具体实现节点：生成各个章节的具体内容

## 安装依赖

```bash
pip install langchain langchain-core aiohttp
```

## 使用方法

### 命令行使用

```bash
python main.py "你的研究问题" --model "gpt-4o-mini" --output-dir "output" --output-format "all"
```

参数说明：
- 第一个参数：研究问题
- `--model`：指定使用的 LLM 模型（默认为 gpt-4o-mini）
- `--output-dir`：指定输出目录（默认为 output）
- `--output-format`：指定输出格式，可选值为 markdown、html、json、all（默认为 all）

### 代码中使用

```python
import asyncio
from deep_research.main import run_research

# 执行研究
asyncio.run(run_research(
    query="探索人工智能在医疗领域的最新应用和发展趋势",
    model="gpt-4o-mini",
    output_dir="output",
    output_format="all"
))
```

## 目录结构

```
deep_research/
├── agent.py           # 主代理模块
├── tools.py           # 工具模块（网络搜索、知识库搜索等）
├── decomposer.py      # 问题分解器模块
├── knowledge_base.py  # 知识库模块
├── output_organizer.py # 输出整理模块
├── main.py            # 主程序入口
└── README.md          # 说明文档
```

## 工作原理

1. **输入研究问题**：系统接收用户提供的研究问题
2. **评估复杂度**：评估问题复杂度，决定是否需要分解
3. **问题分解**：如果问题复杂，系统会将其分解为多个子任务
4. **递归解决**：
   - 对于复杂子任务，继续进行分解
   - 对于简单子任务，直接调用解决模块解决
5. **知识整合**：将所有子任务的解决方案整合到知识库
6. **生成报告**：根据研究结果生成结构化的研究报告
7. **输出结果**：以用户指定的格式输出研究报告

## 示例输出

研究报告通常包括以下章节：

1. **引言**：介绍研究背景、目的和意义
2. **研究方法**：描述本次研究采用的方法和步骤
3. **研究发现**：详细阐述研究的主要发现和结果
4. **分析与讨论**：对研究结果进行深入分析和讨论
5. **结论**：总结研究结论，提出建议或展望

## 自定义与扩展

### 添加新的搜索工具

编辑 `tools.py` 文件，添加新的搜索工具类。例如：

```python
class CustomSearchTool(BaseTool):
    name = "custom_search"
    description = "使用自定义搜索引擎搜索信息"
    
    async def _arun(self, query: str) -> str:
        # 实现自定义搜索逻辑
        pass
```

### 自定义知识库

知识库默认使用本地JSON文件存储，可以修改 `knowledge_base.py` 以支持其他存储方式，如数据库：

```python
class DatabaseKnowledgeBase(KnowledgeBase):
    def __init__(self, connection_string):
        self.db = Database(connection_string)
        
    def add_entry(self, entry):
        # 实现数据库存储逻辑
        pass
```

## 注意事项

- 确保已正确设置 API 密钥（在 LLMapi_service 中）
- 复杂研究可能会消耗较多的 API 调用次数
- 建议为较大的研究任务设置较长的超时时间

## 许可证

MIT 许可证 