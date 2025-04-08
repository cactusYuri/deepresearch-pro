import datetime
import json
from typing import Dict, List, Optional

from research_assistant.schemas import (
    SubmitTaskRequest, SubmitTaskResponse, TaskStatusResponse, TaskResultResponse,
    Task, task_storage, ConfirmTaskRequest # Import shared storage, Task model and new Confirm request
)
from research_assistant.helpers import generate_task_id, get_task_results_dir, logger
from research_assistant.orchestrator import run_background_task # Import the async function for background task
from research_assistant.llm_interface import LLMInterface # Import LLMInterface
from research_assistant.config import settings

class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"


async def start_new_task(
    task_id: str = "The ID of the task to confirm."
):
    """
    Submits a new task. May require confirmation based on topic clarity.
    Returns task ID and potentially clarification questions.
    """
    
    task = task_storage.get(task_id)

    # 1. Generate clarification prompt/check
    try:
        clarification_result = await LLMInterface.generate_clarification_prompt(
            task.topic, task.selected_conferences
        )
        logger.info(f"Task {task_id}: Clarification result: {clarification_result[:100]}...")

        if clarification_result.startswith("CONFIRM:"):
            task.message = "Topic confirmed clear. Generating final queries..."
            task.status = "pending" # Remains pending, will start background task
            task.clarification_prompt = clarification_result # Store confirmation message
            task_storage[task_id] = task # Update task storage
            logger.info(f"Task {task_id}: Topic confirmed clear. Proceeding to generate final queries.")

            # 2. Generate final queries immediately
            final_queries = await LLMInterface.generate_final_queries_with_confirmation(
                task.topic,
                user_confirmation=clarification_result, # Use the confirmation as input
                selected_conferences=task.selected_conferences
            )
            task.final_queries = final_queries
            task.message = f"Generated {len(final_queries)} queries. Task is queued for processing."
            task_storage[task_id] = task
            logger.info(f"Task {task_id}: Generated final queries: {final_queries}. Adding background task.")
            
            # 3. Add the processing function to background tasks
            await run_background_task(task_id)
            #background_tasks.add_task(run_background_task, task_id)
            #logger.info(f"Background task added for task {task_id}")

        elif clarification_result.startswith("QUESTIONS:"):
            task.status = "awaiting_confirmation"
            task.clarification_prompt = clarification_result # Store the questions
            task.message = "Awaiting user confirmation. Please respond to the clarification questions."
            task_storage[task_id] = task # Update task storage
            logger.info(f"Task {task_id}: Requires user confirmation. Prompt: {task.clarification_prompt}")
        
        else:
            # Should not happen based on llm_interface logic, but handle defensively
            logger.warning(f"Task {task_id}: Unexpected clarification result format. Treating as confirmation.")
            task.status = "pending" 
            task.clarification_prompt = clarification_result
            task.message = "Proceeding with original topic (unexpected LLM response format). Generating final queries..."
            task_storage[task_id] = task
            # Generate queries and start background task as if confirmed
            final_queries = await LLMInterface.generate_final_queries_with_confirmation(task.topic, "CONFIRM: Proceeding as is.", task.selected_conferences)
            task.final_queries = final_queries
            task.message = f"Generated {len(final_queries)} queries (unexpected LLM format). Task queued."
            task_storage[task_id] = task
            
            await run_background_task(task_id)
            #background_tasks.add_task(run_background_task, task_id)
            #logger.info(f"Background task added for task {task_id} despite unexpected format.")

    except Exception as e:
        logger.error(f"Task {task_id}: Error during initial LLM processing: {e}", exc_info=True)
        task.status = "failed"
        task.message = f"Failed during initial processing: {e}"
        task_storage[task_id] = task
        # Do not proceed, return error state in response
        # Status code 202 might still be okay, but the response body reflects the failure

    return SubmitTaskResponse(
        task_id=task_id,
        message=task.message,
        clarification_prompt=task.clarification_prompt if task.status == "awaiting_confirmation" else None,
        status=task.status
    )

