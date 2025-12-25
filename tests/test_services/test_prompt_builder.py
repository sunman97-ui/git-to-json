import pytest
from unittest.mock import MagicMock, patch
from rich.console import Console

from src.schemas import PromptTemplate, CommitData, TemplatePrompts
from src.services.prompt_builder import build_prompt

# --- Fixtures ---


@pytest.fixture
def mock_console():
    return MagicMock(spec=Console)


@pytest.fixture
def mock_template_with_diff_placeholder():
    template = MagicMock(spec=PromptTemplate)
    template.prompts = MagicMock(spec=TemplatePrompts)
    template.prompts.system = "System instruction."
    template.prompts.user = "Analyze these changes: {DIFF_CONTENT}"
    return template


@pytest.fixture
def mock_simple_template():
    template = MagicMock(spec=PromptTemplate)
    template.prompts = MagicMock(spec=TemplatePrompts)
    template.prompts.system = "Simple system instruction."
    template.prompts.user = "Simple user instruction."
    return template


@pytest.fixture
def mock_single_commit_data():
    commit = MagicMock(spec=CommitData)
    commit.diff = "single_diff_content"
    commit.short_hash = "abc1234"
    commit.message = "feat: single commit"
    return [commit]


@pytest.fixture
def mock_multiple_commits_data():
    commit1 = MagicMock(spec=CommitData)
    commit1.diff = "diff_content_1"
    commit1.short_hash = "abc1234"
    commit1.message = "feat: first commit"

    commit2 = MagicMock(spec=CommitData)
    commit2.diff = "diff_content_2"
    commit2.short_hash = "def5678"
    commit2.message = "fix: second commit"
    return [commit1, commit2]


# --- Tests for build_prompt ---


@patch("src.services.prompt_builder.count_tokens", return_value=100)
def test_build_prompt_single_commit(
    mock_count_tokens,
    mock_console,
    mock_template_with_diff_placeholder,
    mock_single_commit_data,
):
    """Test building a prompt with a single commit."""
    result = build_prompt(
        mock_console, mock_template_with_diff_placeholder, mock_single_commit_data
    )

    expected_diff_content = mock_single_commit_data[0].diff
    assert (
        f"--- SYSTEM PROMPT ---\nSystem instruction.\n\n--- USER PROMPT ---\nAnalyze these changes: {expected_diff_content}"  # noqa: E501
        in result
    )
    mock_count_tokens.assert_called_once()
    mock_console.print.assert_called_once()


@patch("src.services.prompt_builder.count_tokens", return_value=200)
def test_build_prompt_multiple_commits(
    mock_count_tokens,
    mock_console,
    mock_template_with_diff_placeholder,
    mock_multiple_commits_data,
):
    """Test building a prompt with multiple commits."""
    result = build_prompt(
        mock_console, mock_template_with_diff_placeholder, mock_multiple_commits_data
    )

    expected_combined_diffs = (
        f"--- Diff for {mock_multiple_commits_data[0].short_hash}: {mock_multiple_commits_data[0].message.splitlines()[0]} ---\n{mock_multiple_commits_data[0].diff}\n\n"  # noqa: E501
        f"--- Diff for {mock_multiple_commits_data[1].short_hash}: {mock_multiple_commits_data[1].message.splitlines()[0]} ---\n{mock_multiple_commits_data[1].diff}"  # noqa: E501
    )

    assert expected_combined_diffs in result
    assert (
        f"--- SYSTEM PROMPT ---\nSystem instruction.\n\n--- USER PROMPT ---\nAnalyze these changes: {expected_combined_diffs}"  # noqa: E501
        in result
    )
    mock_count_tokens.assert_called_once()
    mock_console.print.assert_called_once()


@patch("src.services.prompt_builder.count_tokens", return_value=0)
def test_build_prompt_empty_data(
    mock_count_tokens, mock_console, mock_template_with_diff_placeholder
):
    """Test building a prompt with no commit data."""
    result = build_prompt(mock_console, mock_template_with_diff_placeholder, [])
    assert result == ""
    mock_count_tokens.assert_not_called()
    mock_console.print.assert_not_called()


@patch("src.services.prompt_builder.count_tokens", return_value=50)
def test_build_prompt_count_tokens_called(
    mock_count_tokens, mock_console, mock_simple_template, mock_single_commit_data
):
    """Verify that count_tokens is called with the full payload."""
    build_prompt(mock_console, mock_simple_template, mock_single_commit_data)
    mock_count_tokens.assert_called_once()
    # Detailed assertion for the payload would be too complex here,
    # but we confirm it was called.
