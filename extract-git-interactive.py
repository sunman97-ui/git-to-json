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
            # Get the diff text
            # For staged changes, sometimes we need to handle new files (A) vs modified (M)
            if diff_item.new_file:
                # If it's a new file, the diff might be empty in some versions, 
                # so we might want to read the blob directly, but usually diff works.
                prefix = f"--- NEW FILE: {diff_item.b_path} ---\n"
            elif diff_item.deleted_file:
                prefix = f"--- DELETED FILE: {diff_item.a_path} ---\n"
            else:
                path = diff_item.b_path if diff_item.b_path else diff_item.a_path
                prefix = f"--- FILE: {path} ---\n"

            # Check if binary
            if diff_item.diff:
                diff_text = diff_item.diff.decode('utf-8', 'replace')
            else:
                # Sometimes purely new files return None for diff in specific calls
                diff_text = "(New file content)" 

            diffs.append(f"{prefix}{diff_text}")
            
        except Exception as e:
            diffs.append(f"Error reading diff entry: {e}")
            
    return "\n".join(diffs) if diffs else "No changes detected."

def get_commit_diff(commit):
    """Extracts diff for an existing historical commit."""
    try:
        if not commit.parents:
            return "Initial Commit - No parent diff available."
        parent = commit.parents[0]
        # Compare parent -> commit
        diff_index = parent.diff(commit, create_patch=True)
        return get_diff_text(diff_index)
    except Exception as e:
        return f"Error extracting diff: {str(e)}"

def get_staged_diff(repo):
    """Extracts diff for currently STAGED changes (Index vs HEAD)."""
    try:
        # repo.head.commit.diff() compares HEAD against the Index (Staged)
        # create_patch=True ensures we get the text diff
        diff_index = repo.head.commit.diff(None, create_patch=True)
        
        # Note: logic is inverted slightly in wording vs history, but content is correct.
        return get_diff_text(diff_index)
    except Exception as e:
        return f"Error extracting staged diff: {str(e)}"

def extract_commits_logic(repo_path, output_file, filters):
    try:
        repo = git.Repo(repo_path)
        commits_data = []

        # --- MODE: STAGED CHANGES ---
        if filters.get('mode') == 'staged':
            print("\nProcessing Staged Changes (Pre-Commit)...")
            
            # Create a "Virtual Commit" object
            staged_diff = get_staged_diff(repo)
            
            if not staged_diff or staged_diff == "No changes detected.":
                print("⚠️  No staged changes found. Did you run 'git add'?")
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

    # Updated Menu Options
    mode_selection = questionary.select(
        "What would you like to extract?",
        choices=[
            "📝 Staged Changes (Pre-Commit Analysis)", 
            "📜 All History",
            "🔢 Last N Commits",
            "📅 Date Range",
            "👤 By Author"
        ]
    ).ask()

    filters = {}

    # Map selection to filter logic
    if "Staged Changes" in mode_selection:
        filters['mode'] = 'staged'
    elif "Last N Commits" in mode_selection:
        filters['limit'] = questionary.text("How many commits?", validate=lambda t: t.isdigit()).ask()
    elif "Date Range" in mode_selection:
        filters['since'] = questionary.text("Start Date (YYYY-MM-DD):").ask()
        filters['until'] = questionary.text("End Date (YYYY-MM-DD) [Optional]:").ask()
        if filters['until'] == "": filters['until'] = None
    elif "By Author" in mode_selection:
        filters['author'] = questionary.text("Author Name:").ask()

    output_file = questionary.text("Output JSON filename:", default="git_extract.json").ask()

    if questionary.confirm(f"Ready to extract?").ask():
        abs_output_path = os.path.abspath(output_file)
        count = extract_commits_logic(repo_path, abs_output_path, filters)
        
        if count > 0:
            print(f"\n✅ Success! Data saved to: {abs_output_path}")
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