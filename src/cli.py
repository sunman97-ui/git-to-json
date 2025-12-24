import os
import pyperclip
from rich.console import Console
from src.utils import load_config, save_path_to_config, setup_logging, save_data_to_file
from src.template_loader import load_templates
from src.core import fetch_repo_data
from src.engine import generate_prompt_from_template, stream_llm_response
import src.tui as tui

# Initialize Logger & Console
logger = setup_logging()
console = Console()

OUTPUT_ROOT_DIR = "Extracted JSON"
OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
OPT_ALL = "📜 All History"
OPT_LIMIT = "🔢 Last N Commits"
OPT_DATE = "📅 Date Range"
OPT_AUTHOR = "👤 By Author"

def get_repository_path():
    """Gets the repository path from the user, utilizing saved paths."""
    config = load_config()
    saved_paths = config.get("saved_paths", [])
    path = tui.get_repository_path(saved_paths)
    if path and path not in saved_paths:
        save_path_to_config(path)
    return path

def handle_raw_extraction(repo_path):
    """Manages the raw data extraction workflow."""
    mode_selection = tui.get_raw_extraction_mode()
    if not mode_selection:
        return

    dir_mapping = {
        OPT_STAGED: "Staged_Changes",
        OPT_ALL: "All_History",
        OPT_LIMIT: "Last_N_Commits",
        OPT_DATE: "Date_Range",
        OPT_AUTHOR: "By_Author",
    }
    selected_sub_dir = dir_mapping.get(mode_selection, "Other")
    
    filters = tui.get_raw_extraction_filters(mode_selection)

    try:
        console.print("   ⚙️  Extracting data...")
        data = fetch_repo_data(repo_path, filters)
        
        if not data:
            console.print("\n⚠️  No matching data found.")
            return

        filename = tui.get_output_filename()
        if not filename:
            return

        target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, selected_sub_dir)
        full_output_path = os.path.join(target_dir, filename)

        if tui.confirm_save(full_output_path, len(data)):
            if save_data_to_file(data, full_output_path):
                console.print(f"\n✅ Success! Saved to {full_output_path}", style="bold green")
            else:
                console.print("\n❌ Error saving file. Check logs.", style="bold red")
        else:
            console.print("Operation cancelled.")

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        logger.error("Raw extraction failed", exc_info=True)

def handle_direct_execution():
    """Manages the direct AI prompt execution workflow."""
    provider = tui.select_llm_provider()
    if provider:
        prompt = tui.get_user_prompt()
        if prompt:
            stream_llm_response(provider, prompt)

def handle_template_workflow(repo_path, templates, selection_name):
    """Manages the template-based workflow."""
    selected_template = next((t for t in templates if t.meta.name == selection_name), None)
    if not selected_template:
        return

    prompt = generate_prompt_from_template(repo_path, selected_template)
    if not prompt:
        return

    output_option = tui.get_prompt_handling_choice()

    if output_option == "cancel" or output_option is None:
        return

    if output_option == "clipboard":
        try:
            pyperclip.copy(prompt)
            console.print("\n✅  Success! Prompt copied to clipboard.", style="bold green")
        except Exception as e:
            console.print(f"\n❌ Clipboard error: {e}", style="bold red")
    elif output_option == "file":
        filename = tui.get_prompt_filename()
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(prompt)
                console.print(f"\n✅  Saved to {filename}", style="green")
            except Exception as e:
                console.print(f"\n❌ Error saving file: {e}", style="bold red")
    elif output_option == "execute":
        provider = tui.select_llm_provider()
        if provider:
            console.print("\n🤖 [Agent] Initializing AI Execution...", style="bold purple")
            stream_llm_response(provider, prompt)

def run_app():
    """Main Application Loop"""
    console.print("\n--- 🤖 Git-to-JSON Framework (v3.0) ---\n", style="bold blue")

    repo_path = get_repository_path()
    if not repo_path:
        return

    logger.info(f"Session started for: {repo_path}")
    console.print(f"Selected Repo: [green]{repo_path}[/green]")

    templates = load_templates()

    while True:
        selection_name = tui.get_main_menu_choice(templates)

        if selection_name == "❌ Exit":
            break
        elif selection_name == "💾 Extract Raw Data (Classic Mode)":
            handle_raw_extraction(repo_path)
        elif selection_name == "🚀 Execute AI Prompt (Direct Mode)":
            handle_direct_execution()
        else:
            handle_template_workflow(repo_path, templates, selection_name)

        if not tui.confirm_another_action():
            break
            
    console.print("Goodbye!", style="bold blue")

if __name__ == "__main__":
    run_app()