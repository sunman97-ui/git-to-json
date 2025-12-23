import os
import pyperclip
import logging
from datetime import datetime
from src.core import fetch_repo_data
from src.utils import save_data_to_file, count_tokens

logger = logging.getLogger(__name__)

# Constants
CLIPBOARD_LIMIT = 15000  # Conservative limit (approx 4k tokens)
OUTPUT_ROOT_DIR = "Extracted JSON"
TOKEN_LIMIT_CLIPBOARD = 3500  # Safe buffer 

def run_template_workflow(repo_path, template):
    """
    Orchestrates the Flow: Data Fetch -> Prompt Build -> Output
    """
    
    # 1. Parse Execution Config
    exec_config = template.get("execution", {})
    source_mode = exec_config.get("source", "staged") # Default to staged
    
    # 2. Fetch Data (In-Memory)
    # We construct a filter object compatible with core.fetch_repo_data
    filters = {"mode": source_mode}
    
    # (Future: map other template filters like 'limit' or 'author' here if needed)
    
    print(f"   ⚙️  Fetching data (Mode: {source_mode})...")
    data = fetch_repo_data(repo_path, filters)
    
    if not data:
        print("   ⚠️  No data found (Empty diff).")
        return

    # 3. Build Prompt (Hydration)
    # For now, we assume we are processing the FIRST item (usually sufficient for Staged mode)
    # In 'history' mode, you might want to loop this, but for commit gen, we take index 0.
    target_commit = data[0]
    
    raw_diff = target_commit.get("diff", "")
    
    # Load raw prompts
    system_prompt = template["prompts"]["system"]
    user_prompt_template = template["prompts"]["user"]
    
    # Inject Variables
    # We replace {DIFF_CONTENT} with the actual string
    final_user_prompt = user_prompt_template.replace("{DIFF_CONTENT}", raw_diff)
    
    # Construct Full Payload (for clipboard/file)
    # We format it so it's ready to paste into a Chat Interface
    full_payload = (
        f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n"
        f"--- USER PROMPT ---\n{final_user_prompt}"
    )
    
    # 4. Smart Output Handling
    output_mode = exec_config.get("output_mode", "auto")
    
    # Calculate Tokens
    token_count = count_tokens(full_payload)
    print(f"   📊  Payload size: {token_count} tokens")

    # Determine Action
    should_clip = False
    
    if output_mode == "clipboard":
        should_clip = True
    elif output_mode == "auto":
        if token_count < TOKEN_LIMIT_CLIPBOARD:
            should_clip = True
        else:
            print(f"   ⚠️  Payload ({token_count} tokens) exceeds limit ({TOKEN_LIMIT_CLIPBOARD}). Switched to file.")
            should_clip = False
            
    # Execute Output
    if should_clip:
        try:
            pyperclip.copy(full_payload)
            print("\n✅  Success! Prompt copied to clipboard.")
            print("    (Just paste it into ChatGPT/Claude)")
        except Exception as e:
            logger.error(f"Clipboard failed: {e}")
            print("\n❌  Clipboard error. Saving to file instead.")
            save_prompt_to_file(template, full_payload)
    else:
        save_prompt_to_file(template, full_payload)

def save_prompt_to_file(template, payload):
    """Fallback: Saves prompt to a text file."""
    # Create path: Extracted JSON / Template Name / prompt.txt
    safe_name = template["meta"]["name"].replace(" ", "_").replace("/", "-")
    target_dir = os.path.join(OUTPUT_ROOT_DIR, safe_name)
    os.makedirs(target_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"PROMPT_{timestamp}.md"
    full_path = os.path.join(target_dir, filename)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(payload)
        
    print(f"\n📁  Saved prompt to: {full_path}")