import yaml
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_FILE_PATH = Path(__file__).parent.parent / "config.yaml"

class AppConfig:
    def __init__(self, config_path: Path = CONFIG_FILE_PATH):
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config_data = yaml.safe_load(f)

    @property
    def semantic_scholar_api_key(self) -> Optional[str]:
        return self.config_data.get('semantic_scholar_api_key')

    @property
    def semantic_scholar_api_url(self) -> str:
        return self.config_data.get('semantic_scholar_api_url', "https://api.semanticscholar.org/graph/v1")

    @property
    def request_timeout(self) -> int:
        return self.config_data.get('request_timeout', 30)

    @property
    def papers_per_query(self) -> int:
        return self.config_data.get('papers_per_query', 20)

    @property
    def max_queries_per_task(self) -> int:
        return self.config_data.get('max_queries_per_task', 5)

    @property
    def arxiv_max_results(self) -> int:
        return self.config_data.get('arxiv_max_results', 20)

    @property
    def search_years_range(self) -> int:
        return self.config_data.get('search_years_range', 3)

    @property
    def top_conferences(self) -> Dict[str, List[str]]:
        # 返回小写化的别名列表，方便匹配
        conf_dict = self.config_data.get('top_conferences', {})
        return {name: [alias.lower() for alias in aliases] for name, aliases in conf_dict.items()}

    @property
    def results_base_dir(self) -> Path:
        return Path(self.config_data.get('results_base_dir', 'results'))

    @property
    def llm_model_name(self) -> str:
        return self.config_data.get('llm_model_name', 'default_llm') # 提供默认值

    @property
    def llm_prompt_template(self) -> str:
        return self.config_data.get('llm_prompt_template', "Generate search queries for: {topic}")

# 创建一个全局可访问的配置实例
settings = AppConfig()

# 确保结果目录存在
settings.results_base_dir.mkdir(parents=True, exist_ok=True) 