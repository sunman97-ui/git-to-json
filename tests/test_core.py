import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from src.core import fetch_repo_data, get_commits_for_display
import git

# --- Mocks ---

@pytest.fixture
def mock_repo():
    # Return an autospecced mock that acts like a git.Repo instance
    repo = MagicMock(spec=git.Repo)
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

@patch("src.core.git", autospec=True)
def test_fetch_staged_no_changes(mock_git_module, mock_repo):
    """Test staged mode when there are no changes."""
    mock_git_module.Repo.return_value = mock_repo
    mock_repo.index.diff.return_value = [] # Empty diff
    
    results = fetch_repo_data("/repo", {"mode": "staged"})
    
    assert results == []

@patch("src.core.git.Repo")
def test_fetch_history_filters(mock_repo_cls, mock_repo):
    """Test that filters are passed to iter_commits."""
    mock_repo_cls.return_value = mock_repo
    fetch_repo_data("/repo", {"mode": "history", "limit": "5", "author": "Me"})
    
    mock_repo.iter_commits.assert_called_with(max_count=5, author="Me")

# New Fixtures
@pytest.fixture
def mock_commit_with_stats():
    commit = MagicMock()
    commit.hexsha = "c0ffee" * 4
    commit.author.name = "Dev Lead"
    commit.committed_date = 1700000000
    commit.message = "Feat: Add new feature\n\n- Details of feature"
    
    # Mock commit.stats.files
    mock_stats_files = MagicMock()
    mock_stats_files.keys.return_value = ["src/file1.py", "src/file2.py", "docs/README.md"]
    commit.stats.files = mock_stats_files
    
    return commit

# New Tests
@patch("src.core.git.Repo")
def test_get_commits_for_display_success(mock_repo_cls, mock_repo, mock_commit_with_stats):
    """Test get_commits_for_display returns correctly formatted data."""
    mock_repo_cls.return_value = mock_repo
    mock_repo.iter_commits.return_value = [mock_commit_with_stats]
    
    results = get_commits_for_display("/path/to/repo", limit=1)
    
    assert len(results) == 1
    commit_info = results[0]
    assert commit_info["short_hash"] == "c0ffeec"
    assert commit_info["author"] == "Dev Lead"
    assert "Feat: Add new feature" in commit_info["message"]
    assert "src/file1.py" in commit_info["files"]
    assert "src/file2.py" in commit_info["files"]
    assert "docs/README.md" in commit_info["files"]

@patch("src.core.git.Repo")
@patch("src.core.DiffExtractor.extract_diff")
def test_fetch_history_data_by_hashes_success(mock_extract_diff, mock_repo_cls, mock_repo, mock_commit):
    """Test fetching specific commits by hash."""
    mock_repo_cls.return_value = mock_repo
    mock_repo.commit.side_effect = [mock_commit, mock_commit] # Return same mock commit for simplicity
    mock_extract_diff.return_value = "mocked diff"
    
    test_hashes = ["hash1", "hash2"]
    results = fetch_repo_data("/path/to/repo", {"mode": "hashes", "hashes": test_hashes})
    
    assert len(results) == 2
    mock_repo.commit.assert_has_calls([call("hash1"), call("hash2")])
    assert results[0].diff == "mocked diff"
    assert results[1].diff == "mocked diff"

@patch("src.core._fetch_history_data_by_hashes")
@patch("src.core._fetch_staged_data")
@patch("src.core._fetch_history_data")
@patch("src.core.git.Repo")
def test_fetch_repo_data_mode_hashes(mock_repo_cls, mock_fetch_history, mock_fetch_staged, mock_fetch_by_hashes, mock_repo):
    """Test fetch_repo_data correctly dispatches to _fetch_history_data_by_hashes."""
    mock_repo_cls.return_value = mock_repo
    mock_fetch_by_hashes.return_value = ["mock_commit_data"]
    
    test_hashes = ["hash_abc"]
    results = fetch_repo_data("/path/to/repo", {"mode": "hashes", "hashes": test_hashes})
    
    mock_fetch_by_hashes.assert_called_once_with(mock_repo, test_hashes)
    mock_fetch_staged.assert_not_called()
    mock_fetch_history.assert_not_called()
    assert results == ["mock_commit_data"]