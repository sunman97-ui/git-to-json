import git
import logging
from datetime import datetime

# Initialize module-level logger
logger = logging.getLogger(__name__)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_diff_text(diff_index, repo):
    """Helper to convert a GitPython DiffIndex into a string."""
    diffs = []
    # R=True means we are looking at things relative to the index/staging
    for diff_item in diff_index:
        try:
            # Handle Rename/New/Deleted
            if diff_item.new_file:
                prefix = f"--- NEW FILE: {diff_item.b_path} ---\n"
            elif diff_item.deleted_file:
                prefix = f"--- DELETED FILE: {diff_item.a_path} ---\n"
            else:
                path = diff_item.b_path if diff_item.b_path else diff_item.a_path
                prefix = f"--- FILE: {path} ---\n"

            # Get Diff Content
            # For staged changes (index vs HEAD), we often need to read the blob directly 
            # if diff is empty, but usually create_patch=True handles it.
            if diff_item.diff:
                diff_text = diff_item.diff.decode('utf-8', 'replace')
            else:
                diff_text = "(New file content)" 

            diffs.append(f"{prefix}{diff_text}")
            
        except Exception as e:
            msg = f"Error reading diff entry: {e}"
            diffs.append(msg)
            logger.error(msg)
            
    return "\n".join(diffs) if diffs else "No changes detected."

def get_staged_diff(repo):
    """Extracts diff for currently STAGED changes (Index vs HEAD)."""
    try:
        # STRICT COMPARISON: Index vs HEAD
        diff_index = repo.index.diff(repo.head.commit, create_patch=True, R=True)
        return get_diff_text(diff_index, repo)
    except Exception as e:
        logger.error(f"Staged diff error: {e}", exc_info=True)
        return None

def get_commit_diff(commit):
    """Extracts diff for a historical commit."""
    try:
        if not commit.parents:
            return "Initial Commit - No parent diff available."
        parent = commit.parents[0]
        diff_index = parent.diff(commit, create_patch=True)
        # We pass None for repo here as standard commit diffs don't usually need repo access for blobs
        return get_diff_text(diff_index, None) 
    except Exception as e:
        return f"Error extracting diff: {str(e)}"

def fetch_repo_data(repo_path, filters):
    """
    Pure Logic Function:
    Input: Path and Filters
    Output: List of dictionaries (The Data)
    """
    try:
        repo = git.Repo(repo_path)
        commits_data = []

        # --- MODE: STAGED CHANGES ---
        if filters.get('mode') == 'staged':
            logger.info("Fetching Staged Changes...")
            staged_diff = get_staged_diff(repo)
            
            if not staged_diff or staged_diff == "No changes detected.":
                return [] # Return empty list, let UI handle the message

            virtual_commit = {
                "hash": "STAGED_CHANGES",
                "short_hash": "STAGED",
                "author": "Current User",
                "date": datetime.now(),
                "message": "PRE-COMMIT: Staged changes ready for analysis.",
                "diff": staged_diff
            }
            commits_data.append(virtual_commit)

        # --- MODE: HISTORY ---
        else:
            kwargs = {}
            if filters.get('limit'): kwargs['max_count'] = int(filters['limit'])
            if filters.get('since'): kwargs['since'] = filters['since']
            if filters.get('until'): kwargs['until'] = filters['until']
            if filters.get('author'): kwargs['author'] = filters['author']

            logger.info(f"Fetching History with filters: {kwargs}")
            commits_generator = list(repo.iter_commits(**kwargs))
            
            for commit in commits_generator:
                commit_info = {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "author": commit.author.name,
                    "date": datetime.fromtimestamp(commit.committed_date),
                    "message": commit.message.strip(),
                    "diff": get_commit_diff(commit)
                }
                commits_data.append(commit_info)

        return commits_data

    except git.exc.InvalidGitRepositoryError:
        logger.critical(f"Invalid git repo: {repo_path}")
        raise ValueError("Invalid Git Repository")
    except Exception as e:
        logger.critical(f"Error fetching data: {e}", exc_info=True)
        raise e