async def continue_task(
    task_id: str = "The ID of the task to confirm."
):
    """
    Submits the user's confirmation/response to clarification questions.
    If successful, generates final queries and queues the task for background processing.
    """
    task = task_storage.get(task_id)

    try:
        # 1. Generate final queries using the confirmation
        final_queries = await LLMInterface.generate_final_queries_with_confirmation(
            task.topic,
            task.user_confirmation_response,
            task.selected_conferences
        )
        task.final_queries = final_queries
        task.message = f"Generated {len(final_queries)} queries. Task is queued for processing."
        task_storage[task_id] = task
        logger.info(f"Task {task_id}: Generated final queries after confirmation: {final_queries}. Adding background task.")

        # 2. Add the processing function to background tasks
        await run_background_task(task_id)
        #background_tasks.add_task(run_background_task, task_id)
        #logger.info(f"Background task added for task {task_id} after confirmation.")
        
        # Return the updated task status
        return task # TaskStatusResponse is compatible with Task model

    except Exception as e:
        logger.error(f"Task {task_id}: Error during query generation after confirmation: {e}", exc_info=True)
        task.status = "failed"
        task.message = f"Failed during query generation after confirmation: {e}"
        task_storage[task_id] = task
        # Raise HTTPException to indicate failure during this step
        raise HTTPException(status_code=500, detail="Failed to generate search queries after confirmation.")

async def get_task_status(
    task_id: str = "The ID of the task to check."
):
    """
    Retrieves the current status of a previously submitted task.
    """
    logger.info(f"Checking status for task {task_id}")
    task = task_storage.get(task_id)
    if not task:
        logger.warning(f"Task {task_id} not found in task storage")
        raise HTTPException(status_code=404, detail="Task not found")
    
    logger.info(f"Task {task_id} status: {task.status}, message: {task.message}")
    return task

def get_task_results(
    task_id: str = "The ID of the task to retrieve results for.",
    include_papers: bool =True #= Query(True, description="Whether to include the full paper list in the response.")
):
    """
    Retrieves the results of a completed task.
    By default, includes the list of papers found. Set include_papers=false for metadata only.
    """
    logger.info(f"Retrieving results for task {task_id}, include_papers={include_papers}")
    task_info = task_storage.get(task_id)
    if not task_info:
        logger.warning(f"Task {task_id} not found in task storage")
        raise HTTPException(status_code=404, detail="Task not found")

    if task_info.status not in ["completed", "failed"]:
        logger.info(f"Task {task_id} is not completed yet, status: {task_info.status}")
        # Return current status without results if not finished
        # Use TaskResultResponse but set results to None
        return TaskResultResponse(**task_info.dict(), results=None)


    results_data: Optional[Dict[str, List[Dict]]] = None
    if include_papers and task_info.status == "completed" and task_info.results_path:
        task_dir = get_task_results_dir(settings.results_base_dir, task_id) # Use helper to ensure consistency
        logger.info(f"Loading result files from directory: {task_dir}")
        results_data = {}
        try:
            result_files = list(task_dir.glob("query_*.json"))
            logger.info(f"Found {len(result_files)} result files for task {task_id}")
            
            if not result_files:
                logger.warning(f"No result files found for task {task_id} in directory {task_dir}")
            
            for json_file in result_files:
                query_key = json_file.stem.replace("query_", "") # Get the sanitized query part
                with open(json_file, 'r', encoding='utf-8') as f:
                    logger.debug(f"Reading result file: {json_file}")
                    papers = json.load(f)
                    # Use the sanitized query part as the key in the response
                    results_data[query_key] = papers
                    logger.info(f"Loaded {len(papers)} papers from query '{query_key}'")
                    
        except Exception as e:
            logger.error(f"Error reading result files for task {task_id}: {e}")
            # Return task info but indicate results couldn't be loaded
            task_info.message = f"{task_info.message}. Error loading result files."
            # Fall through to return task_info without results_data
    else:
        if not include_papers:
            logger.info(f"Skipping paper data for task {task_id} as requested")
        elif task_info.status != "completed":
            logger.info(f"No results available for task {task_id} with status {task_info.status}")
        elif not task_info.results_path:
            logger.warning(f"No results path found for completed task {task_id}")

    # Create the final response object
    response = TaskResultResponse(**task_info.dict(), results=results_data)
    
    # 记录返回的结果规模
    if results_data:
        total_papers = sum(len(papers) for papers in results_data.values())
        logger.info(f"Returning {total_papers} papers across {len(results_data)} queries for task {task_id}")
    return response 