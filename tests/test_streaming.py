import pytest
import json
from unittest.mock import MagicMock, patch
from typing import Iterator
from src.core import fetch_repo_data, CommitData
from src.utils import save_data_to_file
from datetime import datetime


# --- Mock Data Fixture ---
@pytest.fixture
def sample_commit_data():
    return [
        CommitData(
            hash="111",
            short_hash="111",
            author="Tester",
            date=datetime.now(),
            message="First",
            diff="diff1",
        ),
        CommitData(
            hash="222",
            short_hash="222",
            author="Tester",
            date=datetime.now(),
            message="Second",
            diff="diff2",
        ),
    ]


# --- Test 1: Verify Core Returns a Generator ---
@patch("src.core.GitRepositoryContext")
def test_fetch_repo_data_is_generator(mock_context, sample_commit_data):
    """
    Ensures that fetch_repo_data returns an iterator/generator,
    NOT a list (which would load everything into RAM).
    """
    # Setup Mock Repo
    mock_repo = MagicMock()
    mock_context.return_value.__enter__.return_value = mock_repo

    # Mock the internal iterator to yield our sample data
    # We mock _fetch_history_data to yield instead of returning list
    with patch("src.core._fetch_history_data") as mock_fetch:
        mock_fetch.return_value = iter(sample_commit_data)

        # Execute
        result = fetch_repo_data("/mock/path", {"mode": "history"})

        # ASSERT: It must be an iterator, not a list
        assert isinstance(result, Iterator)
        assert not isinstance(result, list)

        # ASSERT: We can consume it
        items = list(result)
        assert len(items) == 2
        assert items[0].hash == "111"


# --- Test 2: Verify Utils Streams Valid JSON ---
def test_save_data_to_file_creates_valid_json(tmp_path, sample_commit_data):
    """
    Ensures the manual file writing logic (writing '[' and ',' manually)
    produces valid JSON that can be read back.
    """
    # Create a generator (not a list) to pass to the function
    data_gen = (item for item in sample_commit_data)

    output_file = tmp_path / "stream_test.json"
    str_path = str(output_file)

    # Execute
    success = save_data_to_file(data_gen, str_path)

    # Verify Success
    assert success is True
    assert output_file.exists()

    # Verify Content Validity
    with open(output_file, "r") as f:
        content = json.load(f)

    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["hash"] == "111"
    assert content[1]["hash"] == "222"


# --- Test 3: Verify Empty Generator Handling ---
def test_save_empty_generator(tmp_path):
    """Ensures we handle 0 items correctly (empty JSON list)."""
    empty_gen = (x for x in [])
    output_file = tmp_path / "empty.json"

    save_data_to_file(empty_gen, str(output_file))

    with open(output_file, "r") as f:
        content = json.load(f)

    assert content == []
