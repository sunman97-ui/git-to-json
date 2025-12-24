import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.engine import generate_prompt_from_template, stream_llm_response, _build_prompt_from_data

# --- Mocks for Data Structures ---
# We mock these to avoid dependency on src.schemas/core availability during test execution

@pytest.fixture
def mock_template():
    """Creates a mock PromptTemplate object."""
    template = MagicMock()
    template.meta.name = "Test Template"
    template.execution.source = "history"
    template.execution.limit = 1
    template.prompts.system = "System Prompt"
    template.prompts.user = "User Prompt {DIFF_CONTENT}"
    return template

@pytest.fixture
def mock_commit_data():
    """Creates a mock CommitData object."""
    commit = MagicMock()
    commit.diff = "diff_content"
    commit.message = "commit message"
    commit.hash = "abc1234"
    return commit

# --- Tests for _build_prompt_from_data ---

def test_build_prompt_from_data_valid(mock_template, mock_commit_data):
    """Test that the prompt is correctly hydrated with diff data."""
    data = [mock_commit_data]
    
    with patch("src.engine.count_tokens", return_value=100) as mock_count:
        result = _build_prompt_from_data(mock_template, data)
    
    assert "--- SYSTEM PROMPT ---\nSystem Prompt" in result
    assert "--- USER PROMPT ---\nUser Prompt diff_content" in result
    mock_count.assert_called_once()

def test_build_prompt_from_data_empty(mock_template):
    """Test that empty data returns an empty string."""
    result = _build_prompt_from_data(mock_template, [])
    assert result == ""

# --- Tests for generate_prompt_from_template ---

@patch("src.engine.fetch_repo_data")
@patch("src.engine.console")  # Mock console to suppress output
def test_generate_prompt_success(mock_console, mock_fetch, mock_template, mock_commit_data):
    """Test the full flow of generating a prompt from a template."""
    mock_fetch.return_value = [mock_commit_data]
    
    with patch("src.engine.count_tokens", return_value=50):
        result = generate_prompt_from_template("repo/path", mock_template)
    
    assert result is not None
    assert "User Prompt diff_content" in result
    mock_fetch.assert_called_with("repo/path", {"mode": "history", "limit": 1})

@patch("src.engine.fetch_repo_data")
@patch("src.engine.console")
def test_generate_prompt_no_data(mock_console, mock_fetch, mock_template):
    """Test handling when no git data is found."""
    mock_fetch.return_value = []  # Empty list
    
    result = generate_prompt_from_template("repo/path", mock_template)
    
    assert result is None
    # Verify a warning was printed
    assert any("No data found" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)

@patch("src.engine.fetch_repo_data")
@patch("src.engine.console")
def test_generate_prompt_exception(mock_console, mock_fetch, mock_template):
    """Test handling of exceptions during data fetch."""
    mock_fetch.side_effect = Exception("Git failure")
    
    result = generate_prompt_from_template("repo/path", mock_template)
    
    assert result is None
    assert any("Error" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)

# --- Tests for stream_llm_response ---

@patch("src.engine.load_settings")
@patch("src.engine.get_provider")
@patch("src.engine.Live")  # Patch Live to prevent UI rendering
def test_stream_llm_response_success(mock_live, mock_get_provider, mock_load_settings):
    """Test successful streaming from a provider."""
    # Setup provider mock
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider
    
    # Setup async stream generator
    async def async_stream(prompt):
        yield "Part 1"
        yield "Part 2"
    mock_provider.stream_response = async_stream
    
    result = stream_llm_response("openai", "test prompt")
    
    assert result == "Part 1Part 2"
    mock_get_provider.assert_called_once()

@patch("src.engine.load_settings")
@patch("src.engine.get_provider")
@patch("src.engine.console")
def test_stream_llm_response_config_error(mock_console, mock_get_provider, mock_load_settings):
    """Test handling of configuration errors (e.g. missing keys)."""
    mock_get_provider.side_effect = ValueError("Missing Key")
    
    result = stream_llm_response("openai", "test prompt")
    
    assert result is None
    assert any("Configuration Error" in str(arg) for args, _ in mock_console.print.call_args_list for arg in args)