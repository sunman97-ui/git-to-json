# src/tui.py

"""
Terminal User Interface (TUI) components for user interaction.
"""

import os
import questionary
from src.config import LLMSettings
from src.model_config import get_model_name

def get_repository_path(saved_paths):
    """Interactively asks user to select or input a repo path."""
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
            
    return selected_path

def select_llm_provider():
    """
    Specific menu for choosing an AI provider.
    Now supports all 4 providers defined in src/providers.py
    """
    settings = LLMSettings()

    # Get model names for display using your new function
    ollama_model = get_model_name("ollama", settings)
    openai_model = get_model_name("openai", settings)
    xai_model = get_model_name("xai", settings)
    gemini_model = get_model_name("gemini", settings)

    choice = questionary.select(
        "Select your Intelligence Provider:",
        choices=[
            f"🛡️  Ollama ({ollama_model}) (Local - Safe, Private, Free)",
            f"☁️  OpenAI ({openai_model}) (Cloud - Public, Costs Tokens)",
            f"☁️  XAI / Grok ({xai_model}) (Cloud - Public, Costs Tokens)",
            f"☁️  Gemini ({gemini_model}) (Cloud - Public, Costs Tokens)",
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

def get_raw_extraction_mode():
    """
    Restores the classic 'Extract to JSON' functionality.
    """
    # Menu Options
    OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
    OPT_ALL = "📜 All History"
    OPT_LIMIT = "🔢 Last N Commits"
    OPT_DATE = "📅 Date Range"
    OPT_AUTHOR = "👤 By Author"

    return questionary.select(
        "Raw Data Extraction: What filters?",
        choices=[OPT_STAGED, OPT_ALL, OPT_LIMIT, OPT_DATE, OPT_AUTHOR]
    ).ask()

def get_raw_extraction_filters(mode_selection):
    filters = {}
    if mode_selection == "📝 Staged Changes (Pre-Commit Analysis)":
        filters['mode'] = 'staged'
    elif mode_selection == "🔢 Last N Commits":
        filters['limit'] = questionary.text("How many commits?", validate=lambda t: t.isdigit()).ask()
    elif mode_selection == "📅 Date Range":
        filters['since'] = questionary.text("Start Date (YYYY-MM-DD):",).ask()
        filters['until'] = questionary.text("End Date (YYYY-MM-DD) [Optional]:",).ask()
        if filters['until'] == "": filters['until'] = None
    elif mode_selection == "👤 By Author":
        filters['author'] = questionary.text("Author Name:",).ask()
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
    
    choices.append("🚀 Execute AI Prompt (Direct Mode)")
    choices.append("💾 Extract Raw Data (Classic Mode)")
    choices.append("❌ Exit")
    
    return questionary.select(
        "What is your goal?",
        choices=choices
    ).ask()

def get_prompt_handling_choice():
    return questionary.select(
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

def get_prompt_filename():
    return questionary.text("Enter filename:", default="prompt.txt").ask()

def confirm_another_action():
    return questionary.confirm("Perform another action?").ask()
