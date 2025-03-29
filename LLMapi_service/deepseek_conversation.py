import requests
import json
from typing import List, Dict, Any, Optional, Union, Generator

class DeepseekConversation:
    """
    实现Deepseek模型的多轮对话
    支持deepseek-chat和deepseek-reasoner模型
    """
    
    def __init__(self, api_key: str = "sk-00d68421cffa4f1c91cbf538aa498867", base_url: str = "https://api.deepseek.com"):
        """
        初始化DeepseekConversation实例
        
        Args:
            api_key: Deepseek API密钥
            base_url: Deepseek API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.messages = []
        self.proxies = {
            "http": "http://127.0.0.1:33210",
            "https": "http://127.0.0.1:33210"
        }
    
    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到对话历史
        
        Args:
            role: 消息角色 (user, assistant, system)
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})
    
    def clear_messages(self) -> None:
        """清空对话历史"""
        self.messages = []
    
    def get_messages(self) -> List[Dict[str, str]]:
        """获取当前的对话历史"""
        return self.messages
    
    def chat(self, user_message: str, model: str = "deepseek-chat", stream: bool = False) -> Dict[str, Any]:
        """
        发送单轮对话请求并获取回复（非流式）
        
        Args:
            user_message: 用户消息
            model: 模型名称 (deepseek-chat 或 deepseek-reasoner)
            stream: 是否使用流式响应
            
        Returns:
            包含AI回复的字典
        """
        # 添加用户消息到对话历史
        self.add_message("user", user_message)
        
        # 调用API
        response = self._call_api(model, stream=False)
        
        # 添加AI回复到对话历史
        if "content" in response:
            self.add_message("assistant", response["content"])
        
        return response
    
    def chat_stream(self, user_message: str, model: str = "deepseek-reasoner") -> Generator[Dict[str, Any], None, None]:
        """
        流式对话接口，通过生成器返回流式响应
        
        Args:
            user_message: 用户消息
            model: 模型名称 (deepseek-chat 或 deepseek-reasoner)
        
        Yields:
            包含AI响应片段的字典，对于deepseek-reasoner还包含reasoning_content
        """
        # 添加用户消息到对话历史
        self.add_message("user", user_message)
        
        # 调用流式API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            "model": model,
            "messages": self.messages,
            "stream": True
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=data,
            headers=headers,
            proxies=self.proxies,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")
        
        # 处理流式响应
        full_content = ""
        full_reasoning_content = ""
        
        for line in response.iter_lines():
            if not line:
                continue
                
            if line.startswith(b"data: "):
                line = line[6:]  # 去掉 "data: " 前缀
                
            if line == b"[DONE]":
                break
                
            try:
                chunk = json.loads(line)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                
                # 处理不同类型的内容
                content = delta.get("content", "")
                reasoning_content = delta.get("reasoning_content", "")
                
                if content:
                    full_content += content
                if reasoning_content:
                    full_reasoning_content += reasoning_content
                
                yield {
                    "content": content, 
                    "reasoning_content": reasoning_content,
                    "full_content": full_content,
                    "full_reasoning_content": full_reasoning_content
                }
            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {line}")
        
        # 将完整回复添加到对话历史
        if full_content:
            self.add_message("assistant", full_content)
    
    def _call_api(self, model: str, stream: bool = False) -> Dict[str, Any]:
        """
        调用Deepseek API
        
        Args:
            model: 模型名称
            stream: 是否使用流式响应
            
        Returns:
            API响应
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        data = {
            "model": model,
            "messages": self.messages,
            "stream": stream
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=data,
            headers=headers,
            proxies=self.proxies,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")
        
        response_data = response.json()
        
        # 提取回复内容
        message = response_data.get("choices", [{}])[0].get("message", {})
        return {
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "full_response": response_data
        }


# 使用示例
if __name__ == "__main__":
    # 使用示例
    api_key = ""  # 请填入有效的Deepseek API密钥
    
    # 创建对话实例
    conversation = DeepseekConversation(api_key=api_key)
    
    # 单轮非流式对话
    response = conversation.chat("今天天气怎么样？", model="deepseek-chat")
    print("非流式回复:", response["content"])
    
    # 使用deepseek-reasoner进行推理（流式）
    print("\n流式对话示例：")
    for chunk in conversation.chat_stream("9.11和9.8，哪个更大？", model="deepseek-reasoner"):
        if chunk["reasoning_content"]:
            print(f"推理过程: {chunk['reasoning_content']}", end="", flush=True)
        if chunk["content"]:
            print(f"回复内容: {chunk['content']}", end="", flush=True)
    
    # 显示完整对话历史
    print("\n\n对话历史:")
    for msg in conversation.get_messages():
        print(f"{msg['role']}: {msg['content']}") 