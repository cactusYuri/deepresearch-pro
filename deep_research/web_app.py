"""
深度研究 Agent 网页应用
提供网页界面，让用户可以输入研究查询
"""

import os
import json
import asyncio
import uuid
import traceback
from datetime import datetime
import sys
import threading
sys.path.append('..')

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# 导入深度研究模块
from deep_research.agent import DeepResearchAgent
from deep_research.knowledge_base import KnowledgeBase
from deep_research.output_organizer import OutputOrganizer

# 初始化Flask应用
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')

# 设置上传文件存储路径
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

# 存储后台运行的研究任务
research_tasks = {}

@app.route('/')
def index():
    """网站首页，展示研究查询输入表单"""
    models = [
        {"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "通用对话模型，适合大多数研究任务"},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "description": "推理能力更强，适合复杂分析"},
        {"id": "gemini2.5", "name": "gemini-2.5-pro-exp", "description": "推理能力更强，适合复杂分析"}
    ]
    
    # 添加研究深度选项
    depth_options = [
        {"value": 2, "name": "浅度研究（速度快，API消耗少）"},
        {"value": 3, "name": "标准研究（平衡速度和深度）", "default": True},
        {"value": 4, "name": "深度研究（更全面，API消耗较多）"},
        {"value": 5, "name": "极深研究（非常详尽，API消耗大）"}
    ]
    
    return render_template('index.html', models=models, depth_options=depth_options)

@app.route('/submit', methods=['POST'])
def submit_query():
    """处理用户提交的研究查询"""
    query = request.form.get('query', '')
    model = request.form.get('model', 'deepseek-chat')
    max_depth = int(request.form.get('max_depth', '3'))  # 获取用户设置的研究深度
    
    if not query:
        return render_template('index.html', error="请输入研究查询")
    
    # 生成唯一任务ID
    task_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建结果目录
    output_dir = os.path.join(app.config['RESULTS_FOLDER'], f"{task_id}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化任务状态
    task_info = {
        'id': task_id,
        'query': query,
        'model': model,
        'max_depth': max_depth,  # 存储研究深度
        'output_dir': output_dir,
        'status': 'running',
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'progress': 0,
        'message': '正在初始化研究...',
        'detail': {'stage': 'initialization'}
    }
    
    # 保存到全局研究任务字典
    research_tasks[task_id] = task_info
    
    # 保存初始任务信息到文件
    with open(os.path.join(output_dir, 'task_info.json'), 'w', encoding='utf-8') as f:
        json.dump(task_info, f, ensure_ascii=False, indent=2)
    
    print(f"创建新任务: {task_id}, 查询: {query}, 模型: {model}, 深度: {max_depth}")
    
    # 在新线程中运行异步任务
    def run_async_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(start_research_task(task_id, query, model, output_dir, max_depth))
        finally:
            loop.close()
    
    # 启动线程
    thread = threading.Thread(target=run_async_task)
    thread.daemon = True
    thread.start()
    
    # 重定向到研究状态页面
    return redirect(url_for('research_status', task_id=task_id))

@app.route('/status/<task_id>')
def research_status(task_id):
    """显示研究任务的状态页面"""
    task_info = research_tasks.get(task_id, {})
    return render_template('status.html', task_id=task_id, task_info=task_info)

@app.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """API端点，返回任务状态的JSON数据"""
    # 先从全局字典获取
    task_info = research_tasks.get(task_id, {})
    
    # 如果没有找到，尝试从文件加载
    if not task_info:
        try:
            # 查找可能的结果目录
            for dirname in os.listdir(app.config['RESULTS_FOLDER']):
                if dirname.startswith(task_id):
                    output_dir = os.path.join(app.config['RESULTS_FOLDER'], dirname)
                    task_info_path = os.path.join(output_dir, 'task_info.json')
                    if os.path.exists(task_info_path):
                        with open(task_info_path, 'r', encoding='utf-8') as f:
                            task_info = json.load(f)
                            # 将任务信息加入内存中
                            research_tasks[task_id] = task_info
                            break
        except Exception as e:
            print(f"读取任务信息文件失败: {e}")
            pass
    
    # 如果仍未找到，返回空状态
    if not task_info:
        print(f"警告: 未找到任务 {task_id} 的状态信息")
        return jsonify({"status": "unknown", "error": "找不到任务信息"})
    
    print(f"返回任务 {task_id} 的状态: {task_info.get('status')}, 进度: {task_info.get('progress')}%")
    return jsonify(task_info)

@app.route('/result/<task_id>')
def show_result(task_id):
    """显示研究结果页面"""
    task_info = research_tasks.get(task_id, {})
    
    if not task_info or task_info.get('status') != 'completed':
        return redirect(url_for('research_status', task_id=task_id))
    
    # 读取研究结果
    output_dir = task_info.get('output_dir', '')
    result_path = os.path.join(output_dir, 'research_content.json')
    
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
    except Exception as e:
        result = {"error": f"读取结果失败: {str(e)}"}
    
    # 获取HTML报告路径
    html_report_path = os.path.join(output_dir, 'research_report.html')
    html_report_url = None
    if os.path.exists(html_report_path):
        html_report_url = f"/download/{task_id}/research_report.html"
    
    # 获取Markdown报告路径
    md_report_path = os.path.join(output_dir, 'research_report.md')
    md_report_url = None
    if os.path.exists(md_report_path):
        md_report_url = f"/download/{task_id}/research_report.md"
    
    return render_template('result.html', 
                         task_id=task_id, 
                         task_info=task_info,
                         result=result,
                         html_report_url=html_report_url,
                         md_report_url=md_report_url)

@app.route('/download/<task_id>/<filename>')
def download_file(task_id, filename):
    """下载文件"""
    task_info = research_tasks.get(task_id, {})
    if not task_info:
        return "任务不存在", 404
    
    output_dir = task_info.get('output_dir', '')
    return send_from_directory(output_dir, filename)

async def start_research_task(task_id, query, model, output_dir, max_depth=3):
    """在后台启动研究任务"""
    # 获取已初始化的任务信息
    task_info = research_tasks.get(task_id, {})
    if not task_info:
        print(f"错误: 任务 {task_id} 不存在")
        return
    
    print(f"开始后台研究任务: {task_id}")
    print(f"研究深度: {max_depth}")
    
    # 更新任务状态
    task_info['status'] = 'running'
    task_info['message'] = '正在准备研究环境...'
    task_info['progress'] = 5
    task_info['detail'] = {'stage': 'preparation'}
    
    # 保存任务状态
    with open(os.path.join(output_dir, 'task_info.json'), 'w', encoding='utf-8') as f:
        json.dump(task_info, f, ensure_ascii=False, indent=2)
    
    try:
        # 初始化知识库
        kb_path = os.path.join(output_dir, "knowledge_base.json")
        kb = KnowledgeBase(storage_path=kb_path)
        
        # 创建研究Agent并设置进度回调
        agent = DeepResearchAgent(model=model, max_recursion_depth=max_depth)
        agent.knowledge_base = kb.entries
        
        # 设置进度回调函数
        def update_progress(progress_data):
            nonlocal task_info
            # 从进度数据对象中提取信息
            task_info['progress'] = progress_data.get('progress', 0)
            task_info['message'] = progress_data.get('message', '')
            if 'detail' in progress_data:
                task_info['detail'] = progress_data.get('detail', {})
            
            # 保存任务状态
            with open(os.path.join(output_dir, 'task_info.json'), 'w', encoding='utf-8') as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            print(f"任务 {task_id} 进度更新: {task_info['progress']}%, {task_info['message']}")
        
        agent.set_progress_callback(update_progress)
        
        # 执行研究
        results = await agent.research(query)
        
        # 保存原始研究结果
        with open(os.path.join(output_dir, "raw_results.json"), "w", encoding="utf-8") as f:
            json.dump(results["raw_results"], f, ensure_ascii=False, indent=2)
        
        # 使用输出整理器格式化结果
        organizer = OutputOrganizer(model=model)
        
        # 保存不同格式的结果
        # Markdown
        markdown = organizer.format_as_markdown(results["content"])
        with open(os.path.join(output_dir, "research_report.md"), "w", encoding="utf-8") as f:
            f.write(markdown)
        
        # HTML
        html = organizer.format_as_html(results["content"])
        with open(os.path.join(output_dir, "research_report.html"), "w", encoding="utf-8") as f:
            f.write(html)
        
        # JSON
        with open(os.path.join(output_dir, "research_content.json"), "w", encoding="utf-8") as f:
            json.dump(results["content"], f, ensure_ascii=False, indent=2)
        
        # 更新任务状态为完成
        task_info['status'] = 'completed'
        task_info['progress'] = 100
        task_info['message'] = '研究完成'
        task_info['detail'] = {'stage': 'completed'}
        task_info['completion_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存最终任务状态
        with open(os.path.join(output_dir, 'task_info.json'), 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
        
        print(f"研究任务 {task_id} 已完成")
        
    except Exception as e:
        # 更新任务状态为失败
        task_info['status'] = 'failed'
        task_info['message'] = f'研究失败: {str(e)}'
        task_info['detail'] = {'stage': 'error', 'error': str(e)}
        
        # 保存错误信息
        error_file = os.path.join(output_dir, "error_log.txt")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"研究问题: {query}\n")
            f.write(f"错误信息: {str(e)}\n")
            f.write(f"详细堆栈:\n{traceback.format_exc()}")
        
        # 保存任务状态
        with open(os.path.join(output_dir, 'task_info.json'), 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
        
        print(f"研究任务 {task_id} 失败: {e}")
        traceback.print_exc()

def run_app(host='0.0.0.0', port=5000, debug=True):
    """运行Flask应用"""
    # 禁用重载器以避免Windows上的套接字问题
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    run_app() 