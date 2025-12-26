# src/workflows.py
import os
from abc import ABC, abstractmethod
from rich.console import Console

from src.engine import AuditEngine
from src.schemas import PromptTemplate, TemplateMeta, TemplateExecution, TemplatePrompts

# --- CONSTANTS from cli.py ---
OUTPUT_ROOT_DIR = "Extracted JSON"
OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
OPT_ALL = "📜 All History"
OPT_LIMIT = "🔢 Last N Commits"
OPT_DATE = "📅 Date Range"
OPT_AUTHOR = "👤 By Author"


def resolve_output_path(filename: str, subfolder: str = "General") -> str:
    """Standardizes where files are saved."""
    target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, filename)


class WorkflowHandler(ABC):
    """Abstract base class for all workflow handlers."""

    def __init__(self, engine: AuditEngine, console: Console, tui_module):
        self.engine = engine
        self.console = console
        self.tui = tui_module

    @abstractmethod
    def execute(self, repo_path: str, **kwargs):
        """Execute the specific workflow."""
        pass


class TemplateWorkflowHandler(WorkflowHandler):
    def execute(self, repo_path: str, **kwargs):
        templates = kwargs.get("templates", [])
        selection_name = kwargs.get("selection_name")

        selected_template = next(
            (t for t in templates if t.meta.name == selection_name), None
        )
        if not selected_template:
            return

        filters = {"mode": selected_template.execution.source}
        if filters["mode"] == "history":
            filters["limit"] = selected_template.execution.limit

        data = self.engine.fetch_data(repo_path, filters)
        if not data:
            return

        prompt = self.engine.build_prompt(selected_template, data)

        action = self.tui.get_prompt_handling_choice()

        if action == "clipboard":
            if self.engine.copy_to_clipboard(prompt):
                self.console.print(
                    "\n✅ Prompt copied to clipboard.", style="bold green"
                )
        elif action == "file":
            filename = self.tui.get_prompt_filename()
            if filename and self.engine.save_prompt_to_file(prompt, filename):
                self.console.print(f"\n✅ Saved to {filename}", style="green")
        elif action == "execute":
            provider = self.tui.select_llm_provider()
            if provider:
                self.engine.execute_ai_stream(provider, prompt)


class RawExtractionWorkflowHandler(WorkflowHandler):
    def execute(self, repo_path: str, **kwargs):
        mode_selection = self.tui.get_raw_extraction_mode()
        if not mode_selection:
            return

        filters = self.tui.get_raw_extraction_filters(mode_selection)
        filename = self.tui.get_output_filename()
        if not filename:
            return

        dir_mapping = {
            OPT_STAGED: "Staged_Changes",
            OPT_ALL: "All_History",
            OPT_LIMIT: "Last_N_Commits",
            OPT_DATE: "Date_Range",
            OPT_AUTHOR: "By_Author",
        }
        folder_name = dir_mapping.get(mode_selection, "Raw_Data")
        full_path = resolve_output_path(filename, folder_name)

        if self.tui.confirm_save(full_path, "matching items"):
            success = self.engine.execute_raw_extraction(repo_path, filters, full_path)
            if success:
                self.console.print(f"\n✅ Saved to {full_path}", style="bold green")


class InteractiveWorkflowHandler(WorkflowHandler):
    def execute(self, repo_path: str, **kwargs):
        self.console.print(
            "\n[bold cyan]-- Interactive Commit Selection --[/bold cyan]"
        )
        selected_hashes = self.tui.select_commits_interactively(repo_path)
        if not selected_hashes:
            return

        self.console.print(
            f"   ⚙️  Hydrating {len(selected_hashes)} selected commits..."
        )
        data = self.engine.fetch_data(
            repo_path, {"mode": "hashes", "hashes": selected_hashes}
        )
        if not data:
            return

        output_choice = self.tui.get_interactive_output_choice()

        if output_choice == "extract":
            filename = self.tui.get_output_filename(
                default_name="combined_commits.json"
            )
            if filename:
                full_path = resolve_output_path(filename, "Interactive")
                if self.engine.execute_raw_extraction(
                    repo_path, {"mode": "hashes", "hashes": selected_hashes}, full_path
                ):
                    self.console.print(f"\n✅ Saved to {full_path}", style="bold green")
        elif output_choice == "ai":
            generic_template = PromptTemplate(
                meta=TemplateMeta(name="Interactive", description="Ad-hoc analysis"),
                execution=TemplateExecution(source="history"),
                prompts=TemplatePrompts(
                    system="You are a senior software engineer.",
                    user="Analyze these specific commits:\n\n{DIFF_CONTENT}",
                ),
            )
            prompt = self.engine.build_prompt(generic_template, data)
            provider = self.tui.select_llm_provider()
            if provider:
                self.engine.execute_ai_stream(provider, prompt)


class DirectExecutionWorkflowHandler(WorkflowHandler):
    def execute(self, repo_path: str, **kwargs):
        provider = self.tui.select_llm_provider()
        if provider:
            prompt = self.tui.get_user_prompt()
            if prompt:
                # Direct execution doesn't inherently need a repo path, but the interface requires it.
                # We can ignore it here.
                self.engine.execute_ai_stream(provider, prompt)
