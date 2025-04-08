import json
from typing import List, Optional
import asyncio
import re # Import regex module


from research_assistant.config import settings
from research_assistant.helpers import logger
from research_assistant.schemas import PaperMetadata

# Import the GPT function from the service (which can handle DeepSeek)
try:
    # Assuming gptservice.GPT can handle different models based on selected_model
    from LLMapi_service.gptservice import GPT 
except ImportError:
    logger.error("LLMapi_service.gptservice could not be imported!")
    # Mock function if import fails
    async def GPT(input, selected_model): 
        return {"role": "assistant", "content": "[]"} # Return empty JSON list on error

# No global client needed here, gptservice likely handles it internally

class LLMInterface:

    @staticmethod
    async def generate_clarification_prompt(topic: str, selected_conferences: Optional[List[str]]) -> str:
        """
        Uses the configured LLM (via gptservice, expected to be Deepseek) to analyze the topic 
        and generate clarification questions or a confirmation message.
        """
        conference_info = "any relevant conferences"
        if selected_conferences:
            conference_info = f"the following conferences: {', '.join(selected_conferences)}"
        elif settings.top_conferences:
            conference_info = f"top conferences like {', '.join(settings.top_conferences.keys())}"

        # Prompt for Deepseek via gptservice
        prompt = f"""Analyze the following research topic description provided by a user. Your goal is to determine if the topic is clear enough to generate effective search queries for academic paper databases (like Semantic Scholar, arXiv).

        User's Topic: "{topic}"
        User's Conference Preference: {conference_info}
        Search Years Range: {settings.search_years_range}

        Based on this, do ONE of the following:
        1. If the topic is very clear and specific, respond with a short confirmation message starting with 'CONFIRM:'. Example: 'CONFIRM: The topic is clear. Proceeding to generate search queries.'
        2. If the topic is ambiguous, too broad, or lacks key details for searching, formulate 1-3 specific questions for the user to clarify their need. Start your response with 'QUESTIONS:'. Ask about things like key methodologies, specific sub-areas, datasets, or desired outcomes. Example: 'QUESTIONS: 1. Could you specify the primary deep learning architecture you are focusing on? 2. Are you interested in theoretical analysis or empirical results? 3. Are there any specific datasets you want to see papers evaluated on?'

        Respond ONLY with the confirmation message (starting with 'CONFIRM:') OR the questions (starting with 'QUESTIONS:'). Do not add any other explanation."""

        logger.info(f"Generating clarification prompt for topic: {topic[:100]}... using model {settings.llm_model_name}")
        
        # Format input for the GPT service (usually list of messages)
        llm_input = [{"role": "user", "content": prompt}]

        try:
            # Call the GPT service, specifying the model from settings
            llm_response_dict = await GPT(input=llm_input, selected_model=settings.llm_model_name)
            
            clarification = llm_response_dict.get("content", "").strip()
            logger.info(f"LLM ({settings.llm_model_name}) clarification response: {clarification[:200]}...")

            if not clarification.startswith(("CONFIRM:", "QUESTIONS:")):
                 logger.warning(f"LLM ({settings.llm_model_name}) response did not follow expected format. Defaulting to CONFIRM.")
                 return f"CONFIRM: Proceeding with the topic as provided: '{topic[:100]}...'" # Fallback
            return clarification
        except Exception as e:
            logger.error(f"Error calling LLM ({settings.llm_model_name}) for clarification: {e}", exc_info=True)
            # Fallback: Assume confirmation if LLM fails
            return f"CONFIRM: Proceeding with the topic as provided due to an internal error: '{topic[:100]}...'"


    @staticmethod
    async def generate_final_queries_with_confirmation(topic: str, user_confirmation: str, selected_conferences: Optional[List[str]]) -> List[str]:
        """
        Uses the configured LLM (via gptservice, expected to be Deepseek) to generate final search queries 
        based on the original topic and user's confirmation/clarification.
        Raises ValueError if the response cannot be parsed into a list of strings.
        """
        conference_list_str = "any relevant"
        if selected_conferences:
            conference_list_str = ", ".join(selected_conferences)
        elif settings.top_conferences:
            conference_list_str = ", ".join(settings.top_conferences.keys())

        prompt = f"""Based on the user's initial research topic and their subsequent confirmation/clarification, generate a JSON list of {settings.max_queries_per_task} specific and diverse search query strings suitable for academic paper databases (like Semantic Scholar, arXiv). Focus on keywords, phrases, and potential synonyms related to the core concepts. Ensure the queries cover different facets if the topic is broad. Consider the specified conference preferences and year range.

        Initial Topic: "{topic}"
        User Confirmation/Clarification: "{user_confirmation}"
        Conference Preference: {conference_list_str}
        Search Years Range: {settings.search_years_range}
        Maximum Queries: {settings.max_queries_per_task}

        Respond ONLY with a valid JSON list of strings. Example: ["query 1", "query 2", "query 3"]"""

        logger.info(f"Generating final queries with confirmation for topic: {topic[:100]}... using model {settings.llm_model_name}")
        
        llm_input = [{"role": "user", "content": prompt}]
        response_text = ""

        try:
            llm_response_dict = await GPT(input=llm_input, selected_model=settings.llm_model_name)
            response_text = llm_response_dict.get("content", "").strip()
            logger.info(f"LLM ({settings.llm_model_name}) raw final query generation response: {response_text[:500]}...")
            
            # --- Clean the response text --- 
            # Remove markdown code block fences (```json ... ``` or ``` ... ```)
            match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response_text, re.DOTALL)
            if match:
                cleaned_response_text = match.group(1)
                logger.info("Extracted JSON content from markdown code block.")
            else:
                 # If no markdown block found, assume the response is the JSON itself (or invalid)
                cleaned_response_text = response_text
                logger.info("No markdown code block detected, attempting to parse directly.")
            # -------------------------------

            # Parse the cleaned JSON response
            queries = json.loads(cleaned_response_text)
            if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
                # Log the specific reason for the error
                error_msg = f"LLM ({settings.llm_model_name}) response parsed, but is not a valid list of strings: {cleaned_response_text}"
                logger.error(error_msg)
                # Raise ValueError instead of returning fallback
                raise ValueError(error_msg)

            logger.info(f"Successfully parsed {len(queries)} final queries.")
            return queries[:settings.max_queries_per_task]

        except json.JSONDecodeError as e:
            # Log the parsing error AND the problematic cleaned text
            error_msg = f"Failed to parse LLM ({settings.llm_model_name}) response as JSON: {e}. Cleaned response text was: {cleaned_response_text}"
            logger.error(error_msg)
            # Raise ValueError instead of returning fallback
            raise ValueError(error_msg)
        except Exception as e:
            # Catch other potential errors during LLM call or processing
            error_msg = f"Error during LLM ({settings.llm_model_name}) call or processing for final queries: {e}"
            logger.error(error_msg, exc_info=True)
            # Raise ValueError instead of returning fallback
            raise ValueError(error_msg)

    @staticmethod
    async def rate_relevance(topic: str, papers: List[PaperMetadata]) -> List[PaperMetadata]:
        """
        (Future Enhancement) Uses LLM to rate the relevance of found papers to the original topic.
        Currently, this is a placeholder.
        """
        logger.info("LLM relevance rating is not yet implemented.")
        # In the future, you would construct a prompt asking the LLM to evaluate
        # each paper's abstract against the topic and return a score or boolean.
        # For now, just return the papers as is.
        # for paper in papers:
        #     paper.relevance_score = 0.5 # Assign a default score or None
        return papers 