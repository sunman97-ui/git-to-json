import logging
import asyncio
from typing import List, Optional

from rich.console import Console

from src.core import fetch_repo_data
from src.utils import save_data_to_file
from src.config import load_settings
from src.schemas import PromptTemplate, CommitData
from src.services.prompt_builder import build_prompt
import src.services.output_handler as output_handler
from src.services.ai_service import stream_ai_response

logger = logging.getLogger(__name__)


class AuditEngine:
    """
    The Central Processing Unit of the application.
    Orchestrates Data Fetching -> Processing -> Output.
    """

    def __init__(self, console: Console):
        self.console = console
        self.settings = load_settings()

    def fetch_data(self, repo_path: str, filters: dict) -> List[CommitData]:
        """Wrapper to fetch data with UI feedback."""
        self.console.print("   ⚙️  Fetching repository data...", style="dim")
        data = fetch_repo_data(repo_path, filters)
        if not data:
            self.console.print("   ⚠️  No matching data found.", style="yellow")
        return data

    def build_prompt(
        self, template: PromptTemplate, data: List[CommitData]
    ) -> Optional[str]:
        """Hydrates a template with commit data."""
        # A max_tokens value could be sourced from config here in the future
        return build_prompt(self.console, template, data, max_tokens=120000)

    def execute_raw_extraction(
        self, repo_path: str, filters: dict, output_path: str
    ) -> bool:
        """Workflow: Fetch Data -> Save to JSON."""
        data = self.fetch_data(repo_path, filters)
        if not data:
            return False

        return save_data_to_file(data, output_path)

    def execute_ai_stream(self, provider_name: str, prompt_text: str):
        """Workflow: Connect to Provider -> Stream Response."""
        return asyncio.run(
            stream_ai_response(self.console, self.settings, provider_name, prompt_text)
        )

    def save_prompt_to_file(self, prompt_text: str, filepath: str) -> bool:
        """Workflow: Save generated prompt to text file."""
        return output_handler.save_prompt_to_file(prompt_text, filepath)

    def copy_to_clipboard(self, text: str) -> bool:
        """Workflow: Copy text to system clipboard."""
        return output_handler.copy_to_clipboard(text)
