import json
import logging
from pathlib import Path
from typing import List
from pydantic import ValidationError
from src.schemas import PromptTemplate

logger = logging.getLogger(__name__)

# Build a path relative to this file's location -> <src_dir>/../templates
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

def load_templates() -> List[PromptTemplate]:
    """
    Scans the 'templates/' directory, validates them against the PromptTemplate schema,
    and returns a list of valid template objects.
    """
    templates: List[PromptTemplate] = []
    
    if not TEMPLATE_DIR.is_dir():
        logger.warning(f"Template directory '{TEMPLATE_DIR}' not found. Creating it.")
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        return templates

    for file_path in TEMPLATE_DIR.glob("*.json"):
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            validated_template = PromptTemplate.model_validate(data)
            templates.append(validated_template)

        except ValidationError as e:
            logger.error(f"Validation failed for '{file_path.name}': {e}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in '{file_path.name}'.")
        except Exception as e:
            logger.error(f"Failed to load template '{file_path.name}': {e}", exc_info=True)

    return templates