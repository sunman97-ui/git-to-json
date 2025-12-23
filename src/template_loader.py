import os
import json
import logging

logger = logging.getLogger(__name__)

# Constants
TEMPLATE_DIR = "templates"

def load_templates():
    """
    Scans the 'templates/' directory and returns a list of valid template objects.
    """
    templates = []
    
    # Ensure dir exists
    if not os.path.exists(TEMPLATE_DIR):
        logger.warning(f"Template directory '{TEMPLATE_DIR}' not found. Creating it.")
        os.makedirs(TEMPLATE_DIR)
        return []

    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(TEMPLATE_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if validate_schema(data, filename):
                    # Inject filename for internal reference
                    data['_filename'] = filename 
                    templates.append(data)
            
            except Exception as e:
                logger.error(f"Failed to load template {filename}: {e}")

    return templates

def validate_schema(data, filename):
    """
    Ensures the JSON has the 3 required blocks: meta, execution, prompts.
    """
    required_keys = ["meta", "execution", "prompts"]
    for key in required_keys:
        if key not in data:
            logger.warning(f"Skipping {filename}: Missing '{key}' block.")
            return False
            
    # Check sub-keys (Basic validation)
    if "name" not in data["meta"]:
        logger.warning(f"Skipping {filename}: Meta block missing 'name'.")
        return False
        
    return True