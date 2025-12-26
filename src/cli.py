import logging
from rich.console import Console
from src.utils import load_config, save_path_to_config, setup_logging
from src.template_loader import load_templates
from src.engine import AuditEngine
import src.tui as tui
from src.workflows import (
    TemplateWorkflowHandler,
    RawExtractionWorkflowHandler,
    InteractiveWorkflowHandler,
    DirectExecutionWorkflowHandler,
)


class App:
    def __init__(self):
        self.logger = setup_logging()
        self.console = Console()
        self.engine = AuditEngine(self.console)
        # For dependency injection into handlers
        self.tui = tui

    def _get_repository_path(self):
        """Gets the repository path from the user, utilizing saved paths."""
        config = load_config()
        saved_paths = config.get("saved_paths", [])
        path = self.tui.get_repository_path(saved_paths)

        if path and path not in saved_paths:
            save_path_to_config(path)

        return path

    def run(self):
        """Main application loop."""
        self.console.print(
            "\n--- 🤖 Git-to-JSON Framework (v3.2 Refactored) ---\n",
            style="bold blue",
        )

        repo_path = self._get_repository_path()
        if not repo_path:
            return

        self.logger.info(f"Session started for: {repo_path}")
        templates = load_templates()

        # Instantiate handlers with dependencies
        handlers = {
            "template": TemplateWorkflowHandler(self.engine, self.console, self.tui),
            "interactive": InteractiveWorkflowHandler(
                self.engine, self.console, self.tui
            ),
            "raw_extract": RawExtractionWorkflowHandler(
                self.engine, self.console, self.tui
            ),
            "direct_exec": DirectExecutionWorkflowHandler(
                self.engine, self.console, self.tui
            ),
        }

        while True:
            selection_name = self.tui.get_main_menu_choice(templates)

            try:
                if selection_name == "❌ Exit":
                    break
                elif selection_name == "🤝 Interactive Commit Selection":
                    handlers["interactive"].execute(repo_path)
                elif selection_name == "💾 Extract Raw Data (Classic Mode)":
                    handlers["raw_extract"].execute(repo_path)
                elif selection_name == "🚀 Execute AI Prompt (Direct Mode)":
                    # Direct execution doesn't need repo_path, but handler expects it
                    handlers["direct_exec"].execute(repo_path=".")
                else:
                    # This is a template workflow
                    handlers["template"].execute(
                        repo_path, templates=templates, selection_name=selection_name
                    )

            except Exception as e:
                self.console.print(f"\n❌ Application Error: {e}", style="bold red")
                self.logger.error("Top level error", exc_info=True)

            if not self.tui.confirm_another_action():
                break

        self.console.print("Goodbye!", style="bold blue")


def run_app():
    """DEPRECATED: Left for compatibility if old entry points exist."""
    logging.warning("run_app() is deprecated. Please use App().run()")
    app = App()
    app.run()


if __name__ == "__main__":
    app = App()
    app.run()
