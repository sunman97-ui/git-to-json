import pytest
import os
from unittest.mock import MagicMock, patch, mock_open, call
from datetime import datetime

from src.cli import (
    get_repository_path,
    handle_raw_extraction,
    handle_direct_execution,
    handle_template_workflow,
    handle_interactive_workflow,
    run_app,
    OPT_STAGED,
    OUTPUT_ROOT_DIR
)
from src.schemas import CommitData, PromptTemplate


# --- Tests for get_repository_path ---

@patch("src.cli.save_path_to_config")
@patch("src.cli.tui")
@patch("src.cli.load_config")
def test_get_repository_path_new(mock_load, mock_tui, mock_save):
    """Test that a newly entered path is saved to config."""
    mock_load.return_value = {"saved_paths": []}
    mock_tui.get_repository_path.return_value = "/new/path"
    
    path = get_repository_path()
    
    assert path == "/new/path"
    mock_save.assert_called_once_with("/new/path")

@patch("src.cli.save_path_to_config")
@patch("src.cli.tui")
@patch("src.cli.load_config")
def test_get_repository_path_existing(mock_load, mock_tui, mock_save):
    """Test that selecting an existing path does not trigger a save."""
    mock_load.return_value = {"saved_paths": ["/existing/path"]}
    mock_tui.get_repository_path.return_value = "/existing/path"
    
    path = get_repository_path()
    
    assert path == "/existing/path"
    mock_save.assert_not_called()

# --- Tests for handle_raw_extraction ---

@patch("src.cli.save_data_to_file")
@patch("src.cli.tui")
@patch("src.cli.fetch_repo_data")
@patch("src.cli.console")
def test_handle_raw_extraction_success(mock_console, mock_fetch, mock_tui, mock_save):
    """Test the successful flow of raw data extraction."""
    # Setup mocks
    mock_tui.get_raw_extraction_mode.return_value = OPT_STAGED
    mock_tui.get_raw_extraction_filters.return_value = {"mode": "staged"}
    mock_fetch.return_value = ["mock_data_item"]
    mock_tui.get_output_filename.return_value = "out.json"
    mock_tui.confirm_save.return_value = True
    mock_save.return_value = True
    
    handle_raw_extraction("/repo")
    
    # Verify logic
    mock_fetch.assert_called_with("/repo", {"mode": "staged"})
    mock_save.assert_called()
    # Check that the correct subdirectory mapping was used
    args, _ = mock_save.call_args
    output_path = args[1]
    assert "Staged_Changes" in output_path
    assert "Success" in str(mock_console.print.call_args_list)

@patch("src.cli.tui")
def test_handle_raw_extraction_cancel_mode(mock_tui):
    """Test exiting if mode selection is cancelled."""
    mock_tui.get_raw_extraction_mode.return_value = None
    handle_raw_extraction("/repo")
    mock_tui.get_raw_extraction_filters.assert_not_called()

@patch("src.cli.console")
@patch("src.cli.fetch_repo_data")
@patch("src.cli.tui")
def test_handle_raw_extraction_no_data(mock_tui, mock_fetch, mock_console):
    """Test handling when fetch_repo_data returns empty."""
    mock_tui.get_raw_extraction_mode.return_value = OPT_STAGED
    mock_fetch.return_value = []
    
    handle_raw_extraction("/repo")
    
    mock_tui.get_output_filename.assert_not_called()
    assert any("No matching data" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)

# --- Tests for handle_direct_execution ---

@patch("src.cli.stream_llm_response")
@patch("src.cli.tui")
def test_handle_direct_execution_success(mock_tui, mock_stream):
    """Test direct execution flow."""
    mock_tui.select_llm_provider.return_value = "openai"
    mock_tui.get_user_prompt.return_value = "hello"
    
    handle_direct_execution()
    
    mock_stream.assert_called_with("openai", "hello")

@patch("src.cli.stream_llm_response")
@patch("src.cli.tui")
def test_handle_direct_execution_no_provider(mock_tui, mock_stream):
    """Test aborting if no provider is selected."""
    mock_tui.select_llm_provider.return_value = None
    
    handle_direct_execution()
    
    mock_tui.get_user_prompt.assert_not_called()
    mock_stream.assert_not_called()

