import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.core import fetch_repo_data, CommitData

# --- Fixtures ---


@pytest.fixture
def mock_commit_data():
    return [
        CommitData(
            hash="abc1234",
            short_hash="abc1234",
            author="Test Author",
            date=datetime(2023, 1, 1),
            message="Test Message",
            diff="diff content",
        )
    ]


# --- Tests ---


@patch("src.core.GitRepositoryContext")
@patch("src.core._fetch_staged_data")
def test_fetch_staged_mode(mock_fetch_staged, mock_context, mock_commit_data):
    """Test fetching staged changes returns the expected list (consumed generator)."""
    # Setup
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo

    # The internal function returns an iterator/generator
    mock_fetch_staged.return_value = iter(mock_commit_data)

    # Execute
    # CRITICAL FIX: We must consume the generator using list() to trigger logic
    gen = fetch_repo_data("/mock/path", {"mode": "staged"})
    results = list(gen)

    # Assert
    assert len(results) == 1
    assert results[0].hash == "abc1234"
    mock_fetch_staged.assert_called_once_with(mock_repo)


@patch("src.core.GitRepositoryContext")
@patch("src.core._fetch_staged_data")
def test_fetch_staged_no_changes(mock_fetch_staged, mock_context):
    """Test fetching staged changes handles empty results."""
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo

    # Return empty iterator
    mock_fetch_staged.return_value = iter([])

    # Execute
    gen = fetch_repo_data("/mock/path", {"mode": "staged"})
    results = list(gen)

    # Assert
    assert results == []


@patch("src.core.GitRepositoryContext")
@patch("src.core._fetch_history_data")
def test_fetch_history_mode(mock_fetch_history, mock_context, mock_commit_data):
    """Test fetching history returns expected items."""
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo

    mock_fetch_history.return_value = iter(mock_commit_data)

    # Execute
    gen = fetch_repo_data("/mock/path", {"mode": "history"})
    results = list(gen)

    # Assert
    assert len(results) == 1
    assert results[0].message == "Test Message"
    # Note: filters dict passed might differ slightly depending on defaults,
    # checking called matches what we passed.
    mock_fetch_history.assert_called_once_with(mock_repo, {"mode": "history"})


@patch("src.core.GitRepositoryContext")
@patch("src.core._fetch_history_data")
def test_fetch_history_filters(mock_fetch_history, mock_context):
    """Test that filters are passed correctly to the internal history fetcher."""
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo
    mock_fetch_history.return_value = iter([])

    filters = {"mode": "history", "limit": 10, "author": "Dave"}

    # Execute
    # Must list() to trigger the call to _fetch_history_data
    list(fetch_repo_data("/mock/path", filters))

    # Assert
    mock_fetch_history.assert_called_once_with(mock_repo, filters)


@patch("src.core.GitRepositoryContext")
@patch("src.core._fetch_history_data_by_hashes")
def test_fetch_repo_data_mode_hashes(mock_fetch_hashes, mock_context, mock_commit_data):
    """Test 'hashes' mode delegates to the correct internal function."""
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo
    mock_fetch_hashes.return_value = iter(mock_commit_data)

    filters = {"mode": "hashes", "hashes": ["hash1", "hash2"]}

    # Execute
    results = list(fetch_repo_data("/mock/path", filters))

    # Assert
    assert len(results) == 1
    mock_fetch_hashes.assert_called_once_with(mock_repo, ["hash1", "hash2"])


@patch("src.core.GitRepositoryContext")
def test_fetch_repo_data_invalid_repo(mock_context):
    """Test that invalid repo errors are raised correctly."""
    # Setup the context manager to raise ValueError on __enter__
    mock_context.return_value.__enter__.side_effect = ValueError("Invalid Git Repo")

    # Execute & Assert
    with pytest.raises(ValueError):
        # CRITICAL FIX: Calling fetch_repo_data() just returns a generator.
        # It won't try to enter the context (and fail) until we try to get an item.
        list(fetch_repo_data("/invalid/path", {}))


# --- Tests for internal helpers (Optional but good for coverage) ---


@patch("src.core.DiffExtractor.extract_diff")
def test_fetch_history_data_by_hashes_success(mock_extract):
    """Test the internal helper for fetching specific hashes."""
    from src.core import _fetch_history_data_by_hashes

    # 1. Setup Mock Repo
    mock_repo = MagicMock()
    mock_commit = MagicMock()

    # 2. Setup Mock Commit Attributes (CRITICAL: Must be strings for Pydantic)
    mock_commit.hexsha = "abc1234567"  # Valid hexsha
    mock_commit.committed_date = 1672531200
    mock_commit.message = "Fixed Message"
    mock_commit.author.name = (
        "Test Author"  # <--- FIX: This was missing/mocked incorrectly
    )

    mock_repo.commit.return_value = mock_commit
    mock_extract.return_value = "diff_content"

    # 3. Execute
    # We pass a valid list of hashes
    gen = _fetch_history_data_by_hashes(mock_repo, ["abc1234567"])
    results = list(gen)

    # 4. Assert
    assert len(results) == 1
    assert results[0].hash == "abc1234567"
    assert results[0].author == "Test Author"
