import asyncio
import httpx # Use httpx for async requests
from typing import List, Dict, Any, Optional
import datetime
import json

from research_assistant.schemas import PaperMetadata
from research_assistant.config import settings
from research_assistant.helpers import logger, get_current_year

# Optional: Import arxiv library if used
try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    logger.warning("arxiv library not installed. arXiv search functionality disabled.")


class SearchClient:

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def search_semantic_scholar(self, query: str) -> List[Dict[str, Any]]:
        """Performs a search on Semantic Scholar API."""
        api_url = f"{settings.semantic_scholar_api_url}/paper/search"
        current_year = get_current_year()
        start_year = current_year - settings.search_years_range

        headers = {}
        if settings.semantic_scholar_api_key:
            headers['x-api-key'] = settings.semantic_scholar_api_key

        params = {
            'query': query,
            'limit': settings.papers_per_query,
            'year': f"{start_year}-{current_year}",
            'fields': 'title,authors.name,abstract,url,venue,year,externalIds' # 移除了doi字段
        }

        try:
            logger.info(f"Querying Semantic Scholar: Query='{query}' Years={start_year}-{current_year} Limit={settings.papers_per_query}")
            logger.debug(f"Semantic Scholar Request Headers: {headers}")
            logger.debug(f"Semantic Scholar Request Params: {params}")
            
            response = await self.client.get(api_url, params=params, headers=headers, timeout=settings.request_timeout)
            status_code = response.status_code
            
            logger.info(f"Semantic Scholar API response status code: {status_code}")
            
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            
            logger.info(f"Semantic Scholar returned {len(data.get('data', []))} results for query '{query}'.")
            
            # 记录返回结果的部分内容，帮助排查问题
            if data.get('data') and len(data.get('data')) > 0:
                sample_titles = [p.get('title') for p in data.get('data')[:3] if p.get('title')]
                logger.info(f"Sample paper titles: {sample_titles}")
            else:
                logger.warning(f"No papers found for query '{query}'")
                
            return data.get('data', []) # Return the list of paper objects
        except httpx.HTTPStatusError as e:
            logger.error(f"Semantic Scholar API error for query '{query}': {e.response.status_code} - {e.response.text}")
            try:
                error_json = e.response.json()
                logger.error(f"API error details: {json.dumps(error_json)}")
            except:
                logger.error(f"Response content: {e.response.text[:500]}")
        except httpx.RequestError as e:
            logger.error(f"Network error querying Semantic Scholar for '{query}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Semantic Scholar search for '{query}': {e}")
        
        logger.warning(f"Returning empty results for query '{query}' due to error")
        return []

    async def search_arxiv(self, query: str) -> List[Dict[str, Any]]:
        """Performs a search on arXiv API using the 'arxiv' library."""
        if not ARXIV_AVAILABLE:
            return []

        try:
            logger.info(f"Querying arXiv: Query='{query}' Limit={settings.arxiv_max_results}")
            # Use the 'arxiv' library's search functionality
            # Note: The library might be synchronous, consider running in a thread pool executor
            # for true async behavior if performance becomes an issue.
            # For simplicity here, we call it directly.

            # Define the search parameters
            search = arxiv.Search(
                query=query,
                max_results=settings.arxiv_max_results,
                sort_by=arxiv.SortCriterion.Relevance # Or SubmittedDate
            )

            results_list = []
            # The library returns a generator
            for result in search.results():
                 # Convert arxiv.Result object to a dictionary structure similar to Semantic Scholar's
                 # for easier processing later.
                 results_list.append({
                     'paperId': f"arxiv:{result.entry_id.split('/')[-1]}", # Use arXiv ID as paperId
                     'externalIds': {'ArXiv': result.entry_id.split('/')[-1]},
                     'url': result.entry_id, # Link to the abstract page
                     'title': result.title,
                     'abstract': result.summary.replace('\n', ' '), # Clean up abstract newlines
                     'authors': [{'name': author.name} for author in result.authors],
                     'venue': 'arXiv', # Explicitly set venue
                     'year': result.published.year,
                     'doi': result.doi,
                     # pdf_url: result.pdf_url # If needed later for downloading
                 })
            logger.info(f"arXiv returned {len(results_list)} results for query '{query}'.")
            if results_list:
                sample_titles = [p.get('title') for p in results_list[:3] if p.get('title')]
                logger.info(f"Sample arXiv paper titles: {sample_titles}")
            else:
                logger.warning(f"No arXiv papers found for query '{query}'")
                
            return results_list

        except Exception as e:
            logger.error(f"Unexpected error during arXiv search for '{query}': {e}")
            return []


async def run_searches(queries: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Runs searches for multiple queries concurrently."""
    results = {}
    logger.info(f"Starting searches for {len(queries)} queries: {queries}")
    
    if not queries:
        logger.warning("No search queries provided, skipping search")
        return results
        
    # Use a single async client for connection pooling
    async with httpx.AsyncClient() as client:
        search_client = SearchClient(client)
        tasks = []
        for query in queries:
            # Create tasks for Semantic Scholar search
            tasks.append(search_client.search_semantic_scholar(query))
            # Optional: Create tasks for arXiv search if enabled
            if ARXIV_AVAILABLE:
                 tasks.append(search_client.search_arxiv(query))

        # Gather results from all search tasks
        logger.info(f"Running {len(tasks)} search tasks concurrently")
        all_search_results = await asyncio.gather(*tasks)
        logger.info(f"All search tasks completed, processing results")

        # Process and organize results by original query
        # Since we might have results from multiple sources for the same query,
        # we need to correctly map them back.

        num_queries = len(queries)
        num_sources = 1 + (1 if ARXIV_AVAILABLE else 0) # Number of search engines used per query

        combined_results: Dict[str, List[Dict[str, Any]]] = {q: [] for q in queries}

        result_index = 0
        for i, query in enumerate(queries):
            # Get Semantic Scholar results for this query
            ss_results = all_search_results[result_index]
            combined_results[query].extend(ss_results)
            result_index += 1

            # Get arXiv results for this query if applicable
            if ARXIV_AVAILABLE:
                arxiv_results = all_search_results[result_index]
                combined_results[query].extend(arxiv_results)
                result_index += 1
                
        # 记录合并后的结果数量
        for query, papers in combined_results.items():
            logger.info(f"Combined results for query '{query}': {len(papers)} papers")
            
    return combined_results 