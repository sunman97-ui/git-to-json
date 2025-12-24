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

def _build_prompt_from_data(template: PromptTemplate, data: List[CommitData]) -> str:
    """Builds the final prompt string from the template and fetched data."""
    if not data:
        return ""

    # For now, we only use the first data item (e.g., staged changes or latest commit)
    target_data = data[0]
    raw_diff = target_data.diff

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
            with Live(Markdown(""), refresh_per_second=12, console=console) as live:
                async for chunk in provider.stream_response(user_prompt):
                    full_response += chunk
                    live.update(Markdown(full_response, "Response"))
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