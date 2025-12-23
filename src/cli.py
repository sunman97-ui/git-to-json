import os
import questionary
import pyperclip
from rich.console import Console
from src.utils import load_config, save_path_to_config, setup_logging, save_data_to_file
from src.template_loader import load_templates
from src.core import fetch_repo_data

# ✅ Import BOTH functions from your robust engine
from src.engine import run_template_workflow, run_llm_execution 

# Initialize Logger & Console
logger = setup_logging()
console = Console()

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

def select_llm_provider():
    """
    Specific menu for choosing an AI provider.
    Now supports all 4 providers defined in src/providers.py
    """
    choice = questionary.select(
        "Select your Intelligence Provider:",
        choices=[
            "🛡️  Ollama (Local - Safe, Private, Free)",
            "☁️  OpenAI (Cloud - Public, Costs Tokens)",
            "☁️  XAI / Grok (Cloud - Public, Costs Tokens)",
            "☁️  Gemini (Cloud - Public, Costs Tokens)",
            questionary.Separator(),
            "🔙 Back"
        ]
    ).ask()

    # Map display label to internal ID used by providers.py
    if choice is None: return None
    if "Ollama" in choice: return "ollama"
    if "OpenAI" in choice: return "openai"
    if "XAI" in choice:    return "xai"
    if "Gemini" in choice: return "gemini"
    
    return None

def get_user_prompt():
    return questionary.text("Enter your prompt for the AI:").ask()

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
        console.print("   ⚙️  Extracting data...")
        data = fetch_repo_data(repo_path, filters)
        
        count = len(data)
        if count == 0:
            console.print("\n⚠️  No matching data found.")
            return

        # Output Handling
        filename = questionary.text("Output JSON filename:", default="raw_data.json").ask()
        target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, selected_sub_dir)
        full_output_path = os.path.join(target_dir, filename)

        if questionary.confirm(f"Save {count} items to:\n   📂 {full_output_path}").ask():
            success = save_data_to_file(data, full_output_path)
            if success:
                console.print(f"\n✅ Success! Saved to {full_output_path}", style="bold green")
            else:
                console.print("\n❌ Error saving file. Check logs.", style="bold red")
        else:
            console.print("Operation cancelled.")

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        logger.error("Raw extraction failed", exc_info=True)

def run_app():
    """Main Application Loop"""
    console.print("\n--- 🤖 Git-to-JSON Framework (v2.5) ---\n", style="bold blue")

    repo_path = get_repository_path()
    if not repo_path: return

    logger.info(f"Session started for: {repo_path}")
    console.print(f"Selected Repo: [green]{repo_path}[/green]")

    # 1. Load Templates
    templates = load_templates()
    
    # 2. Build Menu Choices
    choices = []
    
    if templates:
        choices.extend([t["meta"]["name"] for t in templates])
        choices.append(questionary.Separator()) 
    
    choices.append("🚀 Execute AI Prompt (Direct Mode)")
    choices.append("💾 Extract Raw Data (Classic Mode)")
    choices.append("❌ Exit")

    while True:
        selection_name = questionary.select(
            "What is your goal?",
            choices=choices
        ).ask()

        # --- BRANCH: EXIT ---
        if selection_name == "❌ Exit":
            console.print("Goodbye!", style="bold blue") # FIXED: Bug #5 (Consistent Exit)
            break
            
        # --- BRANCH: RAW DATA ---
        elif selection_name == "💾 Extract Raw Data (Classic Mode)":
            run_raw_extraction_mode(repo_path)

        # --- BRANCH: DIRECT EXECUTION ---
        elif selection_name == "🚀 Execute AI Prompt (Direct Mode)":
            provider = select_llm_provider()
            if provider:
                prompt = get_user_prompt()
                if prompt:
                    # Call engine's async runner (Blocking call)
                    run_llm_execution(provider, prompt)
            
        # --- BRANCH: TEMPLATE WORKFLOW ---
        else:
            # It's a template
            selected_template = next(t for t in templates if t["meta"]["name"] == selection_name)
            
            # 1. Run Engine to get Text (No auto-copy)
            prompt = run_template_workflow(repo_path, selected_template)
            
            if prompt:
                # 2. Show Output Menu
                output_option = questionary.select(
                    "How do you want to handle this prompt?",
                    choices=[
                        questionary.Choice("📋 Copy to Clipboard", value="clipboard"),
                        questionary.Choice("💾 Save to File", value="file"),
                        questionary.Separator(), 
                        questionary.Choice("🚀 Execute with AI Agent", value="execute"),
                        questionary.Separator(),
                        questionary.Choice("❌ Cancel", value="cancel")
                    ]
                ).ask()

                # FIXED: Bug #4 (UX - Cancel should loop back immediately)
                if output_option == "cancel" or output_option is None:
                    continue 

                # Option A: Clipboard
                if output_option == "clipboard":
                    # FIXED: Bug #3 (Clipboard crash protection)
                    try:
                        pyperclip.copy(prompt)
                        console.print("\n✅  Success! Prompt copied to clipboard.", style="bold green")
                    except Exception as e:
                        console.print(f"\n❌ Clipboard error: {e}", style="bold red")

                # Option B: File
                elif output_option == "file":
                    filename = questionary.text("Enter filename:", default="prompt.txt").ask()
                    if filename:
                        # FIXED: Bug #2 (File Save crash protection)
                        try:
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(prompt)
                            console.print(f"\n✅  Saved to {filename}", style="green")
                        except Exception as e:
                            console.print(f"\n❌ Error saving file: {e}", style="bold red")

                # Option C: Execute
                elif output_option == "execute":
                    # We must ask for the provider now
                    provider = select_llm_provider()
                    if provider:
                        console.print("\n🤖 [Agent] Initializing AI Execution...", style="bold purple")
                        # Pass the generated prompt to the engine
                        run_llm_execution(provider, prompt)

        if not questionary.confirm("Perform another action?").ask():
            console.print("Goodbye!", style="bold blue") # FIXED: Bug #5 (Consistent Exit)
            break

if __name__ == "__main__":
    run_app()