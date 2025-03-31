import requests
import json
from typing import List, Dict, Any, Optional, Union

BaseUrl = 'https://api.bianxie.ai'
DeepseekBaseUrl = 'https://api.deepseek.com'
GeminiBaseUrl = 'https://generativelanguage.googleapis.com/v1beta'

ApiLoadCount = 0
# Import API keys from configuration file
try:
    from api_keys import gemini_keys,open_ai_keys,deepseek_api_keys
except ImportError:
    # Fallback if configuration file is not available
    gemini_keys = ['']
    open_ai_keys = ['']
    deepseek_api_keys = ['']

models = {
    'gpt-4o-mini': 'gpt-4o-mini',
    'gpt-4o': 'chatgpt-4o-latest',
    'o1': 'o1',
    'o3-mini-high': 'o3-mini-high',
    'claude-3-5-sonnet-20240620': 'claude-3-5-sonnet-20240620',
    'claude-3-7-sonnet':'claude-3-7-sonnet-20250219',
    'chatgpt-4o-latest':'chatgpt-4o-latest',
    'gemini-2.0-flash': 'gemini-2.0-flash',
    'gemini-2.0-pro-latest': 'gemini-2.0-pro-exp',
    'gemini-2.0-flash-thinking': 'gemini-2.0-flash-thinking-exp',
    'gemini-2.5-pro-exp-03-25':'gemini-2.5-pro-exp-03-25',
    'deepseek-chat': 'deepseek-chat',
    'deepseek-reasoner': 'deepseek-reasoner',
    'gpt-4o-mini-search-preview': 'gpt-4o-mini-search-preview',
    'gpt-4o-search-preview': 'gpt-4o-search-preview'
}

# 判断是否为Deepseek模型
def is_deepseek_model(model_name: str) -> bool:
    return model_name.startswith('deepseek-')
# 判断是否为 Gemini 模型
def is_gemini_model(model_name: str) -> bool:
    return model_name.startswith('gemini-')

async def GPT(input, selected_model='gpt-4o-mini'):
    # Debug flag
    debug = False
    if debug:
        return {"role": "gpt", "content": "这是测试使用,未连接GPT。 gptservers.py 7"}

    try:
        if selected_model not in models:
            raise ValueError(f"未知的模型: {selected_model}")
        
        # 针对不同模型源使用不同的处理逻辑
        if is_gemini_model(selected_model):
            return await call_gemini_api(input, selected_model)
        elif is_deepseek_model(selected_model):
            return await call_deepseek_api(input, selected_model)
        else:
            return await call_bianxie_api(input, selected_model)
            
    except Exception as error:
        print(f"Error: {error}")
        return {"role": "assistant", "content": f"请求失败: {str(error)}"}

async def call_bianxie_api(input, selected_model):
    global ApiLoadCount
    ApiLoadCount = ApiLoadCount + 1
    open_ai_key = open_ai_keys[ApiLoadCount % len(open_ai_keys)]

    """调用原有API"""
    data = {
        "model": models[selected_model],
        "messages": input
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {open_ai_key}'
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
    global ApiLoadCount
    ApiLoadCount = ApiLoadCount + 1
    deepseek_api_key = deepseek_api_keys[ApiLoadCount % len(deepseek_api_keys)]
    """调用Deepseek API"""
    data = {
        "model": selected_model,
        "messages": input,
        "stream": False  # 单轮对话不使用流式响应
    }
    
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


async def gemini_mode_list():
    global ApiLoadCount
    ApiLoadCount = ApiLoadCount + 1
    gemini_api_key = gemini_keys[ApiLoadCount % len(gemini_keys)]
    
    headers = {
        'Authorization': f'Bearer {gemini_api_key}'
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
        response = requests.get(
            f"{GeminiBaseUrl}/models?key={gemini_api_key}",
            #headers=headers,
            #proxies=proxies,
            timeout=60
        )
        response.raise_for_status()        
        print("Gemini response:", response)
        models = json.loads(response.content)
        print(models)

    except requests.RequestException as error:
        print(f"Gemini request failed: {error}")
        raise


#使用 兼容OpenAI 接口
async def call_gemini_api2(input, selected_model):
    global ApiLoadCount
    ApiLoadCount = ApiLoadCount + 1
    # 这里应填入 Gemini 的API密钥   
    gemini_api_key = gemini_keys[ApiLoadCount % len(gemini_keys)]
    
    """调用Gemini API"""
    data = {
        "model": selected_model,
        "messages": input,
        "stream": False  # 单轮对话不使用流式响应
    }
    
     
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {gemini_api_key}'
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
            f"{GeminiBaseUrl}/openai/chat/completions",
            json=data,
            headers=headers,
            proxies=proxies,
            timeout=60
        )
        response.raise_for_status()
        
        print("Gemini response:", response)
        print("Gemini response.json:", response.json())
        
        # 提取响应内容并转换为与原API相同的格式
        resp_data = response.json()
        return {
            "role": resp_data.get("choices", [{}])[0].get("message", {}).get("role", "assistant"),
            "content": resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        }
    except requests.RequestException as error:
        print(f"Gemini request failed: {error}")
        raise

#使用 Gemini 自身接口
async def call_gemini_api(input, selected_model):
    global ApiLoadCount
    ApiLoadCount = ApiLoadCount + 1
    """调用Gemini API"""
    
    # Convert OpenAI format to Gemini format 把输入转换成 Gemini 格式
    gemini_contents = []
    for message in input:
        role = "user" if message["role"] == "user" else "model"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })
    
    data = {
        "contents": gemini_contents
    }
    
    # 这里应填入 Gemini 的API密钥   
    gemini_api_key = gemini_keys[ApiLoadCount % len(gemini_keys)]
    
    headers = {
        'Content-Type': 'application/json'
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
            f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={gemini_api_key}",
            json=data,
            headers=headers,
            proxies=proxies,
            timeout=60
        )
        response.raise_for_status()
        
        print("Gemini response:", response)
        print("Gemini response.json:", response.json())
        
        # Extract response content from Gemini API format 输出转换成 OpenAI 格式
        resp_data = response.json()
        if "candidates" in resp_data and len(resp_data["candidates"]) > 0:
            candidate = resp_data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return {
                        "role": "assistant",
                        "content": parts[0]["text"]
                    }
        
        # Fallback if the structure is not as expected
        return {
            "role": "assistant",
            "content": "Unable to parse Gemini response properly."
        }
    except requests.RequestException as error:
        print(f"Gemini request failed: {error}")
        raise

