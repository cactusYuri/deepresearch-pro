import requests
import json
from typing import List, Dict, Any, Optional, Union

BaseUrl = 'https://api.bianxie.ai'
DeepseekBaseUrl = 'https://api.deepseek.com'

models = {
    'gpt-4o-mini': 'gpt-4o-mini',
    'gpt-4o': 'chatgpt-4o-latest',
    'o1': 'o1',
    'o3-mini-high': 'o3-mini-high',
    'claude-3-5-sonnet-20240620': 'claude-3-5-sonnet-20240620',
    'claude-3-7-sonnet':'claude-3-7-sonnet-20250219',
    'chatgpt-4o-latest':'chatgpt-4o-latest',
    'gemini-2.0-pro-latest': 'gemini-2.0-pro-exp',
    'gemini-2.0-flash-thinking': 'gemini-2.0-flash-thinking-exp',
    'deepseek-chat': 'deepseek-chat',
    'deepseek-reasoner': 'deepseek-reasoner',
    'gpt-4o-mini-search-preview': 'gpt-4o-mini-search-preview',
    'gpt-4o-search-preview': 'gpt-4o-search-preview'
}

# 判断是否为Deepseek模型
def is_deepseek_model(model_name: str) -> bool:
    return model_name.startswith('deepseek-')

async def GPT(input, selected_model='gpt-4o-mini'):
    # Debug flag
    debug = False
    if debug:
        return {"role": "gpt", "content": "这是测试使用,未连接GPT。 gptservers.py 7"}

    try:
        if selected_model not in models:
            raise ValueError(f"未知的模型: {selected_model}")
        
        # 针对不同模型源使用不同的处理逻辑
        if is_deepseek_model(selected_model):
            return await call_deepseek_api(input, selected_model)
        else:
            return await call_bianxie_api(input, selected_model)
            
    except Exception as error:
        print(f"Error: {error}")
        return {"role": "assistant", "content": f"请求失败: {str(error)}"}

async def call_bianxie_api(input, selected_model):
    """调用原有API"""
    data = {
        "model": models[selected_model],
        "messages": input
    }
    open_ai_keys = "sk-2ok6qeoYGcbMcbDvo294lUU06JWF5awPjB3tY9FTmlvGVRDk"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {open_ai_keys}'
    }
    
    # 设置代理为可选
    proxies = None
    try:
        # 测试代理是否可用
        test_response = requests.get(
            "http://127.0.0.1:33210",
            timeout=1
        )
        # 如果代理可用，则使用代理
        proxies = {
            "http": "http://127.0.0.1:33210",
            "https": "http://127.0.0.1:33210"
        }
    except:
        print("代理不可用，使用直接连接")

    try:
        response = requests.post(
            f"{BaseUrl}/v1/chat/completions",
            json=data,
            headers=headers,
            proxies=proxies,
            timeout=60
        )
        response.raise_for_status()  # Raise HTTPError for bad responses
        print("response:", response)
        print("response.json:", response.json())
        return response.json().get("choices", [{}])[0].get("message")
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        raise

async def call_deepseek_api(input, selected_model):
    """调用Deepseek API"""
    data = {
        "model": selected_model,
        "messages": input,
        "stream": False  # 单轮对话不使用流式响应
    }
    
    # 这里应填入Deepseek的API密钥
    deepseek_api_key = "sk-00d68421cffa4f1c91cbf538aa498867"  # 请填入有效的Deepseek API密钥
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {deepseek_api_key}'
    }
    
    # 设置代理为可选
    proxies = None
    try:
        # 测试代理是否可用
        test_response = requests.get(
            "http://127.0.0.1:33210",
            timeout=1
        )
        # 如果代理可用，则使用代理
        proxies = {
            "http": "http://127.0.0.1:33210",
            "https": "http://127.0.0.1:33210"
        }
    except:
        print("代理不可用，使用直接连接")

    try:
        response = requests.post(
            f"{DeepseekBaseUrl}/v1/chat/completions",
            json=data,
            headers=headers,
            proxies=proxies,
            timeout=60
        )
        response.raise_for_status()
        
        print("Deepseek response:", response)
        print("Deepseek response.json:", response.json())
        
        # 提取响应内容并转换为与原API相同的格式
        resp_data = response.json()
        return {
            "role": resp_data.get("choices", [{}])[0].get("message", {}).get("role", "assistant"),
            "content": resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        }
    except requests.RequestException as error:
        print(f"Deepseek request failed: {error}")
        raise

