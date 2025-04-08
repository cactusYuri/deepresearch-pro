import asyncio
from pathlib import Path
from typing import List, Optional, Dict
import time
import traceback

from research_assistant.schemas import Task, PaperMetadata, task_storage # Import shared task storage
from research_assistant.config import settings
# LLMInterface might not be needed here anymore unless for relevance rating
# from app.core.llm_interface import LLMInterface 
from research_assistant.search_engines import run_searches
from research_assistant.data_processor import DataProcessor
from research_assistant.helpers import (
    logger,
    get_task_results_dir,
    load_existing_paper_ids,
    save_papers_to_json,
    sanitize_filename
)

class TaskOrchestrator:

    def __init__(self):
        self.data_processor = DataProcessor(settings.top_conferences)
        logger.info("TaskOrchestrator initialized with DataProcessor")

    async def process_task(self, task: Task):
        """The main background task processing logic. Uses pre-generated queries from the task object."""
        start_time = time.time()
        task.status = "processing"
        # Update message to reflect starting the search with existing queries
        task.message = "Processing task: Starting paper search..."
        logger.info(f"Starting processing for task {task.task_id}. Using pre-generated queries.")

        task_dir = get_task_results_dir(settings.results_base_dir, task.task_id)
        # Ensure results_path is set if not already (though it should be by API)
        if not task.results_path:
            task.results_path = str(task_dir)
            logger.warning(f"Task {task.task_id}: results_path was not set, setting it now to {task_dir}")
        else:
             logger.info(f"Using results directory: {task.results_path}") # Log the path being used

        try:
            # 1. Get Final Search Queries from Task Object
            search_queries = task.final_queries
            if not search_queries:
                # This case should ideally not happen if the background task is triggered correctly
                logger.error(f"Task {task.task_id}: No final_queries found in the task object. Cannot proceed with search.")
                raise ValueError("No search queries available for this task.")
            
            task.message = f"Using {len(search_queries)} pre-generated queries. Starting search..."
            logger.info(f"Task {task.task_id}: Using {len(search_queries)} final queries: {search_queries}")

            # 2. Run Searches Concurrently
            # raw_results_map is Dict[str, List[Dict[str, Any]]] -> {"query1": [paper_dict1, ...], "query2": [...]}
            logger.info(f"Task {task.task_id}: Running searches for {len(search_queries)} queries")
            raw_results_map = await run_searches(search_queries)
            task.message = "Search complete. Processing results..."
            
            # 记录每个查询的原始结果数量
            total_raw_papers = sum(len(results) for results in raw_results_map.values())
            logger.info(f"Task {task.task_id}: Search completed. Found {total_raw_papers} raw papers across {len(search_queries)} queries")

            # 3. Process and Store Results for each query
            total_new_papers = 0
            # processed_results_map is no longer strictly needed here unless for immediate in-memory use
            # processed_results_map: Dict[str, List[PaperMetadata]] = {} 

            for query_index, (query, raw_results) in enumerate(raw_results_map.items()):
                query_log_str = f'{query[:50]}...' if len(query) > 50 else query # Truncate long queries for logs
                logger.info(f"Task {task.task_id}: Processing query {query_index+1}/{len(raw_results_map)}: '{query_log_str}'")
                
                if not raw_results:
                    logger.info(f"Task {task.task_id}: No results found for query '{query_log_str}'.")
                    # processed_results_map[query] = [] # No need to store empty list if not using map
                    continue

                task.message = f"Processing results for query: '{query_log_str}'"
                logger.info(f"Task {task.task_id}: Processing {len(raw_results)} results for query '{query_log_str}'.")

                # Load existing IDs *before* processing this batch to ensure task-wide deduplication
                existing_ids = load_existing_paper_ids(Path(task.results_path)) # Ensure path is Path object
                logger.info(f"Task {task.task_id}: Found {len(existing_ids)} existing paper IDs.")

                # Process: Parse, Deduplicate (against existing and current batch), Mark Top Conf
                new_papers = self.data_processor.process_raw_results(raw_results, existing_ids)

                if new_papers:
                    total_new_papers += len(new_papers)
                    # Optional: Relevance Rating (Future)
                    # You might need LLMInterface back if you uncomment this
                    # new_papers = await LLMInterface.rate_relevance(task.topic, new_papers)

                    # Store results for this query
                    # Sanitize the original query for use in the filename
                    query_filename = f"query_{sanitize_filename(query)}.json"
                    query_filepath = Path(task.results_path) / query_filename # Use Path object
                    logger.info(f"Task {task.task_id}: Saving {len(new_papers)} papers to {query_filepath}")
                    save_papers_to_json(new_papers, query_filepath)
                    # processed_results_map[query] = new_papers # Not storing in map anymore
                else:
                    logger.warning(f"Task {task.task_id}: No new papers found after processing for query '{query_log_str}'")
                    # processed_results_map[query] = [] # Not storing in map


            task.status = "completed"
            elapsed_time = time.time() - start_time
            # Use the count of original queries from the task object for the message
            task.message = f"Task completed in {elapsed_time:.1f} seconds. Found {total_new_papers} new papers across {len(search_queries)} queries."
            logger.info(f"Task {task.task_id}: {task.message}")
            # Removing task.results assignment to avoid storing large data in memory
            # task.results = processed_results_map 

        except Exception as e:
            task.status = "failed"
            error_trace = traceback.format_exc()
            task.message = f"Task failed: {str(e)}"
            logger.error(f"Task {task.task_id} failed during processing. Error: {str(e)}")
            logger.error(f"Traceback: {error_trace}")

        # Update the global task storage (ensure thread-safety if not using memory dict)
        task_storage[task.task_id] = task
        logger.info(f"Task {task.task_id} completed with status: {task.status}")

# Instantiate the orchestrator
orchestrator = TaskOrchestrator()

# Define the async function that FastAPI BackgroundTasks will call
async def run_background_task(task_id: str):
    logger.info(f"Starting background task for task_id: {task_id}")
    task = task_storage.get(task_id)
    if task:
        # Check if the task actually has queries before processing
        if task.status == "pending" and task.final_queries:
            await orchestrator.process_task(task)
        elif not task.final_queries:
             logger.error(f"Background task for {task_id} started, but final_queries are missing. Setting status to failed.")
             task.status = "failed"
             task.message = "Task failed: Search queries were not generated before processing started."
             task_storage[task_id] = task # Update storage
        else:
            logger.warning(f"Background task for {task_id} started, but status is {task.status}. Skipping process_task.")
    else:
        logger.error(f"Background task started for non-existent task ID: {task_id}") 