import logging

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from src.providers import get_provider
from src.config import LLMSettings

logger = logging.getLogger(__name__)


async def stream_ai_response(
    console: Console,
    settings: LLMSettings,
    provider_name: str,
    user_prompt: str,
):
    """Handles the streaming of the AI response to the console."""
    try:
        provider = get_provider(provider_name, settings)
        console.print(
            f"\n[bold green]Connecting to {provider_name.upper()}...[/]"
        )

        full_response = ""
        async with provider:
            with Live(
                Markdown(""), refresh_per_second=12, console=console
            ) as live:
                async for chunk in provider.stream_response(user_prompt):
                    full_response += chunk
                    live.update(Markdown(full_response, style="blue"))
                live.stop()
        return full_response
    except Exception as e:
        console.print(f"\n[bold red]AI Execution Error:[/]\n{e}")
        logger.error(f"Stream error: {e}", exc_info=True)
        return None
