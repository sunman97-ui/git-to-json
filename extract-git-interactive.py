import git
import json
import logging
import os
import questionary
from datetime import datetime

# --- Configuration & Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("git_extraction.log")]
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "repo_config.json"

# --- Config Management ---

def load_config():
    """Loads the list of saved repo paths from JSON."""
    if not os.path.exists(CONFIG_FILE):
        return {"saved_paths": []}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"saved_paths": []}

def save_path_to_config(path):
    """Saves a new valid path to the config file."""
    config = load_config()
    # Normalize path to fix slashes
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

def get_commit_diff(commit):
    diffs = []
    try:
        if not commit.parents:
            diffs.append("Initial Commit - No parent diff available.")
        else:
            parent = commit.parents[0]
            diff_index = parent.diff(commit, create_patch=True)
            for diff_item in diff_index:
                diff_text = diff_item.diff.decode('utf-8', 'replace')
                file_path = diff_item.b_path if diff_item.b_path else diff_item.a_path
                diffs.append(f"--- FILE: {file_path} ---\n{diff_text}")
    except Exception as e:
        logger.error(f"Error extracting diff for commit {commit.hexsha}: {e}")
        diffs.append(f"Error extracting diff: {str(e)}")
    return "\n".join(diffs)

def extract_commits_logic(repo_path, output_file, filters):
    try:
        repo = git.Repo(repo_path)
        
        kwargs = {}
        if filters.get('limit'):
            kwargs['max_count'] = int(filters['limit'])
        if filters.get('since'):
            kwargs['since'] = filters['since']
        if filters.get('until'):
            kwargs['until'] = filters['until']
        if filters.get('author'):
            kwargs['author'] = filters['author']

        commits_data = []
        commits_generator = list(repo.iter_commits(**kwargs))
        total_commits = len(commits_generator)
        
        print(f"\nProcessing {total_commits} commits...")

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
    """Handles logic for selecting saved paths or entering a new one."""
    config = load_config()
    saved_paths = config.get("saved_paths", [])
    
    selected_path = None
    
    # If we have saved paths, offer them as choices
    if saved_paths:
        choices = saved_paths + ["-- Enter a New Path --"]
        choice = questionary.select(
            "Select a repository:",
            choices=choices
        ).ask()
        
        if choice != "-- Enter a New Path --":
            selected_path = choice
    
    # If no saved paths OR user selected "Enter New Path"
    if not selected_path:
        # We update the validation logic to strip quotes before checking
        selected_path = questionary.path(
            "Enter path to local git repository:",
            default=".",
            only_directories=True,
            validate=lambda p: os.path.exists(p.strip('"\'')) and os.path.isdir(p.strip('"\'')) or "Directory not found."
        ).ask()
        
        # CLEANUP: Strip quotes from the final string before saving/using
        if selected_path:
            selected_path = selected_path.strip('"\'')
            save_path_to_config(selected_path)
            
    return selected_path

def run_interactive_mode():
    print("\n--- 🤖 LLM Git History Extractor ---\n")

    # 1. Get Path (with Config Memory)
    repo_path = get_repository_path()
    if not repo_path:
        return # User cancelled

    print(f"Selected Repo: {repo_path}")

    # 2. Select Filter Mode
    mode = questionary.select(
        "How would you like to filter commits?",
        choices=[
            "Extract Everything (All History)",
            "Last N Commits (e.g., last 10)",
            "Date Range",
            "By Author"
        ]
    ).ask()

    filters = {}

    if mode == "Last N Commits (e.g., last 10)":
        filters['limit'] = questionary.text("How many commits?", validate=lambda t: t.isdigit()).ask()
    elif mode == "Date Range":
        filters['since'] = questionary.text("Start Date (YYYY-MM-DD):").ask()
        filters['until'] = questionary.text("End Date (YYYY-MM-DD) [Optional]:").ask()
        if filters['until'] == "": filters['until'] = None
    elif mode == "By Author":
        filters['author'] = questionary.text("Author Name:").ask()

    # 3. Output
    output_file = questionary.text("Output JSON filename:", default="git_history.json").ask()

    # 4. Confirmation
    if questionary.confirm(f"Ready to extract?").ask():
        abs_output_path = os.path.abspath(output_file)
        count = extract_commits_logic(repo_path, abs_output_path, filters)
        
        if count > 0:
            print(f"\n✅ Success! {count} commits saved to: {abs_output_path}")
        elif count == 0:
            print("\n⚠️  No commits found matching your criteria.")
        else:
            print("\n❌ Error. Check git_extraction.log.")
    else:
        print("\nOperation cancelled.")

if __name__ == "__main__":
    try:
        run_interactive_mode()
    except KeyboardInterrupt:
        print("\nGoodbye!")