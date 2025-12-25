import logging
import asyncio
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from typing import List
from src.core import fetch_repo_data
from src.utils import count_tokens
from src.config import load_settings
from src.providers import get_provider
from src.schemas import PromptTemplate, CommitData

logger = logging.getLogger(__name__)
console = Console()

class WorkflowExecutor:
    def __init__(self, console: Console, logger: logging.Logger):
        self.console = console
        self.logger = logger

    def execute_with_boundary(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute operation with comprehensive error boundary."""
        try:
            self.console.print(f"⚙️  Starting {operation_name}...", style="dim")
            result = operation_func(*args, **kwargs)
            self.console.print(f"✅ {operation_name} completed successfully", style="green")
            return result
        except ValueError as e:
            self.console.print(f"❌ Configuration Error in {operation_name}: {e}", style="bold red")
            self.logger.error(f"{operation_name} configuration error", exc_info=True)
        except FileNotFoundError as e:
            self.console.print(f"❌ File Error in {operation_name}: {e}", style="bold red")
            self.logger.error(f"{operation_name} file error", exc_info=True)
        except Exception as e:
            self.console.print(f"❌ Unexpected Error in {operation_name}: {e}", style="bold red")
            self.logger.error(f"{operation_name} unexpected error", exc_info=True)
        return None

def _build_prompt_from_data(template: PromptTemplate, data: List[CommitData]) -> str:
    """
    Builds the final prompt string from the template and a list of commit data.
    If multiple commits are provided, their diffs are concatenated.
    """
    if not data:
        return ""

    # If there's only one data item, process it directly.
    # If there are multiple, combine their diffs.
    if len(data) == 1:
        raw_diff = data[0].diff
    else:
        combined_diffs = []
        for commit in data:
            header = f"--- Diff for {commit.short_hash}: {commit.message.splitlines()[0]} ---\n"
            combined_diffs.append(header + commit.diff)
        raw_diff = "\n\n".join(combined_diffs)

    system_prompt = template.prompts.system or ""
    user_prompt_template = template.prompts.user

    # Basic hydration
    final_user_prompt = user_prompt_template.replace("{DIFF_CONTENT}", raw_diff)
    
    # Construct Full Payload for token calculation and inspection
    # This part is not sent to the LLM directly but is used for context
    full_payload = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER PROMPT ---\n{final_user_prompt}"
    
    token_count = count_tokens(full_payload)
    console.print(f"   📊  Payload size: ~{token_count} tokens", style="dim")
    
    # The actual prompt sent to the LLM might just be the user part,
    # depending on the provider's API. Here we return the full text for context.
    return full_payload

def generate_prompt_from_template(repo_path: str, template: PromptTemplate) -> str | None:
    """
    Orchestrates the flow: Data Fetch -> Prompt Build.
    Returns the final prompt string or None if no data is found.
    """
    exec_config = template.execution
    source_mode = exec_config.source
    
    filters = {"mode": source_mode}
    if source_mode == "history":
        filters["limit"] = exec_config.limit

    try:
        console.print(f"   ⚙️  Fetching data (Mode: {source_mode}, Limit: {exec_config.limit})...", style="dim")
        data = fetch_repo_data(repo_path, filters)
        
        if not data:
            console.print("   ⚠️  No data found (e.g., empty diff or no matching commits).", style="yellow")
            return None

        return _build_prompt_from_data(template, data)

    except Exception as e:
        logger.error(f"Error during template workflow for '{template.meta.name}': {e}", exc_info=True)
        console.print(f"[bold red]Error:[/]\nFailed to generate prompt: {e}")
        return None

def stream_llm_response(provider_name: str, user_prompt: str) -> str | None:
    """
    Orchestrates the async streaming flow for LLM providers.
    Uses Rich Live to render the response in real-time.
    """
    try:
        settings = load_settings()
        provider = get_provider(provider_name, settings)
        
        console.print(f"\n[bold green]Connecting to {provider_name.upper()}...[/]")
        
        async def stream_task():
            full_response = ""
            async with provider:
                with Live(Markdown(""), refresh_per_second=12, console=console) as live:
                    async for chunk in provider.stream_response(user_prompt):
                        full_response += chunk
                        live.update(Markdown(full_response, style="blue"))
            return full_response

        return asyncio.run(stream_task())

    except ValueError as e:
        console.print(f"\n[bold red]Configuration Error:[/]\n{e}")
        console.print("[yellow]Tip: Check your .env file and ensure the provider is configured.[/]")
        return None
    except Exception as e:
        logger.error(f"LLM Execution Error with {provider_name}: {e}", exc_info=True)
        console.print(f"\n[bold red]Connection Error:[/]\n{e}")
        return None