"""
深度研究 Agent 包
"""

from .agent import DeepResearchAgent, DeepResearchNode
from .tools import WebSearchTool, KnowledgeBaseSearchTool, KnowledgeBaseStorageTool, get_default_tools
from .decomposer import ProblemDecomposer, TaskDependencyResolver
from .knowledge_base import KnowledgeBase
from .output_organizer import OutputOrganizer
from .main import run_research

# 设置默认模型
DEFAULT_MODEL = "deepseek-chat"

__version__ = "0.1.0"
__all__ = [
    "DeepResearchAgent",
    "DeepResearchNode",
    "WebSearchTool",
    "KnowledgeBaseSearchTool",
    "KnowledgeBaseStorageTool",
    "get_default_tools",
    "ProblemDecomposer",
    "TaskDependencyResolver",
    "KnowledgeBase",
    "OutputOrganizer",
    "run_research",
    "DEFAULT_MODEL"
] 