import asyncio
from gptservice import GPT
from deepseek_conversation import DeepseekConversation

async def demo_single_round():
    """演示单轮对话的使用方法"""
    print("==================== 单轮对话示例 ====================")
    
    # 使用原有模型
    messages = [{"role": "user", "content": "证明素数有无数个。"}]
    response = await GPT(messages, selected_model='o3-mini-high')
    print(f"\n原始模型 (o3-mini-high) 回复: {response['content']}")


async def demo_multi_round():
    """演示多轮对话的使用方法"""
    print("\n\n==================== 多轮对话示例 ====================")
    
    # 需要填入有效的Deepseek API密钥
    api_key = ""  # 请替换为实际的API密钥
    
    # 创建对话实例
    conversation = DeepseekConversation(api_key=api_key)
    
    # 第一轮对话
    print("\n第一轮对话:")
    response = conversation.chat("9.11和9.8，哪个更大？", model="deepseek-reasoner")
    print(f"AI回复: {response['content']}")
    
    # 第二轮对话
    print("\n第二轮对话:")
    response = conversation.chat("'strawberry'这个单词中有多少个字母'r'？", model="deepseek-reasoner")
    print(f"AI回复: {response['content']}")
    
    # 显示完整对话历史
    print("\n完整对话历史:")
    for msg in conversation.get_messages():
        print(f"{msg['role']}: {msg['content']}")

async def demo_stream():
    """演示流式响应的使用方法"""
    print("\n\n==================== 流式响应示例 ====================")
    
    # 需要填入有效的Deepseek API密钥
    api_key = ""  # 请替换为实际的API密钥
    
    # 创建新的对话实例
    conversation = DeepseekConversation(api_key=api_key)
    
    print("\n使用deepseek-reasoner进行流式对话:")
    print("\n用户: 计算23 * 45的结果，并解释计算过程")
    
    print("\nAI回复 (流式):")
    for chunk in conversation.chat_stream("计算23 * 45的结果，并解释计算过程", model="deepseek-reasoner"):
        if chunk["reasoning_content"]:
            print(f"\r推理过程: {chunk['full_reasoning_content']}", end="", flush=True)
        if chunk["content"]:
            print(f"\r回复内容: {chunk['full_content']}", end="", flush=True)

async def main():
    """主函数"""
    print("GPT服务和Deepseek多轮对话演示")
    print("注意: 请确保在运行前已替换API密钥\n")
    
    # 运行单轮对话示例
    await demo_single_round()
    
    # 运行多轮对话示例
    #await demo_multi_round()
    
    # 运行流式响应示例
    #await demo_stream()

if __name__ == "__main__":
    asyncio.run(main()) 