import git
import json
import logging
import os
import questionary
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- Configuration & Logging ---
# BEST PRACTICE: Rotate logs to prevent huge files, and force UTF-8 for git diffs
log_handler = RotatingFileHandler(
    "git_extraction.log", 
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=1, 
    encoding='utf-8'
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[log_handler]
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "repo_config.json"
OUTPUT_ROOT_DIR = "Extracted JSON"

# --- Config Management ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"saved_paths": []}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"saved_paths": []}

def save_path_to_config(path):
    config = load_config()
    clean_path = os.path.normpath(path)
    if clean_path not in config["saved_paths"]:
        config["saved_paths"].append(clean_path)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

# --- Core Logic ---
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_diff_text(diff_index):
    """Helper to convert a GitPython DiffIndex into a string."""
    diffs = []
    for diff_item in diff_index:
        try:
            # Handle Rename/New/Deleted
            if diff_item.new_file:
                prefix = f"--- NEW FILE: {diff_item.b_path} ---\n"
            elif diff_item.deleted_file:
                prefix = f"--- DELETED FILE: {diff_item.a_path} ---\n"
            else:
                path = diff_item.b_path if diff_item.b_path else diff_item.a_path
                prefix = f"--- FILE: {path} ---\n"

            # Get Diff Content
            if diff_item.diff:
                diff_text = diff_item.diff.decode('utf-8', 'replace')
            else:
                diff_text = "(New file content)" 

            diffs.append(f"{prefix}{diff_text}")
            
        except Exception as e:
            msg = f"Error reading diff entry: {e}"
            diffs.append(msg)
            logger.error(msg)
            
    return "\n".join(diffs) if diffs else "No changes detected."

def get_commit_diff(commit):
    try:
        if not commit.parents:
            return "Initial Commit - No parent diff available."
        parent = commit.parents[0]
        diff_index = parent.diff(commit, create_patch=True)
        return get_diff_text(diff_index)
    except Exception as e:
        return f"Error extracting diff: {str(e)}"

def get_staged_diff(repo):
    """Extracts diff for currently STAGED changes (Index vs HEAD)."""
    try:
        # STRICT COMPARISON:
        # repo.index.diff(repo.head.commit) -> Compares Index to Head
        # R=True -> Reverse it (Head to Index), which is 'git diff --cached'
        # create_patch=True -> Gets the actual text diff
        diff_index = repo.index.diff(repo.head.commit, create_patch=True, R=True)
        
        return get_diff_text(diff_index)
    except Exception as e:
        logger.error(f"Staged diff error: {e}", exc_info=True)
        return f"Error extracting staged diff: {str(e)}"

def extract_commits_logic(repo_path, output_file, filters):
    try:
        repo = git.Repo(repo_path)
        commits_data = []

        # --- MODE: STAGED CHANGES ---
        if filters.get('mode') == 'staged':
            print("\nProcessing Staged Changes (Pre-Commit)...")
            staged_diff = get_staged_diff(repo)
            
            # Note: "No changes detected." logic depends on get_diff_text output
            if not staged_diff or staged_diff == "No changes detected.":
                print("⚠️  No staged changes found. Did you run 'git add'?")
                # We return 0 so user knows nothing happened, but it's not a crash error
                return 0

            virtual_commit = {
                "hash": "STAGED_CHANGES",
                "short_hash": "STAGED",
                "author": "You (Current User)",
                "date": datetime.now(),
                "message": "PRE-COMMIT: Staged changes ready for analysis.",
                "diff": staged_diff
            }
            commits_data.append(virtual_commit)

        # --- MODE: HISTORY ---
        else:
            kwargs = {}
            if filters.get('limit'): kwargs['max_count'] = int(filters['limit'])
            if filters.get('since'): kwargs['since'] = filters['since']
            if filters.get('until'): kwargs['until'] = filters['until']
            if filters.get('author'): kwargs['author'] = filters['author']

            commits_generator = list(repo.iter_commits(**kwargs))
            total_commits = len(commits_generator)
            print(f"\nProcessing {total_commits} historical commits...")

            for i, commit in enumerate(commits_generator):
                if i % 10 == 0:
                    print(f"  ... processing commit {i+1}/{total_commits}", end='\r')

                commit_info = {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "author": commit.author.name,
                    "date": datetime.fromtimestamp(commit.committed_date),
                    "message": commit.message.strip(),
                    "diff": get_commit_diff(commit)
                }
                commits_data.append(commit_info)

        # Write Output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(commits_data, f, default=json_serial, indent=4)
            
        return len(commits_data)

    except git.exc.InvalidGitRepositoryError:
        logger.critical(f"Invalid git repo: {repo_path}")
        return -1
    except Exception as e:
        logger.critical(f"Error: {e}", exc_info=True)
        return -2

# --- Interactive UI ---
def get_repository_path():
    config = load_config()
    saved_paths = config.get("saved_paths", [])
    selected_path = None
    
    if saved_paths:
        choices = saved_paths + ["-- Enter a New Path --"]
        choice = questionary.select("Select a repository:", choices=choices).ask()
        if choice != "-- Enter a New Path --":
            selected_path = choice
    
    if not selected_path:
        selected_path = questionary.path(
            "Enter path to local git repository:",
            default=".",
            only_directories=True,
            validate=lambda p: os.path.exists(p.strip('"\'')) and os.path.isdir(p.strip('"\'')) or "Directory not found."
        ).ask()
        if selected_path:
            selected_path = selected_path.strip('"\'')
            save_path_to_config(selected_path)
            
    return selected_path

def run_interactive_mode():
    print("\n--- 🤖 LLM Git History Extractor ---\n")

    repo_path = get_repository_path()
    if not repo_path: return

    print(f"Selected Repo: {repo_path}")

    # Menu Choices
    OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
    OPT_ALL = "📜 All History"
    OPT_LIMIT = "🔢 Last N Commits"
    OPT_DATE = "📅 Date Range"
    OPT_AUTHOR = "👤 By Author"

    mode_selection = questionary.select(
        "What would you like to extract?",
        choices=[OPT_STAGED, OPT_ALL, OPT_LIMIT, OPT_DATE, OPT_AUTHOR]
    ).ask()

    # Map selection to a clean directory name
    dir_mapping = {
        OPT_STAGED: "Staged_Changes",
        OPT_ALL: "All_History",
        OPT_LIMIT: "Last_N_Commits",
        OPT_DATE: "Date_Range",
        OPT_AUTHOR: "By_Author"
    }
    
    selected_sub_dir = dir_mapping.get(mode_selection, "Other")
    
    # Create the full output path
    # Path: ./Extracted JSON/[Option_Name]/
    target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, selected_sub_dir)
    os.makedirs(target_dir, exist_ok=True) # Ensure dirs exist

    filters = {}

    # Map selection to filter logic
    if mode_selection == OPT_STAGED:
        filters['mode'] = 'staged'
    elif mode_selection == OPT_LIMIT:
        filters['limit'] = questionary.text("How many commits?", validate=lambda t: t.isdigit()).ask()
    elif mode_selection == OPT_DATE:
        filters['since'] = questionary.text("Start Date (YYYY-MM-DD):").ask()
        filters['until'] = questionary.text("End Date (YYYY-MM-DD) [Optional]:").ask()
        if filters['until'] == "": filters['until'] = None
    elif mode_selection == OPT_AUTHOR:
        filters['author'] = questionary.text("Author Name:").ask()

    # Get filename from user
    filename = questionary.text("Output JSON filename:", default="git_extract.json").ask()
    
    # Combine Directory + Filename
    full_output_path = os.path.join(target_dir, filename)

    if questionary.confirm(f"Ready to extract to:\n   📂 {full_output_path}").ask():
        count = extract_commits_logic(repo_path, full_output_path, filters)
        
        if count > 0:
            print(f"\n✅ Success! Data saved to: {full_output_path}")
            if filters.get('mode') == 'staged':
                print("   (Tip: Upload this to your AI to generate a commit message!)")
        elif count == 0:
            print("\n⚠️  No matching data found.")
        else:
            print("\n❌ Error. Check git_extraction.log.")
    else:
        print("\nOperation cancelled.")

if __name__ == "__main__":
    try:
        run_interactive_mode()
    except KeyboardInterrupt:
        print("\nGoodbye!")