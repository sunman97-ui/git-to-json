# src/tui.py

"""
Terminal User Interface (TUI) components for user interaction.
"""

import os
import questionary
from src.core import get_commits_for_display
from src.config import LLMSettings
from src.model_config import ModelConfigManager

# --- IMPORTED CONSTANTS (Refactored) ---
from src.constants import OPT_STAGED, OPT_ALL, OPT_LIMIT, OPT_DATE, OPT_AUTHOR


def get_repository_path(saved_paths):
    """Interactively asks user to select or input a repo path."""
    selected_path = None

    if saved_paths:
        choices = saved_paths + ["-- Enter a New Path --"]
        choice = questionary.select("Select a repository:", choices=choices).ask()

        if choice != "-- Enter a New Path --":
            # --- FIX START: Validate existence of saved path ---
            if os.path.exists(choice) and os.path.isdir(choice):
                selected_path = choice
            else:
                print(
                    f"\n⚠️  The path '{choice}' no longer exists. Please select another."
                )

    if not selected_path:
        selected_path = questionary.path(
            "Enter path to local git repository:",
            default=".",
            only_directories=True,
            validate=lambda p: os.path.exists(p.strip("\"'"))
            and os.path.isdir(p.strip("\"'"))
            or "Directory not found.",
        ).ask()
        if selected_path:
            selected_path = selected_path.strip("\"'")

    return selected_path


def select_commits_interactively(repo_path: str) -> list[str] | None:
    """
    Displays an interactive checklist for the user to select commits.
    Returns a list of selected commit hashes.
    """
    try:
        commits = get_commits_for_display(
            repo_path, limit=50
        )  # Fetch more commits for selection
        if not commits:
            print("No commits found to display.")
            return None

        # Format choices for questionary
        choices = []
        for commit in commits:
            # Truncate message and file list for cleaner display
            msg_short = (
                (commit["message"][:60] + "..")
                if len(commit["message"]) > 60
                else commit["message"]
            )
            files_str = ", ".join(commit["files"][:3])
            if len(commit["files"]) > 3:
                files_str += f" (+{len(commit['files']) - 3} more)"

            display_text = (
                f"{commit['short_hash']} | {commit['date']} | {commit['author']}: "
                f"{msg_short} | Files: [{files_str or 'None'}]"
            )
            choices.append(questionary.Choice(title=display_text, value=commit["hash"]))

        if not choices:
            print("No processable commits found.")
            return None

        selected_hashes = questionary.checkbox(
            "Select commits (space to toggle, enter to confirm):",
            choices=choices,
            pointer="➡️",
        ).ask()

        return selected_hashes

    except Exception as e:
        print(f"\n❌ Error during interactive commit selection: {e}")
        return None


def select_llm_provider():
    """
    Specific menu for choosing an AI provider.
    Now supports all 4 providers defined in src/providers.py
    """
    settings = LLMSettings()

    # Get model names for display using your new function
    ollama_model = ModelConfigManager.get_model_name("ollama", settings)
    openai_model = ModelConfigManager.get_model_name("openai", settings)
    xai_model = ModelConfigManager.get_model_name("xai", settings)
    gemini_model = ModelConfigManager.get_model_name("gemini", settings)

    choice = questionary.select(
        "Select your Intelligence Provider:",
        choices=[
            f"🛡️  Ollama ({ollama_model}) (Local - Safe, Private, Free)",
            f"☁️  OpenAI ({openai_model}) (Cloud - Public, Costs Tokens)",
            f"☁️  XAI / Grok ({xai_model}) (Cloud - Public, Costs Tokens)",
            f"☁️  Gemini ({gemini_model}) (Cloud - Public, Costs Tokens)",
            questionary.Separator(),
            "🔙 Back",
        ],
    ).ask()

    # Map display label to internal ID used by providers.py
    if choice is None:
        return None
    if "Ollama" in choice:
        return "ollama"
    if "OpenAI" in choice:
        return "openai"
    if "XAI" in choice:
        return "xai"
    if "Gemini" in choice:
        return "gemini"

    return None


def get_user_prompt():
    return questionary.text("Enter your prompt for the AI:").ask()


def get_raw_extraction_mode():
    """
    Restores the classic 'Extract to JSON' functionality.
    Now uses constants to ensure matching logic in CLI.
    """
    return questionary.select(
        "Raw Data Extraction: What filters?",
        choices=[OPT_STAGED, OPT_ALL, OPT_LIMIT, OPT_DATE, OPT_AUTHOR],
    ).ask()


def get_raw_extraction_filters(mode_selection):
    filters = {}
    if mode_selection == OPT_STAGED:
        filters["mode"] = "staged"
    elif mode_selection == OPT_LIMIT:
        filters["limit"] = questionary.text(
            "How many commits?", validate=lambda t: t.isdigit()
        ).ask()
    elif mode_selection == OPT_DATE:
        # --- Use a named function instead of assigning a lambda ---
        def validate_date(text):
            if len(text) == 0:
                return True
            # Simple check for YYYY-MM-DD format
            return True if len(text.split("-")) == 3 else "Format must be YYYY-MM-DD"

        filters["since"] = questionary.text(
            "Start Date (YYYY-MM-DD):", validate=validate_date
        ).ask()
        filters["until"] = questionary.text(
            "End Date (YYYY-MM-DD) [Optional]:", validate=validate_date
        ).ask()

        if filters["until"] == "":
            filters["until"] = None
    elif mode_selection == OPT_AUTHOR:
        filters["author"] = questionary.text(
            "Author Name:",
        ).ask()
    return filters


def get_output_filename(default_name="raw_data.json"):
    return questionary.text("Output JSON filename:", default=default_name).ask()


def confirm_save(file_path, count):
    return questionary.confirm(f"Save {count} items to:\n   📂 {file_path}").ask()


def get_main_menu_choice(templates):
    choices = []
    if templates:
        choices.extend([t.meta.name for t in templates])
        choices.append(questionary.Separator())

    choices.append("🤝 Interactive Commit Selection")
    choices.append("🚀 Execute AI Prompt (Direct Mode)")
    choices.append("💾 Extract Raw Data (Classic Mode)")
    choices.append("❌ Exit")

    return questionary.select("What is your goal?", choices=choices).ask()


def get_prompt_handling_choice():
    return questionary.select(
        "How do you want to handle this prompt?",
        choices=[
            questionary.Choice("📋 Copy to Clipboard", value="clipboard"),
            questionary.Choice("💾 Save to File", value="file"),
            questionary.Separator(),
            questionary.Choice("🚀 Execute with AI Agent", value="execute"),
            questionary.Separator(),
            questionary.Choice("❌ Cancel", value="cancel"),
        ],
    ).ask()


def get_prompt_filename():
    return questionary.text("Enter filename:", default="prompt.txt").ask()


def confirm_another_action():
    return questionary.confirm("Perform another action?").ask()


def get_interactive_output_choice():
    """Asks user how to handle the data from interactive selection."""
    return questionary.select(
        "How do you want to process the selected commits?",
        choices=[
            questionary.Choice("🚀 Execute with AI", value="ai"),
            questionary.Choice("💾 Save Combined JSON to File", value="extract"),
            questionary.Separator(),
            questionary.Choice("❌ Cancel", value="cancel"),
        ],
    ).ask()
