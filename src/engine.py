import logging
import asyncio
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

# Core & Config Imports
from src.core import fetch_repo_data
from src.utils import save_data_to_file, count_tokens
from src.config import load_settings
from src.providers import get_provider

logger = logging.getLogger(__name__)
console = Console()

# Constants
OUTPUT_ROOT_DIR = "Extracted JSON"

def run_template_workflow(repo_path, template):
    """
    Orchestrates the Flow: Data Fetch -> Prompt Build
    RETURNS the prompt string (does not print/copy it).
    """
    
    # 1. Parse Execution Config
    exec_config = template.get("execution", {})
    source_mode = exec_config.get("source", "staged") 
    
    # 2. Fetch Data (In-Memory)
    filters = {"mode": source_mode}
    
    console.print(f"   ⚙️  Fetching data (Mode: {source_mode})...", style="dim")
    data = fetch_repo_data(repo_path, filters)
    
    if not data:
        console.print("   ⚠️  No data found (Empty diff).", style="yellow")
        return None

    # 3. Build Prompt (Hydration)
    target_commit = data[0]
    raw_diff = target_commit.get("diff", "")
    
    # Load raw prompts
    system_prompt = template["prompts"]["system"]
    user_prompt_template = template["prompts"]["user"]
    
    # Inject Variables
    final_user_prompt = user_prompt_template.replace("{DIFF_CONTENT}", raw_diff)
    
    # Construct Full Payload
    full_payload = (
        f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n"
        f"--- USER PROMPT ---\n{final_user_prompt}"
    )
    
    # Calculate Tokens
    token_count = count_tokens(full_payload)
    console.print(f"   📊  Payload size: {token_count} tokens", style="dim")

    # 🛑 STOP: We removed the auto-clipboard logic here.
    # We just return the data so CLI can decide what to do.
    return full_payload


def run_llm_execution(provider_name, user_prompt):
    """
    Orchestrates the async streaming flow for LLM providers.
    Uses Rich Live to render the response in real-time.
    """
    # 1. Load the secure settings (validates .env implicitly)
    settings = load_settings()
    
    try:
        # 2. Initialize the specific provider via Factory
        provider = get_provider(provider_name, settings)
        
        console.print(f"\n[bold green]Connecting to {provider_name.upper()}...[/]")
        
        # 3. Define the Async Stream Task
        async def stream_task():
            full_response = ""
            # refresh_per_second=12 gives a smooth 'typing' feel
            with Live(Markdown(""), refresh_per_second=12, console=console) as live:
                async for chunk in provider.stream_response(user_prompt):
                    full_response += chunk
                    live.update(Markdown(full_response))
            return full_response

        # 4. Run the async loop
        return asyncio.run(stream_task())

    except ValueError as e:
        console.print(f"\n[bold red]Configuration Error:[/]\n{e}")
        console.print("[yellow]Tip: Check your .env file keys.[/]")
    except Exception as e:
        logger.error("LLM Execution Error", exc_info=True)
        console.print(f"\n[bold red]Connection Error:[/]\n{e}")