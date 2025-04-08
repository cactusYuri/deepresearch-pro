import hashlib
import re
import datetime
import logging
from pathlib import Path
from typing import List, Optional, Set
import json

from research_assistant.schemas import PaperMetadata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_task_id(topic: str) -> str:
    """Generates a unique task ID based on topic and timestamp."""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    topic_hash = hashlib.sha1(topic.encode()).hexdigest()[:8]
    return f"task_{timestamp}_{topic_hash}"

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid for filenames."""
    name = re.sub(r'[^\w\s-]', '', name).strip() # Keep word chars, whitespace, hyphen
    name = re.sub(r'[-\s]+', '_', name)        # Replace whitespace/hyphens with underscore
    return name[:100] # Limit length

def get_task_results_dir(base_dir: Path, task_id: str) -> Path:
    """Gets the specific directory path for a task's results."""
    path = base_dir / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_existing_paper_ids(task_dir: Path) -> Set[str]:
    """Loads unique IDs of already processed papers in a task directory."""
    existing_ids = set()
    if not task_dir.is_dir():
        return existing_ids

    for json_file in task_dir.glob("query_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                papers_data = json.load(f)
                if isinstance(papers_data, list): # Ensure it's a list of papers
                    for paper_dict in papers_data:
                        # Re-create PaperMetadata to use get_unique_id
                        # Handle potential missing keys gracefully
                        paper = PaperMetadata(
                            doi=paper_dict.get('doi'),
                            arxiv_id=paper_dict.get('arxiv_id'),
                            title=paper_dict.get('title'),
                            authors=paper_dict.get('authors', [])
                        )
                        paper_id = paper.get_unique_id()
                        if paper_id:
                            existing_ids.add(paper_id)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading or parsing {json_file}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error processing {json_file}: {e}")


    return existing_ids

def save_papers_to_json(papers: List[PaperMetadata], filepath: Path) -> None:
    """Saves a list of PaperMetadata objects to a JSON file.
    
    Handles serialization of objects that are not directly JSON serializable.
    """
    try:
        # 转换为字典并将不能序列化的类型(如HttpUrl)转换为字符串
        papers_json = [paper.dict(exclude_none=True) for paper in papers]
        
        # 确保目标目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(papers_json, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully saved {len(papers)} papers to {filepath}")
    except Exception as e:
        logger.error(f"Unexpected error saving papers to {filepath}: {e}")
        raise

def normalize_venue_name(venue: Optional[str]) -> str:
    """Converts venue name to lowercase and removes common noise."""
    if not venue:
        return ""
    venue = venue.lower()
    # Remove common prefixes/suffixes or normalize known variations if needed
    venue = venue.replace("proceedings of the", "").strip()
    venue = venue.replace("international conference on", "").strip()
    venue = venue.replace("conference on", "").strip()
    # Add more specific normalization if required based on observed API data
    return venue.strip()

def get_current_year() -> int:
    return datetime.datetime.utcnow().year 