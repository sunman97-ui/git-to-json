import pytest
from unittest.mock import patch, MagicMock

from src.cli import App
from src.workflows import (
    TemplateWorkflowHandler,
    RawExtractionWorkflowHandler,
    InteractiveWorkflowHandler,
    DirectExecutionWorkflowHandler,
)


@pytest.fixture
def app():
    """Fixture to provide a fresh App instance for each test."""
    return App()


# --- Tests for App._get_repository_path ---


def test_get_repository_path_new(app, mocker):
    """Test that _get_repository_path saves a new path."""
    mock_save = mocker.patch("src.cli.save_path_to_config")
    mock_load = mocker.patch("src.cli.load_config", return_value={"saved_paths": []})
    mock_get_repo = mocker.patch(
        "src.tui.get_repository_path", return_value="/new/path"
    )

    path = app._get_repository_path()

    assert path == "/new/path"
    mock_load.assert_called_once()
    mock_get_repo.assert_called_once_with([])  # Expects to be called with empty list
    mock_save.assert_called_once_with("/new/path")


# --- Tests for Workflow Handlers via App.run ---


def test_run_app_flow_raw_extraction(app, mocker):
    """Test App.run calls the correct handler for raw extraction."""
    mocker.patch.object(app, "_get_repository_path", return_value="/repo")
    mock_tui = mocker.patch.object(app, "tui")
    mock_tui.get_main_menu_choice.side_effect = [
        "💾 Extract Raw Data (Classic Mode)",
        "❌ Exit",
    ]
    mock_tui.confirm_another_action.return_value = False  # End loop after one action

    # Mock the handler itself to prevent its execution, just check if it's called
    mock_handler = mocker.patch.object(
        RawExtractionWorkflowHandler, "execute", return_value=None
    )

    app.run()

    mock_handler.assert_called_once_with("/repo")


def test_run_app_flow_interactive(app, mocker):
    """Test App.run calls the correct handler for interactive mode."""
    mocker.patch.object(app, "_get_repository_path", return_value="/repo")
    mock_tui = mocker.patch.object(app, "tui")
    mock_tui.get_main_menu_choice.side_effect = [
        "🤝 Interactive Commit Selection",
        "❌ Exit",
    ]
    mock_tui.confirm_another_action.return_value = False

    mock_handler = mocker.patch.object(
        InteractiveWorkflowHandler, "execute", return_value=None
    )

    app.run()

    mock_handler.assert_called_once_with("/repo")


def test_run_app_flow_direct_execution(app, mocker):
    """Test App.run calls the correct handler for direct execution."""
    mocker.patch.object(app, "_get_repository_path", return_value="/repo")
    mock_tui = mocker.patch.object(app, "tui")
    mock_tui.get_main_menu_choice.side_effect = [
        "🚀 Execute AI Prompt (Direct Mode)",
        "❌ Exit",
    ]
    mock_tui.confirm_another_action.return_value = False

    mock_handler = mocker.patch.object(
        DirectExecutionWorkflowHandler, "execute", return_value=None
    )

    app.run()

    mock_handler.assert_called_once_with(repo_path=".")


def test_run_app_flow_template(app, mocker):
    """Test App.run calls the correct handler for a template."""
    mock_template = MagicMock()
    mock_template.meta.name = "My Template"

    mocker.patch.object(app, "_get_repository_path", return_value="/repo")
    mocker.patch("src.cli.load_templates", return_value=[mock_template])
    mock_tui = mocker.patch.object(app, "tui")
    mock_tui.get_main_menu_choice.side_effect = ["My Template", "❌ Exit"]
    mock_tui.confirm_another_action.return_value = False

    mock_handler = mocker.patch.object(
        TemplateWorkflowHandler, "execute", return_value=None
    )

    app.run()

    mock_handler.assert_called_once_with(
        "/repo", templates=[mock_template], selection_name="My Template"
    )


def test_app_run_exit_immediately(app, mocker):
    """Test that the app exits cleanly if the user chooses to."""
    mocker.patch.object(app, "_get_repository_path", return_value="/repo")
    mock_tui = mocker.patch.object(app, "tui")
    mock_tui.get_main_menu_choice.return_value = "❌ Exit"

    # Patch the handler to ensure it's NOT called
    mock_handler = mocker.patch.object(RawExtractionWorkflowHandler, "execute")

    app.run()

    mock_handler.assert_not_called()
    mock_tui.confirm_another_action.assert_not_called()
