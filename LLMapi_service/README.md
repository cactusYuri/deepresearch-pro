# Deepseek 模型集成

这个项目将Deepseek模型集成到现有的GPT服务中，允许用户无缝切换使用不同的模型，包括原有的GPT模型和Deepseek模型。

## 文件说明

- `gptservice.py`: 集成了Deepseek模型的单轮对话服务
- `deepseek_conversation.py`: 实现了Deepseek模型的多轮对话功能
- `usage_example.py`: 使用示例代码

## 功能特点

- 支持原有模型和Deepseek模型的无缝切换
- 支持Deepseek的两种模型：`deepseek-chat`和`deepseek-reasoner`
- 提供单轮对话和多轮对话两种使用方式
- 支持流式响应，特别是对`deepseek-reasoner`的推理过程的实时获取

## 使用方法

### 单轮对话

使用`GPT`函数可以进行单轮对话，只需指定不同的模型名称即可：

```python
import asyncio
from gptservice import GPT

async def main():
    # 使用原有模型
    messages = [{"role": "user", "content": "你好，请介绍一下自己"}]
    response = await GPT(messages, selected_model='gpt-4o-mini')
    print(response['content'])
    
    # 使用Deepseek模型
    messages = [{"role": "user", "content": "你好，请介绍一下自己"}]
    response = await GPT(messages, selected_model='deepseek-chat')
    print(response['content'])
    
    # 使用Deepseek推理模型
    messages = [{"role": "user", "content": "9.11和9.8，哪个更大？"}]
    response = await GPT(messages, selected_model='deepseek-reasoner')
    print(response['content'])

if __name__ == "__main__":
    asyncio.run(main())
```

### 多轮对话

使用`DeepseekConversation`类可以进行多轮对话：

```python
from deepseek_conversation import DeepseekConversation

# 创建对话实例
conversation = DeepseekConversation(api_key="your_api_key")

# 第一轮对话
response = conversation.chat("9.11和9.8，哪个更大？", model="deepseek-reasoner")
print(f"AI: {response['content']}")

# 第二轮对话 (自动继承上下文)
response = conversation.chat("'strawberry'这个单词中有多少个字母'r'？", model="deepseek-reasoner")
print(f"AI: {response['content']}")

# 获取完整对话历史
for msg in conversation.get_messages():
    print(f"{msg['role']}: {msg['content']}")
```

### 流式响应

使用`chat_stream`方法可以获取流式响应：

```python
from deepseek_conversation import DeepseekConversation

conversation = DeepseekConversation(api_key="your_api_key")

# 流式响应
for chunk in conversation.chat_stream("计算23 * 45的结果", model="deepseek-reasoner"):
    if chunk["reasoning_content"]:
        print(f"推理过程: {chunk['reasoning_content']}", end="", flush=True)
    if chunk["content"]:
        print(f"回复内容: {chunk['content']}", end="", flush=True)
```

## 注意事项

1. 使用前请确保已经获取了Deepseek的API密钥并填入相应位置
2. 默认使用了本地代理（127.0.0.1:33210），如需修改请调整代码中的proxies配置
3. 对于`deepseek-reasoner`模型，可以通过流式响应获取实时的推理过程

## 示例运行

直接运行`usage_example.py`可以查看完整的使用示例：

```bash
python usage_example.py
``` 