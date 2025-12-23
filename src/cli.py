import os
import questionary
from src.utils import load_config, save_path_to_config, setup_logging
from src.template_loader import load_templates
from src.engine import run_template_workflow

# Initialize Logger
logger = setup_logging()

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

def run_app():
    """Main Application Loop"""
    print("\n--- 🤖 Git-to-JSON Framework (v2.1) ---\n")

    repo_path = get_repository_path()
    if not repo_path: return

    logger.info(f"Session started for: {repo_path}")
    print(f"Selected Repo: {repo_path}")

    # 1. Load Templates
    templates = load_templates()
    
    if not templates:
        print("\n❌ No templates found in 'templates/' directory.")
        print("   Please create 'templates/commit_message.json' first.")
        return

    # 2. Build Menu Choices
    # We display the 'name' from the meta block
    choices = [t["meta"]["name"] for t in templates]
    choices.append("❌ Exit")

    selection_name = questionary.select(
        "What is your goal?",
        choices=choices
    ).ask()

    if selection_name == "❌ Exit":
        print("Goodbye!")
        return

    # 3. Find the selected template object
    selected_template = next(t for t in templates if t["meta"]["name"] == selection_name)
    
    # 4. Run the Engine
    try:
        run_template_workflow(repo_path, selected_template)
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        logger.critical("App crash", exc_info=True)