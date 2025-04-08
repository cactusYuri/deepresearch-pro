from typing import List, Dict, Any, Optional, Set

from research_assistant.schemas import PaperMetadata
from research_assistant.config import settings
from research_assistant.helpers import normalize_venue_name, logger

class DataProcessor:

    def __init__(self, top_conference_mapping: Dict[str, List[str]]):
        """
        Initializes the processor with the mapping of top conference names to their aliases.
        Keys are the canonical names, values are lists of lowercase aliases.
        """
        self.top_conf_mapping = top_conference_mapping
        # Pre-compile a set of all lowercase aliases for faster lookups
        self.all_top_conf_aliases = set()
        for aliases in top_conference_mapping.values():
            self.all_top_conf_aliases.update(aliases)
        
        logger.info(f"DataProcessor initialized with {len(top_conference_mapping)} top conferences")
        logger.debug(f"Top conference aliases: {self.all_top_conf_aliases}")

    def _parse_semantic_scholar_paper(self, paper_data: Dict[str, Any]) -> Optional[PaperMetadata]:
        """Parses a single paper dictionary from Semantic Scholar API response."""
        try:
            # Extract basic info
            title = paper_data.get('title')
            authors = [author.get('name') for author in paper_data.get('authors', []) if author.get('name')]
            abstract = paper_data.get('abstract')
            url = paper_data.get('url')
            venue = paper_data.get('venue')
            year = paper_data.get('year')
            doi = paper_data.get('doi')
            paper_id = paper_data.get('paperId', 'Unknown ID')
            
            logger.debug(f"Parsing Semantic Scholar paper: ID={paper_id}, Title={title}, Venue={venue}")

            # Extract arXiv ID from externalIds if present
            arxiv_id = None
            external_ids = paper_data.get('externalIds')
            if external_ids and isinstance(external_ids, dict):
                 arxiv_id = external_ids.get('ArXiv') # Key is 'ArXiv' case-sensitive
                 logger.debug(f"Found arXiv ID: {arxiv_id} for paper {paper_id}")

            # Basic validation: require at least title and authors
            if not title or not authors:
                 logger.warning(f"Skipping paper due to missing title or authors: {paper_id}")
                 return None

            # Construct source string
            source = f"{venue} {year}" if venue and year else venue or (f"arXiv {year}" if arxiv_id and year else "Unknown Source")

            # Check if it's a top conference
            is_top = self._is_top_conference(venue)
            if is_top:
                logger.info(f"Found top conference paper: {title} ({venue})")

            return PaperMetadata(
                title=title,
                authors=authors,
                abstract=abstract,
                url=url,
                source=source,
                year=year,
                doi=doi,
                arxiv_id=arxiv_id,
                is_top_conference=is_top
            )
        except Exception as e:
            logger.error(f"Error parsing paper data: {paper_data.get('paperId', 'Unknown ID')}. Error: {e}")
            return None

    def _parse_arxiv_paper(self, paper_data: Dict[str, Any]) -> Optional[PaperMetadata]:
        """Parses a single paper dictionary from our custom arXiv result format."""
        try:
            arxiv_id = paper_data.get('externalIds', {}).get('ArXiv', 'Unknown ID')
            title = paper_data.get('title')
            logger.debug(f"Parsing arXiv paper: ID={arxiv_id}, Title={title}")
            
            # Data structure is already quite close to PaperMetadata
            paper = PaperMetadata(
                title=paper_data.get('title'),
                authors=[author.get('name') for author in paper_data.get('authors', [])],
                abstract=paper_data.get('abstract'),
                url=paper_data.get('url'), # This is the arxiv abstract page URL
                source=paper_data.get('venue', 'arXiv'), # Should be 'arXiv'
                year=paper_data.get('year'),
                doi=paper_data.get('doi'),
                arxiv_id=paper_data.get('externalIds', {}).get('ArXiv'),
                is_top_conference=False # arXiv itself is not typically listed as a 'top conference' venue
            )

            # Basic validation
            if not paper.title or not paper.authors:
                logger.warning(f"Skipping arXiv paper due to missing title or authors: {arxiv_id}")
                return None

            return paper

        except Exception as e:
            logger.error(f"Error parsing arXiv paper data: {paper_data.get('externalIds', {}).get('ArXiv', 'Unknown ID')}. Error: {e}")
            return None

    def _is_top_conference(self, venue_name: Optional[str]) -> bool:
        """Checks if the venue name corresponds to a configured top conference."""
        if not venue_name:
            return False

        normalized_venue = normalize_venue_name(venue_name)
        logger.debug(f"Checking if '{normalized_venue}' is a top conference (original: '{venue_name}')")

        # Simple check: is the normalized venue *exactly* one of the aliases?
        if normalized_venue in self.all_top_conf_aliases:
            logger.debug(f"Found exact match for venue '{normalized_venue}' in top conference aliases")
            return True

        # Check against the alias lists directly for better control
        for canonical_name, aliases in self.top_conf_mapping.items():
            if normalized_venue in aliases:
                 logger.debug(f"Venue '{normalized_venue}' matched canonical name '{canonical_name}'")
                 return True

        return False

    def process_raw_results(self, raw_results: List[Dict[str, Any]], existing_ids: Set[str]) -> List[PaperMetadata]:
        """
        Parses raw results from search APIs, performs deduplication, and marks top conferences.
        """
        logger.info(f"Processing {len(raw_results)} raw results. {len(existing_ids)} existing paper IDs for deduplication.")
        
        if not raw_results:
            logger.warning("Empty raw results provided to process_raw_results")
            return []
            
        processed_papers: List[PaperMetadata] = []
        added_ids = set() # Track IDs added in this batch
        skipped_count = 0
        no_id_count = 0

        for i, paper_data in enumerate(raw_results):
            if i < 3:  # 只记录前几条数据的详情
                logger.debug(f"Raw paper data {i+1}: {paper_data}")
                
            paper: Optional[PaperMetadata] = None
            # Determine the source (crude check based on expected keys)
            if 'externalIds' in paper_data and 'ArXiv' in paper_data['externalIds'] and paper_data.get('venue', '').lower() == 'arxiv':
                 # Likely our parsed arXiv result
                 paper = self._parse_arxiv_paper(paper_data)
            elif 'paperId' in paper_data and not paper_data.get('paperId','').startswith('arxiv:'):
                 # Likely Semantic Scholar result
                 paper = self._parse_semantic_scholar_paper(paper_data)
            else:
                 # Attempt generic parsing or log an unknown format
                 logger.warning(f"Unknown paper data format encountered: {paper_data.get('paperId', 'No ID')}")
                 continue # Skip this entry


            if paper:
                paper_id = paper.get_unique_id()
                # Deduplicate against existing papers in the task AND papers added in this batch
                if paper_id and paper_id not in existing_ids and paper_id not in added_ids:
                    processed_papers.append(paper)
                    added_ids.add(paper_id)
                    logger.debug(f"Added paper: {paper.title} with ID {paper_id}")
                elif not paper_id:
                     logger.warning(f"Paper '{paper.title}' could not generate a unique ID for deduplication.")
                     # Decide whether to add papers without reliable IDs (might lead to duplicates)
                     # For now, let's add them but log it.
                     processed_papers.append(paper)
                     no_id_count += 1
                else:
                    skipped_count += 1
                    logger.debug(f"Skipping duplicate paper: {paper_id}")


        logger.info(f"Processed {len(raw_results)} raw results, yielding {len(processed_papers)} new unique papers. Skipped {skipped_count} duplicates. {no_id_count} papers had no unique ID.")
        return processed_papers 