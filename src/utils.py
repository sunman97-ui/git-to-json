import json
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import tiktoken

# Constants
CONFIG_FILE = "repo_config.json"
LOG_FILE = "git_extraction.log"

def count_tokens(text, model="gpt-4"):
    """
    Returns the number of tokens in a text string using tiktoken.
    Defaults to gpt-4 encoding (cl100k_base).
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback if model is unknown or tiktoken fails
        logging.getLogger(__name__).warning(f"Token count failed: {e}. using char estimate.")
        return len(text) // 4  # Rough estimate

def setup_logging():
    """Configures application-wide logging with rotation and UTF-8 support."""
    log_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=1, 
        encoding='utf-8'
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[log_handler]
    )
    return logging.getLogger("GitToJson")

def load_config():
    """Loads the repository history configuration."""
    if not os.path.exists(CONFIG_FILE):
        return {"saved_paths": []}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"saved_paths": []}

def save_path_to_config(path):
    """Updates the repository history configuration."""
    config = load_config()
    clean_path = os.path.normpath(path)
    
    # Avoid duplicates
    if clean_path not in config["saved_paths"]:
        config["saved_paths"].append(clean_path)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def save_data_to_file(data, output_path):
    """
    Writes the extracted data list to a JSON file.
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=json_serial, indent=4)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to save data: {e}", exc_info=True)
        return False