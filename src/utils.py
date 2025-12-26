import json
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List
import tiktoken
from appdirs import AppDirs
from pydantic import BaseModel

# Initialize AppDirs
dirs = AppDirs("git-to-json", "sunman97-ui")
CONFIG_DIR = Path(dirs.user_config_dir)
CONFIG_FILE = CONFIG_DIR / "repo_config.json"
LOG_FILE = "git_extraction.log"


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Returns the number of tokens in a text string using tiktoken.
    Defaults to gpt-4 encoding (cl100k_base).
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        encoding = tiktoken.get_encoding("cl100k_base")  # Fallback to GPT-4 encoding
        logging.getLogger(__name__).warning(
            f"Error encoding tokens, falling back: {e}", exc_info=True
        )
        return len(encoding.encode(text, errors="replace"))


def setup_logging():
    """Configures application-wide logging with rotation and UTF-8 support."""
    log_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8"  # 5 MB
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[log_handler],
    )
    return logging.getLogger("GitToJson")


def load_config() -> dict:
    """Loads the repository history configuration from the user's config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.is_file():
        return {"saved_paths": []}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.getLogger(__name__).error(
            f"Failed to load config file: {e}", exc_info=True
        )
        return {"saved_paths": []}


def save_path_to_config(path: str):
    """Updates the repository history configuration in the user's config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    clean_path = os.path.normpath(path)

    if clean_path not in config.get("saved_paths", []):
        config.setdefault("saved_paths", []).append(clean_path)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            logging.getLogger(__name__).error(
                f"Failed to save config file: {e}", exc_info=True
            )


def save_data_to_file(data: List[BaseModel], output_path: str) -> bool:
    """
    Writes a list of Pydantic models to a JSON file.
    """
    try:
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dicts first
        data_as_dicts = [item.model_dump(mode="json") for item in data]

        # OPTIMIZATION: Stream directly to the file object (json.dump)
        # instead of creating a large intermediate string string (json.dumps).
        with open(output_path_obj, "w", encoding="utf-8") as f:
            json.dump(data_as_dicts, f, indent=4)

        return True
    except (TypeError, IOError) as e:
        logging.getLogger(__name__).error(
            f"Failed to save data to {output_path}: {e}", exc_info=True
        )
        return False
