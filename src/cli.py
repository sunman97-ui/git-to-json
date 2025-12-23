import os
import questionary
from src.utils import load_config, save_path_to_config, setup_logging, save_data_to_file
from src.template_loader import load_templates
from src.engine import run_template_workflow
from src.core import fetch_repo_data

# Initialize Logger
logger = setup_logging()

OUTPUT_ROOT_DIR = "Extracted JSON"

def get_repository_path():
    """Interactively asks user to select or input a repo path."""
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

def run_raw_extraction_mode(repo_path):
    """
    Restores the classic 'Extract to JSON' functionality.
    """
    # Menu Options
    OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
    OPT_ALL = "📜 All History"
    OPT_LIMIT = "🔢 Last N Commits"
    OPT_DATE = "📅 Date Range"
    OPT_AUTHOR = "👤 By Author"

    mode_selection = questionary.select(
        "Raw Data Extraction: What filters?",
        choices=[OPT_STAGED, OPT_ALL, OPT_LIMIT, OPT_DATE, OPT_AUTHOR]
    ).ask()

    # Directory Mapping
    dir_mapping = {
        OPT_STAGED: "Staged_Changes",
        OPT_ALL: "All_History",
        OPT_LIMIT: "Last_N_Commits",
        OPT_DATE: "Date_Range",
        OPT_AUTHOR: "By_Author"
    }
    selected_sub_dir = dir_mapping.get(mode_selection, "Other")

    # Filter Logic
    filters = {}
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

    # Execution
    try:
        print("   ⚙️  Extracting data...")
        data = fetch_repo_data(repo_path, filters)
        
        count = len(data)
        if count == 0:
            print("\n⚠️  No matching data found.")
            return

        # Output Handling
        filename = questionary.text("Output JSON filename:", default="raw_data.json").ask()
        target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, selected_sub_dir)
        full_output_path = os.path.join(target_dir, filename)

        if questionary.confirm(f"Save {count} items to:\n   📂 {full_output_path}").ask():
            success = save_data_to_file(data, full_output_path)
            if success:
                print(f"\n✅ Success! Saved to {full_output_path}")
            else:
                print("\n❌ Error saving file. Check logs.")
        else:
            print("Operation cancelled.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Raw extraction failed", exc_info=True)


def run_app():
    """Main Application Loop"""
    print("\n--- 🤖 Git-to-JSON Framework (v2.2) ---\n")

    repo_path = get_repository_path()
    if not repo_path: return

    logger.info(f"Session started for: {repo_path}")
    print(f"Selected Repo: {repo_path}")

    # 1. Load Templates
    templates = load_templates()
    
    # 2. Build Menu Choices
    # We mix Templates (Framework) with Raw Tools (Classic)
    choices = []
    
    if templates:
        choices.extend([t["meta"]["name"] for t in templates])
        choices.append(questionary.Separator()) # Visual separator
    
    choices.append("💾 Extract Raw Data (Classic Mode)")
    choices.append("❌ Exit")

    selection_name = questionary.select(
        "What is your goal?",
        choices=choices
    ).ask()

    # 3. Handle Selection
    if selection_name == "❌ Exit":
        print("Goodbye!")
        return
        
    elif selection_name == "💾 Extract Raw Data (Classic Mode)":
        run_raw_extraction_mode(repo_path)
        
    else:
        # It's a template
        selected_template = next(t for t in templates if t["meta"]["name"] == selection_name)
        try:
            run_template_workflow(repo_path, selected_template)
        except Exception as e:
            print(f"\n❌ Critical Error: {e}")
            logger.critical("App crash", exc_info=True)