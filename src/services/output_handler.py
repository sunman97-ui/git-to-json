import logging
import pyperclip

logger = logging.getLogger(__name__)


def save_prompt_to_file(prompt_text: str, filepath: str) -> bool:
    """Saves the given text to a file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        return True
    except Exception as e:
        logger.error(f"Failed to save prompt: {e}")
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copies the given text to the system clipboard."""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.error(f"Clipboard error: {e}")
        return False
