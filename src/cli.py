import os
import pyperclip
from rich.console import Console
from src.utils import load_config, save_path_to_config, setup_logging, save_data_to_file
from src.template_loader import load_templates
from src.core import fetch_repo_data
from src.engine import generate_prompt_from_template, stream_llm_response, _build_prompt_from_data, WorkflowExecutor
from src.schemas import PromptTemplate, TemplateMeta, TemplateExecution, TemplatePrompts
import src.tui as tui

# Initialize Logger & Console
logger = setup_logging()
console = Console()
executor = WorkflowExecutor(console, logger)

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

def _handle_raw_extraction_logic(repo_path):
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

def handle_raw_extraction(repo_path):
    """Manages the raw data extraction workflow."""
    executor.execute_with_boundary("Raw Data Extraction", _handle_raw_extraction_logic, repo_path)

def _handle_direct_execution_logic():
    provider = tui.select_llm_provider()
    if provider:
        prompt = tui.get_user_prompt()
        if prompt:
            stream_llm_response(provider, prompt)

def handle_direct_execution():
    """Manages the direct AI prompt execution workflow."""
    executor.execute_with_boundary("Direct AI Execution", _handle_direct_execution_logic)

def _handle_template_workflow_logic(repo_path, templates, selection_name):
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
        pyperclip.copy(prompt)
        console.print("\n✅  Success! Prompt copied to clipboard.", style="bold green")
    elif output_option == "file":
        filename = tui.get_prompt_filename()
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(prompt)
            console.print(f"\n✅  Saved to {filename}", style="green")
    elif output_option == "execute":
        provider = tui.select_llm_provider()
        if provider:
            console.print("\n🤖 [Agent] Initializing AI Execution...", style="bold purple")
            stream_llm_response(provider, prompt)

def handle_template_workflow(repo_path, templates, selection_name):
    """Manages the template-based workflow."""
    executor.execute_with_boundary("Template Workflow", _handle_template_workflow_logic, repo_path, templates, selection_name)

def _handle_interactive_workflow_logic(repo_path):
    """Manages the interactive commit selection workflow."""
    console.print("\n[bold cyan]-- Interactive Commit Selection --[/bold cyan]")
    selected_hashes = tui.select_commits_interactively(repo_path)

    if not selected_hashes:
        console.print("No commits selected.")
        return

    console.print(f"   ⚙️  Fetching full data for {len(selected_hashes)} selected commits...")
    commit_data = fetch_repo_data(repo_path, {"mode": "hashes", "hashes": selected_hashes})

    if not commit_data:
        console.print("\n⚠️  Could not retrieve data for selected commits.")
        return

    output_choice = tui.get_interactive_output_choice()

    if output_choice == "extract":
        filename = tui.get_output_filename(default_name="combined_commits.json")
        if not filename:
            return

        target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, "Combined_Commits")
        full_output_path = os.path.join(target_dir, filename)

        if tui.confirm_save(full_output_path, len(commit_data)):
            if save_data_to_file(commit_data, full_output_path):
                console.print(f"\n✅ Success! Saved to {full_output_path}", style="bold green")
            else:
                console.print("\n❌ Error saving file. Check logs.", style="bold red")

    elif output_choice == "ai":
        # Create a generic template on the fly for combined analysis
        generic_template = PromptTemplate(
            meta=TemplateMeta(name="Interactive Analysis", description="Analysis of interactively selected commits."),
            execution=TemplateExecution(source="history"),
            prompts=TemplatePrompts(
                system="You are a senior software engineer analyzing code changes from multiple commits.",
                user="Analyze the following combined diffs and provide a comprehensive summary of changes, potential bugs, or refactoring opportunities.\n\n{DIFF_CONTENT}"
            )
        )

        console.print("   Building prompt from combined diffs...")
        prompt = _build_prompt_from_data(generic_template, commit_data)

        if not prompt:
            console.print("\n⚠️  Failed to build prompt from selected commits.")
            return

        provider = tui.select_llm_provider()
        if provider:
            console.print("\n🤖 [Agent] Initializing AI Execution...", style="bold purple")
            stream_llm_response(provider, prompt)

def handle_interactive_workflow(repo_path):
    """Manages the interactive commit selection workflow."""
    executor.execute_with_boundary("Interactive Workflow", _handle_interactive_workflow_logic, repo_path)

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
        elif selection_name == "🤝 Interactive Commit Selection":
            handle_interactive_workflow(repo_path)
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