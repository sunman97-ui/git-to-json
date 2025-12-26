import pytest
from unittest.mock import MagicMock, patch
from src.tui import (
    select_commits_interactively,
    get_interactive_output_choice,
    get_main_menu_choice,
)

# --- Mocks for common tui elements ---


@pytest.fixture
def mock_questionary_select():
    with patch("questionary.select") as mock:
        yield mock


@pytest.fixture
def mock_questionary_checkbox():
    with patch("questionary.checkbox") as mock:
        yield mock


# --- Tests for select_commits_interactively ---


@patch("src.tui.get_commits_for_display")
def test_select_commits_interactively_success(
    mock_get_commits, mock_questionary_checkbox
):
    """Test successful interactive commit selection."""
    mock_get_commits.return_value = [
        {
            "hash": "hash1",
            "short_hash": "abc",
            "date": "2023-01-01",
            "author": "Author1",
            "message": "Msg1",
            "files": ["f1"],
        },
        {
            "hash": "hash2",
            "short_hash": "def",
            "date": "2023-01-02",
            "author": "Author2",
            "message": "Msg2",
            "files": ["f2", "f3"],
        },
    ]
    mock_questionary_checkbox.return_value.ask.return_value = ["hash1"]

    selected = select_commits_interactively("/repo")

    assert selected == ["hash1"]
    mock_questionary_checkbox.assert_called_once()
    # Check that choices were formatted correctly
    _, kwargs = mock_questionary_checkbox.call_args
    choices = kwargs["choices"]
    assert "abc | 2023-01-01 | Author1: Msg1 | Files: [f1]" in choices[0].title


@patch("src.tui.get_commits_for_display")
def test_select_commits_interactively_no_commits(mock_get_commits):
    """Test when no commits are found for display."""
    mock_get_commits.return_value = []

    with patch("builtins.print") as mock_print:
        selected = select_commits_interactively("/repo")

        assert selected is None
        mock_print.assert_called_with("No commits found to display.")


# --- Tests for get_interactive_output_choice ---


def test_get_interactive_output_choice_ai(mock_questionary_select):
    """Test returning 'ai' choice."""
    mock_questionary_select.return_value.ask.return_value = "ai"
    result = get_interactive_output_choice()
    assert result == "ai"


def test_get_interactive_output_choice_extract(mock_questionary_select):
    """Test returning 'extract' choice."""
    mock_questionary_select.return_value.ask.return_value = "extract"
    result = get_interactive_output_choice()
    assert result == "extract"


# --- Tests for get_main_menu_choice (integration for new option) ---


def test_get_main_menu_choice_interactive_option(mock_questionary_select):
    """Test that 'Interactive Commit Selection' is present in main menu choices."""
    mock_template = MagicMock()
    mock_template.meta.name = "Template 1"

    # We don't care about the return value for this test, just the options presented
    mock_questionary_select.return_value.ask.return_value = None

    get_main_menu_choice([mock_template])

    _, kwargs = mock_questionary_select.call_args
    choices = kwargs["choices"]

    # Check that the new option is present
    assert "🤝 Interactive Commit Selection" in choices
    # Check order (templates, then Interactive, then others)
    assert choices.index("🤝 Interactive Commit Selection") > choices.index(
        mock_template.meta.name
    )
    assert choices.index("🤝 Interactive Commit Selection") < choices.index(
        "🚀 Execute AI Prompt (Direct Mode)"
    )
