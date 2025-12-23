import pytest
import git
from src.core import fetch_repo_data

def test_fetch_history_mode(temp_git_repo):
    """Test that we can extract historical commits."""
    # ARRANGE: Add a second commit so we have a parent to compare against
    repo_path = temp_git_repo
    repo = git.Repo(repo_path)
    
    # Modify the existing file
    file_path = repo_path / "hello.py"
    file_path.write_text("print('Hello World v2')")
    
    # Commit the change
    repo.index.add([str(file_path)])
    repo.index.commit("Second commit")

    # ACT: Fetch only the latest commit
    filters = {"mode": "history", "limit": 1}
    data = fetch_repo_data(repo_path, filters)
    
    # ASSERT
    assert len(data) == 1
    assert data[0]["message"] == "Second commit"
    # Now this will pass because we are comparing 'Second' vs 'Initial'
    assert "Hello World v2" in data[0]["diff"]

def test_fetch_staged_mode(temp_git_repo):
    """Test that we can extract staged changes."""
    # Arrange: Modify a file and stage it
    repo_path = temp_git_repo
    new_file = repo_path / "new_feature.py"
    new_file.write_text("def new_feature(): pass")
    
    repo = git.Repo(repo_path)
    repo.index.add([str(new_file)]) # Stage it
    
    # Act
    filters = {"mode": "staged"}
    data = fetch_repo_data(repo_path, filters)
    
    # Assert
    assert len(data) == 1
    assert data[0]["hash"] == "STAGED_CHANGES"
    assert "new_feature.py" in data[0]["diff"]

def test_fetch_staged_empty(temp_git_repo):
    """Test behavior when nothing is staged."""
    # Act (No staging happens here)
    filters = {"mode": "staged"}
    data = fetch_repo_data(temp_git_repo, filters)
    
    # Assert
    assert data == [] # Should return empty list, not crash