import pytest
from unittest.mock import patch, MagicMock
from src.engine import run_template_workflow, run_llm_execution

# --- Fixtures ---

@pytest.fixture
def sample_template():
    return {
        "execution": {"source": "staged"},
        "prompts": {
            "system": "System Prompt",
            "user": "User Prompt with {DIFF_CONTENT}"
        }
    }

# --- Helper for Async Mocking ---

async def mock_stream_generator(prompt):
    """Simulates an async stream of text chunks."""
    yield "Chunk 1"
    yield "Chunk 2"

# --- Tests for run_template_workflow ---

@patch("src.engine.fetch_repo_data")
@patch("src.engine.count_tokens")
@patch("src.engine.console")
def test_run_template_workflow_success(mock_console, mock_count, mock_fetch, sample_template):
    """Test that the workflow correctly fetches data and builds the prompt."""
    # ARRANGE
    mock_fetch.return_value = [{"diff": "print('hello')"}]
    mock_count.return_value = 100
    repo_path = "/tmp/repo"

    # ACT
    result = run_template_workflow(repo_path, sample_template)

    # ASSERT
    expected_result = (
        "--- SYSTEM PROMPT ---\nSystem Prompt\n\n"
        "--- USER PROMPT ---\nUser Prompt with print('hello')"
    )
    assert result == expected_result
    
    # Verify correct calls
    mock_fetch.assert_called_once_with(repo_path, {"mode": "staged"})
    mock_console.print.assert_called()  # Should print status messages

@patch("src.engine.fetch_repo_data")
@patch("src.engine.console")
def test_run_template_workflow_no_data(mock_console, mock_fetch, sample_template):
    """Test behavior when fetch_repo_data returns empty."""
    # ARRANGE
    mock_fetch.return_value = []
    repo_path = "/tmp/repo"

    # ACT
    result = run_template_workflow(repo_path, sample_template)

    # ASSERT
    assert result is None
    # Ensure we logged/printed a warning (checking call args roughly)
    assert any("No data found" in str(args) for args in mock_console.print.call_args_list)

# --- Tests for run_llm_execution ---

@patch("src.engine.load_settings")
@patch("src.engine.get_provider")
@patch("src.engine.Live")
@patch("src.engine.console")
def test_run_llm_execution_success(mock_console, mock_live, mock_get_provider, mock_load_settings):
    """Test the async execution wrapper."""
    # ARRANGE
    mock_settings = MagicMock()
    mock_load_settings.return_value = mock_settings
    
    # Mock the provider to return our async generator
    mock_provider = MagicMock()
    mock_provider.stream_response = mock_stream_generator
    mock_get_provider.return_value = mock_provider

    # ACT
    # This runs the async loop internally
    result = run_llm_execution("openai", "test prompt")

    # ASSERT
    assert result == "Chunk 1Chunk 2"
    mock_get_provider.assert_called_once_with("openai", mock_settings)
    mock_live.assert_called()  # Ensure the UI component was activated

@patch("src.engine.load_settings")
@patch("src.engine.get_provider")
@patch("src.engine.console")
def test_run_llm_execution_config_error(mock_console, mock_get_provider, mock_load_settings):
    """Test that configuration errors are caught and handled gracefully."""
    # ARRANGE
    mock_get_provider.side_effect = ValueError("Missing API Key")

    # ACT
    result = run_llm_execution("openai", "prompt")

    # ASSERT
    assert result is None  # Should return None on error
    assert any("Configuration Error" in str(args) for args in mock_console.print.call_args_list)

@patch("src.engine.load_settings")
@patch("src.engine.get_provider")
@patch("src.engine.console")
@patch("src.engine.logger")
def test_run_llm_execution_generic_error(mock_logger, mock_console, mock_get_provider, mock_load_settings):
    """Test that generic exceptions are caught and logged."""
    # ARRANGE
    # Simulate a crash that is NOT a ValueError (e.g. Network Error)
    mock_get_provider.side_effect = Exception("Unexpected Network Crash")

    # ACT
    result = run_llm_execution("openai", "prompt")

    # ASSERT
    assert result is None
    mock_logger.error.assert_called() # Verify we logged the stack trace
    assert any("Connection Error" in str(args) for args in mock_console.print.call_args_list)