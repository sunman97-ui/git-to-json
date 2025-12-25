import logging
import asyncio
import pyperclip
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from typing import List, Optional

# Internal Imports
from src.core import fetch_repo_data
from src.utils import count_tokens, save_data_to_file
from src.config import load_settings
from src.providers import get_provider
from src.schemas import (
    PromptTemplate,
    CommitData,
)

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
        return _build_prompt_from_data(self.console, template, data)

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
        return asyncio.run(self._stream_task(provider_name, prompt_text))

    def save_prompt_to_file(self, prompt_text: str, filepath: str) -> bool:
        """Workflow: Save generated prompt to text file."""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(prompt_text)
            return True
        except Exception as e:
            logger.error(f"Failed to save prompt: {e}")
            return False

    def copy_to_clipboard(self, text: str) -> bool:
        """Workflow: Copy text to system clipboard."""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error(f"Clipboard error: {e}")
            return False

    async def _stream_task(self, provider_name: str, user_prompt: str):
        """Internal async handler for streaming."""
        try:
            provider = get_provider(provider_name, self.settings)
            self.console.print(
                f"\n[bold green]Connecting to {provider_name.upper()}...[/]"
            )

            full_response = ""
            async with provider:
                with Live(
                    Markdown(""), refresh_per_second=12, console=self.console
                ) as live:
                    async for chunk in provider.stream_response(user_prompt):
                        full_response += chunk
                        live.update(Markdown(full_response, style="blue"))
            return full_response
        except Exception as e:
            self.console.print(f"\n[bold red]AI Execution Error:[/]\n{e}")
            logger.error(f"Stream error: {e}", exc_info=True)
            return None


# --- Helper Functions (Internal) ---


def _build_prompt_from_data(
    console: Console, template: PromptTemplate, data: List[CommitData]
) -> str:
    if not data:
        return ""

    if len(data) == 1:
        raw_diff = data[0].diff
    else:
        # Optimized concatenation
        combined_diffs = [
            f"--- Diff for {c.short_hash}: {c.message.splitlines()[0]} ---\n{c.diff}"
            for c in data
        ]
        raw_diff = "\n\n".join(combined_diffs)

    final_user_prompt = template.prompts.user.replace("{DIFF_CONTENT}", raw_diff)

    # RE-ADDED HEADERS to match test expectations and improve LLM clarity
    full_payload = (
        f"--- SYSTEM PROMPT ---\n{template.prompts.system}\n\n"
        f"--- USER PROMPT ---\n{final_user_prompt}"
    )

    token_count = count_tokens(full_payload)
    console.print(f"   📊  Payload size: ~{token_count} tokens", style="dim")

    return full_payload
