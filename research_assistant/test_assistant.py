"""
测试研究报告内容生成
"""

import os
import json
import asyncio
import sys
import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from research_assistant.helpers import generate_task_id, get_task_results_dir, logger
from research_assistant.tasks import start_new_task, get_task_results
from research_assistant.schemas import (
    SubmitTaskRequest, SubmitTaskResponse, TaskStatusResponse, TaskResultResponse,
    Task, task_storage, ConfirmTaskRequest # Import shared storage, Task model and new Confirm request
)

async def test_task():
    topic="AI agents using LLMs for solving math problems"
    task_id = generate_task_id(topic)
        
    # Create initial task object (status will be updated)
    task = Task(
        task_id=task_id,
        status="pending", # Start as pending, will update based on LLM clarification
        message="Task received, generating clarification prompt...",
        created_at=datetime.datetime.utcnow(),
        topic=topic,
        selected_conferences=[]
    )

    task_storage[task_id] = task
    rep = await start_new_task(task_id)
    print('----------------------start task --------------------------')
    print(rep)
    rep = get_task_results(task_id)
    print('---------------------- task result --------------------------')
    print(rep)

if __name__ == "__main__":
    asyncio.run(test_task())