# --- Tests for handle_template_workflow ---

@pytest.fixture
def mock_template_obj():
    tmpl = MagicMock()
    tmpl.meta.name = "Test Template"
    return tmpl

@patch("src.cli.pyperclip")
@patch("src.cli.tui")
@patch("src.cli.generate_prompt_from_template")
def test_handle_template_clipboard(mock_gen, mock_tui, mock_clip, mock_template_obj):
    """Test copying generated prompt to clipboard."""
    mock_gen.return_value = "The Prompt"
    mock_tui.get_prompt_handling_choice.return_value = "clipboard"
    
    handle_template_workflow("/repo", [mock_template_obj], "Test Template")
    
    mock_clip.copy.assert_called_with("The Prompt")

@patch("builtins.open", new_callable=mock_open)
@patch("src.cli.tui")
@patch("src.cli.generate_prompt_from_template")
def test_handle_template_file(mock_gen, mock_tui, mock_file, mock_template_obj):
    """Test saving generated prompt to file."""
    mock_gen.return_value = "The Prompt"
    mock_tui.get_prompt_handling_choice.return_value = "file"
    mock_tui.get_prompt_filename.return_value = "prompt.txt"
    
    handle_template_workflow("/repo", [mock_template_obj], "Test Template")
    
    mock_file.assert_called_with("prompt.txt", "w", encoding="utf-8")
    mock_file().write.assert_called_with("The Prompt")

# --- Tests for run_app (Main Loop) ---

@patch("src.cli.handle_template_workflow")
@patch("src.cli.handle_direct_execution")
@patch("src.cli.handle_raw_extraction")
@patch("src.cli.load_templates")
@patch("src.cli.tui")
@patch("src.cli.get_repository_path")
@patch("src.cli.console")
def test_run_app_flow(mock_console, mock_get_repo, mock_tui, mock_load_tmpl, mock_raw, mock_direct, mock_tmpl_flow):
    """Test the main application loop routing."""
    mock_get_repo.return_value = "/repo"
    mock_load_tmpl.return_value = ["tmpl1"]
    
    # Simulate user selecting Raw Extraction, then Direct Mode, then Exit
    mock_tui.get_main_menu_choice.side_effect = [
        "💾 Extract Raw Data (Classic Mode)",
        "🚀 Execute AI Prompt (Direct Mode)",
        "❌ Exit"
    ]
    # User confirms "Another Action?" once, then loop breaks on Exit anyway
    mock_tui.confirm_another_action.return_value = True
    
    run_app()
    
    mock_raw.assert_called_once()
    mock_direct.assert_called_once()
    # Template workflow should not be called in this sequence
    mock_tmpl_flow.assert_not_called()


# --- Mock fixtures ---

@pytest.fixture
def mock_commit_data_list():
    """Returns a list of mock CommitData objects."""
    c1 = MagicMock(spec=CommitData)
    c1.hash = "hash1"
    c1.short_hash = "h1"
    c1.author = "Author1"
    c1.date = datetime.now()
    c1.message = "Commit 1 message"
    c1.diff = "diff for commit 1"

    c2 = MagicMock(spec=CommitData)
    c2.hash = "hash2"
    c2.short_hash = "h2"
    c2.author = "Author2"
    c2.date = datetime.now()
    c2.message = "Commit 2 message"
    c2.diff = "diff for commit 2"
    
    return [c1, c2]

# --- Tests for handle_interactive_workflow ---

