import pytest
import os
import git
from pathlib import Path

@pytest.fixture
def temp_git_repo(tmp_path):
    """
    Creates a temporary git repo with some commits.
    returns the path to the repo.
    """
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    repo = git.Repo.init(repo_dir)
    
    # Configure author (required for commits)
    repo.config_writer().set_value("user", "name", "Test Bot").release()
    repo.config_writer().set_value("user", "email", "test@bot.com").release()
    
    # Create a file and commit it (History)
    file_path = repo_dir / "hello.py"
    file_path.write_text("print('Hello World')")
    repo.index.add([str(file_path)])
    repo.index.commit("Initial commit")
    
    return repo_dir