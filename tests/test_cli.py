import pytest
from unittest.mock import MagicMock, patch

# --- FIX: Added OPT_STAGED to imports ---
from src.cli import (
    get_repository_path,
    handle_raw_extraction,
    handle_direct_execution,
    handle_template_workflow,
    handle_interactive_workflow,
    run_app,
    OPT_STAGED,
)

# --- Tests for get_repository_path ---


@patch("src.cli.save_path_to_config")
@patch("src.cli.tui")
@patch("src.cli.load_config")
def test_get_repository_path_new(mock_load, mock_tui, mock_save):
    mock_load.return_value = {"saved_paths": []}
    mock_tui.get_repository_path.return_value = "/new/path"

    path = get_repository_path()

    assert path == "/new/path"
    mock_save.assert_called_once_with("/new/path")


# --- Tests for handle_raw_extraction ---


@patch("src.cli.engine")
@patch("src.cli.tui")
@patch("src.cli.console")
def test_handle_raw_extraction_success(mock_console, mock_tui, mock_engine):
    """Test that CLI delegates raw extraction to the engine."""
    # Setup CLI inputs
    mock_tui.get_raw_extraction_mode.return_value = OPT_STAGED
    mock_tui.get_raw_extraction_filters.return_value = {"mode": "staged"}
    mock_tui.get_output_filename.return_value = "out.json"
    mock_tui.confirm_save.return_value = True

    # Setup Engine response
    mock_engine.execute_raw_extraction.return_value = True

    handle_raw_extraction("/repo")

    # Verify Engine was called correctly
    mock_engine.execute_raw_extraction.assert_called()
    call_args = mock_engine.execute_raw_extraction.call_args
    assert call_args[0][0] == "/repo"
    assert call_args[0][1] == {"mode": "staged"}

    # Verify path mapping works correctly
    assert "Staged" in call_args[0][2]

    # IMPROVED ASSERTION: Iterate through calls to find the success message
    # We look for "Saved to" because that's what the actual code prints: "✅ Saved to {path}"  # noqa: E501
    found_success_msg = False
    for call_obj in mock_console.print.call_args_list:
        args, _ = call_obj
        if args and "Saved to" in str(args[0]):
            found_success_msg = True
            break

    assert (
        found_success_msg
    ), f"Success message not found. Console calls: {mock_console.print.call_args_list}"


@patch("src.cli.tui")
def test_handle_raw_extraction_cancel(mock_tui):
    mock_tui.get_raw_extraction_mode.return_value = None
    handle_raw_extraction("/repo")
    mock_tui.get_output_filename.assert_not_called()


# --- Tests for handle_direct_execution ---


@patch("src.cli.engine")
@patch("src.cli.tui")
def test_handle_direct_execution(mock_tui, mock_engine):
    """Test direct execution delegates to engine AI stream."""
    mock_tui.select_llm_provider.return_value = "openai"
    mock_tui.get_user_prompt.return_value = "hello"

    handle_direct_execution()

    mock_engine.execute_ai_stream.assert_called_with("openai", "hello")


# --- Tests for handle_template_workflow ---


@pytest.fixture
def mock_template_obj():
    tmpl = MagicMock()
    tmpl.meta.name = "Test Template"
    tmpl.execution.source = "history"
    tmpl.execution.limit = 5
    return tmpl


@patch("src.cli.engine")
@patch("src.cli.tui")
def test_handle_template_clipboard(mock_tui, mock_engine, mock_template_obj):
    """Test template flow -> clipboard."""
    # 1. Setup Data Fetch
    mock_engine.fetch_data.return_value = ["mock_data"]
    mock_engine.build_prompt.return_value = "The Prompt"

    # 2. Setup User Choice
    mock_tui.get_prompt_handling_choice.return_value = "clipboard"
    mock_engine.copy_to_clipboard.return_value = True

    handle_template_workflow("/repo", [mock_template_obj], "Test Template")

    # 3. Verify
    mock_engine.fetch_data.assert_called()
    mock_engine.build_prompt.assert_called()
    mock_engine.copy_to_clipboard.assert_called_with("The Prompt")


@patch("src.cli.engine")
@patch("src.cli.tui")
def test_handle_template_file(mock_tui, mock_engine, mock_template_obj):
    """Test template flow -> file save."""
    mock_engine.fetch_data.return_value = ["mock_data"]
    mock_engine.build_prompt.return_value = "The Prompt"

    mock_tui.get_prompt_handling_choice.return_value = "file"
    mock_tui.get_prompt_filename.return_value = "prompt.txt"
    mock_engine.save_prompt_to_file.return_value = True

    handle_template_workflow("/repo", [mock_template_obj], "Test Template")

    mock_engine.save_prompt_to_file.assert_called_with("The Prompt", "prompt.txt")


# --- Tests for handle_interactive_workflow ---


@patch("src.cli.engine")
@patch("src.cli.tui")
def test_handle_interactive_workflow_ai(mock_tui, mock_engine):
    """Test interactive selection -> AI execution."""
    mock_tui.select_commits_interactively.return_value = ["hash1"]
    mock_engine.fetch_data.return_value = ["data"]
    mock_tui.get_interactive_output_choice.return_value = "ai"
    mock_engine.build_prompt.return_value = "prompt"
    mock_tui.select_llm_provider.return_value = "openai"

    handle_interactive_workflow("/repo")

    mock_engine.fetch_data.assert_called_with(
        "/repo", {"mode": "hashes", "hashes": ["hash1"]}
    )
    mock_engine.build_prompt.assert_called()
    mock_engine.execute_ai_stream.assert_called_with("openai", "prompt")


@patch("src.cli.engine")
@patch("src.cli.tui")
def test_handle_interactive_workflow_extract(mock_tui, mock_engine):
    """Test interactive selection -> Extract to JSON."""
    mock_tui.select_commits_interactively.return_value = ["hash1"]
    mock_engine.fetch_data.return_value = ["data"]
    mock_tui.get_interactive_output_choice.return_value = "extract"
    mock_tui.get_output_filename.return_value = "out.json"
    mock_engine.execute_raw_extraction.return_value = True

    handle_interactive_workflow("/repo")

    mock_engine.execute_raw_extraction.assert_called()
    args = mock_engine.execute_raw_extraction.call_args[0]
    assert args[0] == "/repo"
    assert args[1] == {"mode": "hashes", "hashes": ["hash1"]}
    assert "Interactive" in args[2]


# --- Tests for run_app ---


@patch("src.cli.handle_raw_extraction")
@patch("src.cli.load_templates")
@patch("src.cli.tui")
@patch("src.cli.get_repository_path")
@patch("src.cli.console")
@patch("src.cli.load_config")
def test_run_app_flow(
    mock_cfg, mock_console, mock_get_repo, mock_tui, mock_load_tmpl, mock_raw
):
    mock_get_repo.return_value = "/repo"
    mock_load_tmpl.return_value = []

    mock_tui.get_main_menu_choice.side_effect = [
        "💾 Extract Raw Data (Classic Mode)",
        "❌ Exit",
    ]
    mock_tui.confirm_another_action.return_value = True

    run_app()

    mock_raw.assert_called_once()