@patch("src.cli.stream_llm_response")
@patch("src.cli._build_prompt_from_data")
@patch("src.cli.tui")
@patch("src.cli.fetch_repo_data")
@patch("src.cli.console")
def test_handle_interactive_workflow_ai_path(
    mock_console, mock_fetch_repo_data, mock_tui, mock_build_prompt, mock_stream_llm,
    mock_commit_data_list
):
    """Test the AI execution path of the interactive workflow."""
    mock_tui.select_commits_interactively.return_value = ["hash1", "hash2"]
    mock_fetch_repo_data.return_value = mock_commit_data_list
    mock_tui.get_interactive_output_choice.return_value = "ai"
    mock_build_prompt.return_value = "Combined AI Prompt"
    mock_tui.select_llm_provider.return_value = "openai"

    handle_interactive_workflow("/repo")

    mock_tui.select_commits_interactively.assert_called_once_with("/repo")
    mock_fetch_repo_data.assert_called_once_with("/repo", {"mode": "hashes", "hashes": ["hash1", "hash2"]})
    mock_tui.get_interactive_output_choice.assert_called_once()
    mock_build_prompt.assert_called_once()
    mock_tui.select_llm_provider.assert_called_once()
    mock_stream_llm.assert_called_once_with("openai", "Combined AI Prompt")
    assert any("Initializing AI Execution" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)


@patch("src.cli.save_data_to_file")
@patch("src.cli.tui")
@patch("src.cli.fetch_repo_data")
@patch("src.cli.console")
def test_handle_interactive_workflow_extract_path(
    mock_console, mock_fetch_repo_data, mock_tui, mock_save_data,
    mock_commit_data_list
):
    """Test the extract to file path of the interactive workflow."""
    mock_tui.select_commits_interactively.return_value = ["hash1"]
    mock_fetch_repo_data.return_value = mock_commit_data_list
    mock_tui.get_interactive_output_choice.return_value = "extract"
    mock_tui.get_output_filename.return_value = "output.json"
    mock_tui.confirm_save.return_value = True
    mock_save_data.return_value = True
    
    handle_interactive_workflow("/repo")
    
    mock_tui.select_commits_interactively.assert_called_once_with("/repo")
    mock_fetch_repo_data.assert_called_once_with("/repo", {"mode": "hashes", "hashes": ["hash1"]})
    mock_tui.get_interactive_output_choice.assert_called_once()
    mock_tui.get_output_filename.assert_called_once_with(default_name="combined_commits.json")
    
    expected_target_dir = os.path.join(os.getcwd(), OUTPUT_ROOT_DIR, "Combined_Commits")
    expected_full_path = os.path.join(expected_target_dir, "output.json")
    
    mock_tui.confirm_save.assert_called_once_with(expected_full_path, len(mock_commit_data_list))
    mock_save_data.assert_called_once_with(mock_commit_data_list, expected_full_path)
    assert any("Success" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)

@patch("src.cli.tui")
@patch("src.cli.fetch_repo_data")
@patch("src.cli.console")
def test_handle_interactive_workflow_no_selection(mock_console, mock_fetch_repo_data, mock_tui):
    """Test handling when no commits are selected interactively."""
    mock_tui.select_commits_interactively.return_value = []
    
    handle_interactive_workflow("/repo")
    
    mock_tui.select_commits_interactively.assert_called_once_with("/repo")
    mock_fetch_repo_data.assert_not_called()
    assert any("No commits selected" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)

@patch("src.cli.handle_interactive_workflow")
@patch("src.cli.handle_template_workflow")
@patch("src.cli.handle_direct_execution")
@patch("src.cli.handle_raw_extraction")
@patch("src.cli.load_templates")
@patch("src.cli.tui")
@patch("src.cli.get_repository_path")
@patch("src.cli.console")
def test_run_app_interactive_route(
    mock_console, mock_get_repo, mock_tui, mock_load_tmpl, 
    mock_raw, mock_direct, mock_tmpl_flow, mock_interactive_flow
):
    """Test that the main app loop correctly routes to interactive workflow."""
    mock_get_repo.return_value = "/repo"
    mock_load_tmpl.return_value = ["tmpl1"]
    
    mock_tui.get_main_menu_choice.side_effect = [
        "🤝 Interactive Commit Selection",
        "❌ Exit"
    ]
    mock_tui.confirm_another_action.return_value = True # Not called for exit
    
    run_app()
    
    mock_interactive_flow.assert_called_once_with("/repo")
    mock_raw.assert_not_called()
    mock_direct.assert_not_called()
    mock_tmpl_flow.assert_not_called()