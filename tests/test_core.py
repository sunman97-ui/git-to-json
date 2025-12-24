import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.core import fetch_repo_data

# --- Mocks ---

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    return repo

@pytest.fixture
def mock_commit():
    commit = MagicMock()
    commit.hexsha = "1234567890abcdef"
    commit.author.name = "Test Author"
    commit.committed_date = 1700000000
    commit.message = "Test Commit Message"
    # Mock diffs
    diff_item = MagicMock()
    diff_item.a_path = "file.txt"
    diff_item.diff = b"diff content"
    commit.diff.return_value = [diff_item]
    return commit

# --- Tests ---

@patch("src.core.git.Repo")
def test_fetch_staged_mode(mock_repo_cls, mock_repo):
    """Test fetching staged changes."""
    mock_repo_cls.return_value = mock_repo
    
    # Setup staged diff mock
    # MagicMocks are truthy by default, so bool(mock.new_file) is True.
    # We must explicitly set them to False to avoid entering the wrong 'if' block in get_diff_text.
    diff_item = MagicMock()
    diff_item.new_file = False
    diff_item.deleted_file = False
    diff_item.a_path = "file.txt"
    diff_item.diff = b"staged diff"
    mock_repo.index.diff.return_value = [diff_item]
    
    results = fetch_repo_data("/path/to/repo", {"mode": "staged"})
    
    assert len(results) == 1
    # Fix: Access attributes, not keys
    assert results[0].hash == "STAGED_CHANGES"
    assert "staged diff" in results[0].diff

@patch("src.core.git.Repo")
def test_fetch_history_mode(mock_repo_cls, mock_repo, mock_commit):
    """Test fetching commit history."""
    mock_repo_cls.return_value = mock_repo
    
    # Setup history generator
    mock_repo.iter_commits.return_value = [mock_commit]
    
    results = fetch_repo_data("/path/to/repo", {"mode": "history", "limit": 1})
    
    assert len(results) == 1
    # Fix: Access attributes, not keys
    assert results[0].hash == "1234567890abcdef"
    assert results[0].author == "Test Author"

@patch("src.core.git.Repo")
def test_fetch_repo_data_invalid_repo(mock_repo_cls):
    """Test handling of invalid repositories."""
    # Simulate git.exc.InvalidGitRepositoryError
    # We need to import it to mock it properly, or just set side_effect to the class
    from git.exc import InvalidGitRepositoryError
    mock_repo_cls.side_effect = InvalidGitRepositoryError
    
    with pytest.raises(ValueError, match="not a valid Git repository"):
        fetch_repo_data("/bad/path", {})

@patch("src.core.git.Repo")
def test_fetch_staged_no_changes(mock_repo_cls, mock_repo):
    """Test staged mode when there are no changes."""
    mock_repo_cls.return_value = mock_repo
    mock_repo.index.diff.return_value = [] # Empty diff
    
    results = fetch_repo_data("/repo", {"mode": "staged"})
    
    assert results == []

@patch("src.core.git.Repo")
def test_fetch_history_filters(mock_repo_cls, mock_repo):
    """Test that filters are passed to iter_commits."""
    mock_repo_cls.return_value = mock_repo
    fetch_repo_data("/repo", {"mode": "history", "limit": "5", "author": "Me"})
    
    mock_repo.iter_commits.assert_called_with(max_count=5, author="Me")