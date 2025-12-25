import pytest
from unittest.mock import MagicMock, patch
from src.engine import AuditEngine

# --- Fixtures ---


@pytest.fixture
def mock_console():
    return MagicMock()


@pytest.fixture
def audit_engine(mock_console):
    return AuditEngine(mock_console)


@pytest.fixture
def mock_template():
    template = MagicMock()
    template.meta.name = "Test Template"
    template.execution.source = "history"
    template.execution.limit = 1
    template.prompts.system = "System Prompt"
    template.prompts.user = "User Prompt {DIFF_CONTENT}"
    return template


@pytest.fixture
def mock_commit_data():
    commit = MagicMock()
    commit.diff = "diff_content"
    commit.message = "commit message"
    commit.hash = "abc1234"
    commit.short_hash = "abc1234"
    return commit


# --- Tests for AuditEngine ---


@patch("src.engine.fetch_repo_data")
def test_fetch_data(mock_fetch, audit_engine, mock_console):
    """Test fetching data via the engine."""
    mock_fetch.return_value = ["data"]

    result = audit_engine.fetch_data("/path", {"filter": "x"})

    mock_fetch.assert_called_with("/path", {"filter": "x"})
    assert result == ["data"]
    # Check that console printed the "Fetching" status
    assert any(
        "Fetching" in str(arg)
        for args, _ in mock_console.print.call_args_list
        for arg in args
    )


@patch("src.engine.fetch_repo_data")
def test_fetch_data_empty(mock_fetch, audit_engine, mock_console):
    """Test fetch data when no results found."""
    mock_fetch.return_value = []

    result = audit_engine.fetch_data("/path", {})

    assert result == []
    assert any(
        "No matching data" in str(arg)
        for args, _ in mock_console.print.call_args_list
        for arg in args
    )


def test_build_prompt(audit_engine, mock_template, mock_commit_data):
    """Test prompt construction via engine."""
    # We patch count_tokens internal to the engine module
    with patch("src.services.prompt_builder.count_tokens", return_value=100):
        result = audit_engine.build_prompt(mock_template, [mock_commit_data])

    assert "--- SYSTEM PROMPT ---\nSystem Prompt" in result
    assert "--- USER PROMPT ---\nUser Prompt diff_content" in result


@patch("src.engine.save_data_to_file")
@patch("src.engine.fetch_repo_data")
def test_execute_raw_extraction(mock_fetch, mock_save, audit_engine):
    """Test the raw extraction workflow."""
    mock_fetch.return_value = ["data"]
    mock_save.return_value = True

    success = audit_engine.execute_raw_extraction("/repo", {}, "out.json")

    assert success is True
    mock_fetch.assert_called()
    mock_save.assert_called_with(["data"], "out.json")


@patch("src.engine.asyncio.run")
def test_execute_ai_stream(mock_asyncio_run, audit_engine):
    """Test AI streaming workflow."""
    mock_asyncio_run.return_value = "Chunk 1Chunk 2"

    # Since execute_ai_stream runs asyncio.run internally, we can call it synchronously
    result = audit_engine.execute_ai_stream("openai", "prompt")

    assert result == "Chunk 1Chunk 2"
    mock_asyncio_run.assert_called_once()
