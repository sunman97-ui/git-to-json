import os
from rich.console import Console
from src.utils import load_config, save_path_to_config, setup_logging
from src.template_loader import load_templates
from src.engine import AuditEngine
from src.schemas import PromptTemplate, TemplateMeta, TemplateExecution, TemplatePrompts
import src.tui as tui

# --- SETUP ---
logger = setup_logging()
console = Console()
engine = AuditEngine(console)

# --- CONSTANTS ---
# Preserved for compatibility with tests and consistent naming
OUTPUT_ROOT_DIR = "Extracted JSON"
OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
OPT_ALL = "📜 All History"
OPT_LIMIT = "🔢 Last N Commits"
OPT_DATE = "📅 Date Range"
OPT_AUTHOR = "👤 By Author"

# --- HELPER FUNCTIONS ---


def get_repository_path():
    """Gets the repository path from the user, utilizing saved paths."""
    config = load_config()
    saved_paths = config.get("saved_paths", [])
    path = tui.get_repository_path(saved_paths)

    if path and path not in saved_paths:
        save_path_to_config(path)

    return path


def resolve_output_path(filename: str, subfolder: str = "General") -> str:
    """Standardizes where files are saved."""
    target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, filename)


# --- WORKFLOW HANDLERS ---


def handle_raw_extraction(repo_path):
    """
    Classic Mode: Extract Git data -> Save to JSON.
    """
    mode_selection = tui.get_raw_extraction_mode()
    if not mode_selection:
        return

    # 1. Gather Inputs
    filters = tui.get_raw_extraction_filters(mode_selection)
    filename = tui.get_output_filename()
    if not filename:
        return

    # 2. Determine Output Path
    # Map selection string to folder name
    dir_mapping = {
        OPT_STAGED: "Staged_Changes",
        OPT_ALL: "All_History",
        OPT_LIMIT: "Last_N_Commits",
        OPT_DATE: "Date_Range",
        OPT_AUTHOR: "By_Author",
    }
    # Fallback logic if string manipulation was used in tests or future extensions
    folder_name = dir_mapping.get(mode_selection, "Raw_Data")

    full_path = resolve_output_path(filename, folder_name)

    # 3. Delegate to Engine
    if tui.confirm_save(full_path, "matching items"):
        success = engine.execute_raw_extraction(repo_path, filters, full_path)
        if success:
            console.print(f"\n✅ Saved to {full_path}", style="bold green")


def handle_template_workflow(repo_path, templates, selection_name):
    """
    Template Mode: Select Template -> Process Data -> AI/File/Clipboard.
    """
    selected_template = next(
        (t for t in templates if t.meta.name == selection_name), None
    )
    if not selected_template:
        return

    # Engine handles fetching logic
    filters = {"mode": selected_template.execution.source}
    if filters["mode"] == "history":
        filters["limit"] = selected_template.execution.limit

    data = engine.fetch_data(repo_path, filters)
    if not data:
        return

    prompt = engine.build_prompt(selected_template, data)

    action = tui.get_prompt_handling_choice()

    if action == "clipboard":
        if engine.copy_to_clipboard(prompt):
            console.print("\n✅ Prompt copied to clipboard.", style="bold green")

    elif action == "file":
        filename = tui.get_prompt_filename()
        if filename:
            if engine.save_prompt_to_file(prompt, filename):
                console.print(f"\n✅ Saved to {filename}", style="green")

    elif action == "execute":
        provider = tui.select_llm_provider()
        if provider:
            engine.execute_ai_stream(provider, prompt)


def handle_interactive_workflow(repo_path):
    """
    Interactive Mode: Manually pick commits -> AI/Save.
    """
    console.print("\n[bold cyan]-- Interactive Commit Selection --[/bold cyan]")
    selected_hashes = tui.select_commits_interactively(repo_path)
    if not selected_hashes:
        return

    console.print(f"   ⚙️  Hydrating {len(selected_hashes)} selected commits...")
    data = engine.fetch_data(repo_path, {"mode": "hashes", "hashes": selected_hashes})
    if not data:
        return

    output_choice = tui.get_interactive_output_choice()

    if output_choice == "extract":
        filename = tui.get_output_filename(default_name="combined_commits.json")
        if filename:
            full_path = resolve_output_path(filename, "Interactive")
            if engine.execute_raw_extraction(
                repo_path, {"mode": "hashes", "hashes": selected_hashes}, full_path
            ):
                console.print(f"\n✅ Saved to {full_path}", style="bold green")

    elif output_choice == "ai":
        generic_template = PromptTemplate(
            meta=TemplateMeta(name="Interactive", description="Ad-hoc analysis"),
            execution=TemplateExecution(source="history"),
            prompts=TemplatePrompts(
                system="You are a senior software engineer.",
                user="Analyze these specific commits:\n\n{DIFF_CONTENT}",
            ),
        )
        prompt = engine.build_prompt(generic_template, data)

        provider = tui.select_llm_provider()
        if provider:
            engine.execute_ai_stream(provider, prompt)


def handle_direct_execution():
    """Direct Mode: Just Chat."""
    provider = tui.select_llm_provider()
    if provider:
        prompt = tui.get_user_prompt()
        if prompt:
            engine.execute_ai_stream(provider, prompt)


# --- MAIN LOOP ---


def run_app():
    console.print(
        "\n--- 🤖 Git-to-JSON Framework (v3.1 Refactored) ---\n", style="bold blue"
    )

    # Use the restored helper function
    repo_path = get_repository_path()
    if not repo_path:
        return

    logger.info(f"Session started for: {repo_path}")
    templates = load_templates()

    while True:
        selection_name = tui.get_main_menu_choice(templates)

        try:
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

        except Exception as e:
            console.print(f"\n❌ Application Error: {e}", style="bold red")
            logger.error("Top level error", exc_info=True)

        if not tui.confirm_another_action():
            break

    console.print("Goodbye!", style="bold blue")


if __name__ == "__main__":
    run_app()
