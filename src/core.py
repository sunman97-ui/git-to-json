import git
import logging
from datetime import datetime
from typing import List
from .schemas import CommitData

# Initialize module-level logger
logger = logging.getLogger(__name__)

def get_diff_text(diff_index, repo):
    """Helper to convert a GitPython DiffIndex into a string."""
    diffs = []
    for diff_item in diff_index:
        try:
            if diff_item.new_file:
                prefix = f"--- NEW FILE: {diff_item.b_path} ---\n"
                diff_text = diff_item.b_blob.data_stream.read().decode('utf-8', 'replace') if diff_item.b_blob else "(File is binary or empty)"
            elif diff_item.deleted_file:
                prefix = f"--- DELETED FILE: {diff_item.a_path} ---\n"
                diff_text = diff_item.a_blob.data_stream.read().decode('utf-8', 'replace') if diff_item.a_blob else "(File was binary or empty)"
            else:
                prefix = f"--- FILE: {diff_item.a_path} ---\n"
                diff_text = diff_item.diff.decode('utf-8', 'replace')
            
            diffs.append(f"{prefix}{diff_text}")

        except (UnicodeDecodeError, AttributeError, ValueError) as e:
            path = diff_item.a_path or diff_item.b_path
            msg = f"Skipping diff for {path} due to processing error: {e}"
            diffs.append(f"--- FILE: {path} ---\n(Could not decode diff: {e})")
            logger.warning(msg)
        except Exception as e:
            path = diff_item.a_path or diff_item.b_path
            msg = f"Error reading diff entry for {path}: {e}"
            diffs.append(f"--- FILE: {path} ---\n(Error processing diff: {e})")
            logger.error(msg, exc_info=True)
            
    return "\n".join(diffs) if diffs else "No changes detected."

def get_staged_diff(repo: git.Repo) -> str:
    """Extracts diff for currently STAGED changes (Index vs HEAD)."""
    try:
        diff_index = repo.index.diff(repo.head.commit, create_patch=True, R=True)
        return get_diff_text(diff_index, repo)
    except Exception as e:
        logger.error(f"Staged diff error: {e}", exc_info=True)
        return f"Error getting staged diff: {e}"

def get_commit_diff(commit: git.Commit) -> str:
    """Extracts diff for a historical commit."""
    try:
        if not commit.parents:
            # For initial commit, show its content against an empty tree
            diff_index = commit.tree.diff(git.NULL_TREE, create_patch=True)
            return get_diff_text(diff_index, commit.repo)
        parent = commit.parents[0]
        diff_index = parent.diff(commit, create_patch=True)
        return get_diff_text(diff_index, commit.repo)
    except Exception as e:
        logger.error(f"Error extracting diff for commit {commit.hexsha}: {e}", exc_info=True)
        return f"Error extracting diff: {str(e)}"

def _fetch_staged_data(repo: git.Repo) -> List[CommitData]:
    """Fetches a virtual commit representing staged changes."""
    logger.info("Fetching Staged Changes...")
    staged_diff = get_staged_diff(repo)
    
    if not staged_diff or staged_diff == "No changes detected.":
        return []

    return [CommitData(
        hash="STAGED_CHANGES",
        short_hash="STAGED",
        author="Current User",
        date=datetime.now(),
        message="PRE-COMMIT: Staged changes ready for analysis.",
        diff=staged_diff
    )]

def _fetch_history_data(repo: git.Repo, filters: dict) -> List[CommitData]:
    """Fetches commit history based on the provided filters."""
    kwargs = {}
    if filters.get('limit'): kwargs['max_count'] = int(filters['limit'])
    if filters.get('since'): kwargs['since'] = filters['since']
    if filters.get('until'): kwargs['until'] = filters['until']
    if filters.get('author'): kwargs['author'] = filters['author']

    logger.info(f"Fetching History with filters: {kwargs}")
    commits_generator = repo.iter_commits(**kwargs)
    
    commits_data = []
    for commit in commits_generator:
        commit_info = CommitData(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:7],
            author=commit.author.name or "Unknown Author",
            date=datetime.fromtimestamp(commit.committed_date),
            message=commit.message.strip(),
            diff=get_commit_diff(commit)
        )
        commits_data.append(commit_info)
    return commits_data

def fetch_repo_data(repo_path: str, filters: dict) -> List[CommitData]:
    """
    Fetches repository data (staged changes or history) based on filters.
    Input: Path and Filters
    Output: List of CommitData objects.
    """
    try:
        repo = git.Repo(repo_path, search_parent_directories=True)

        if filters.get('mode') == 'staged':
            return _fetch_staged_data(repo)
        else:
            return _fetch_history_data(repo, filters)

    except git.exc.InvalidGitRepositoryError:
        logger.critical(f"Invalid git repo: {repo_path}")
        raise ValueError(f"'{repo_path}' is not a valid Git repository.")
    except Exception as e:
        logger.critical(f"Error fetching data from '{repo_path}': {e}", exc_info=True)
        raise e