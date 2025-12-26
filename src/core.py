import git
import logging
from datetime import datetime
from typing import List, Literal
from .schemas import CommitData

# Initialize module-level logger
logger = logging.getLogger(__name__)


class DiffExtractor:
    @staticmethod
    def _process_diff_index(diff_index) -> str:
        """Helper to convert a GitPython DiffIndex into a string, streaming large files."""  # noqa: E501
        diffs = []

        def _stream_blob_content(blob, empty_message):
            """Streams blob content line by line to avoid high memory usage."""
            if not blob:
                return empty_message
            try:
                # Iterate over the stream line by line instead of calling read()
                return "".join(
                    line.decode("utf-8", "replace") for line in blob.data_stream
                )
            except Exception:
                return "(Could not decode blob content)"

        for diff_item in diff_index:
            try:
                if diff_item.new_file:
                    prefix = f"--- NEW FILE: {diff_item.b_path} ---\n"
                    diff_text = _stream_blob_content(
                        diff_item.b_blob, "(File is binary or empty)"
                    )
                elif diff_item.deleted_file:
                    prefix = f"--- DELETED FILE: {diff_item.a_path} ---\n"
                    diff_text = _stream_blob_content(
                        diff_item.a_blob, "(File was binary or empty)"
                    )
                else:
                    prefix = f"--- FILE: {diff_item.a_path} ---\n"
                    # .diff contains the patch, which is generally small enough to read directly.  # noqa: E501
                    diff_text = diff_item.diff.decode("utf-8", "replace")

                diffs.append(f"{prefix}{diff_text}")

            except (UnicodeDecodeError, AttributeError, ValueError) as e:
                path = diff_item.a_path or diff_item.b_path
                msg = f"Skipping diff for {path} due to processing error: {e}"
                diffs.append(f"--- FILE: {path} ---(Could not decode diff: {e})")
                logger.warning(msg)
            except Exception as e:
                path = diff_item.a_path or diff_item.b_path
                msg = f"Error reading diff entry for {path}: {e}"
                diffs.append(f"--- FILE: {path} ---(Error processing diff: {e})")
                logger.error(msg, exc_info=True)

        return "\n".join(diffs) if diffs else "No changes detected."

    @staticmethod
    def extract_diff(
        diff_source: git.Repo | git.Commit,
        diff_type: Literal["staged", "commit"],
    ) -> str:
        """
        Extracts diff based on the specified source and type.
        """
        try:
            if diff_type == "staged":
                diff_index = diff_source.index.diff(
                    diff_source.head.commit, create_patch=True, R=True
                )
            elif diff_type == "commit":
                if not diff_source.parents:
                    diff_index = diff_source.tree.diff(git.NULL_TREE, create_patch=True)
                else:
                    parent = diff_source.parents[0]
                    diff_index = parent.diff(diff_source, create_patch=True)
            else:
                raise ValueError(
                    f"Invalid diff_type '{diff_type}' for source type {type(diff_source)}"  # noqa: E501
                )

            return DiffExtractor._process_diff_index(diff_index)
        except Exception as e:
            context = f"{diff_type} diff for {getattr(diff_source, 'hexsha', 'repo')}"
            logger.error(f"Error extracting {context}: {e}", exc_info=True)
            return f"Error extracting {context}: {e}"


class GitRepositoryContext:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._repo: git.Repo | None = None

    def __enter__(self) -> git.Repo:
        try:
            self._repo = git.Repo(self.repo_path, search_parent_directories=True)
            return self._repo
        except git.exc.InvalidGitRepositoryError:
            raise ValueError(f"'{self.repo_path}' is not a valid Git repository.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._repo:
            self._repo.close()


def get_commits_for_display(repo_path: str, limit: int = 25) -> List[dict]:
    """
    Fetches a list of recent commits with minimal data for display in a TUI.
    Includes affected file names for context.
    """
    try:
        with GitRepositoryContext(repo_path) as repo:
            commits_for_display = []
            for commit in repo.iter_commits(max_count=limit):
                try:
                    # Efficiently get affected file paths from commit stats
                    affected_files = list(commit.stats.files.keys())

                    commits_for_display.append(
                        {
                            "hash": commit.hexsha,
                            "short_hash": commit.hexsha[:7],
                            "author": commit.author.name or "Unknown Author",
                            "date": datetime.fromtimestamp(
                                commit.committed_date
                            ).strftime("%Y-%m-%d %H:%M"),
                            "message": commit.message.strip().split("\n")[0],
                            "files": affected_files,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not process commit {commit.hexsha} for display: {e}"
                    )
            return commits_for_display
    except Exception as e:
        logger.error(
            f"Error getting commits for display from '{repo_path}': {e}", exc_info=True
        )
        raise e


def _fetch_staged_data(repo: git.Repo) -> List[CommitData]:
    """Fetches a virtual commit representing staged changes."""
    logger.info("Fetching Staged Changes...")
    staged_diff = DiffExtractor.extract_diff(repo, "staged")

    if not staged_diff or staged_diff == "No changes detected.":
        return []

    return [
        CommitData(
            hash="STAGED_CHANGES",
            short_hash="STAGED",
            author="Current User",
            date=datetime.now(),
            message="PRE-COMMIT: Staged changes ready for analysis.",
            diff=staged_diff,
        )
    ]


def _fetch_history_data_by_hashes(
    repo: git.Repo, hashes: List[str]
) -> List[CommitData]:
    """Fetches full commit data for a specific list of commit hashes."""
    commits_data = []
    for commit_hash in hashes:
        try:
            commit = repo.commit(commit_hash)
            commit_info = CommitData(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:7],
                author=commit.author.name or "Unknown Author",
                date=datetime.fromtimestamp(commit.committed_date),
                message=commit.message.strip(),
                diff=DiffExtractor.extract_diff(commit, "commit"),
            )
            commits_data.append(commit_info)
        except Exception as e:
            logger.error(
                f"Could not fetch data for commit hash {commit_hash}: {e}",  # noqa: E501
                exc_info=True,
            )
    return commits_data


def _fetch_history_data(repo: git.Repo, filters: dict) -> List[CommitData]:
    """Fetches commit history based on the provided filters."""
    kwargs = {}
    if filters.get("limit"):
        kwargs["max_count"] = int(filters["limit"])
    if filters.get("since"):
        kwargs["since"] = filters["since"]
    if filters.get("until"):
        kwargs["until"] = filters["until"]
    if filters.get("author"):
        kwargs["author"] = filters["author"]

    logger.info(f"Fetching History with filters: {kwargs}")
    commits_generator = repo.iter_commits(**kwargs)

    commits_data = []
    for commit in commits_generator:
        if len(commits_data) >= 1000:  # Safety cap to prevent excessive memory use
            logger.warning(
                "Reached maximum commit fetch limit of 1000. Stopping further processing."  # noqa: E501
            )
            break
        commit_info = CommitData(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:7],
            author=commit.author.name or "Unknown Author",
            date=datetime.fromtimestamp(commit.committed_date),
            message=commit.message.strip(),
            diff=DiffExtractor.extract_diff(commit, "commit"),
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
        with GitRepositoryContext(repo_path) as repo:
            mode = filters.get("mode")
            if mode == "staged":
                return _fetch_staged_data(repo)
            elif mode == "hashes":
                commit_hashes = filters.get("hashes", [])
                if not commit_hashes:
                    return []
                return _fetch_history_data_by_hashes(repo, commit_hashes)
            else:  # Default to 'history' mode
                return _fetch_history_data(repo, filters)

    except ValueError as e:  # Catch ValueError from GitRepositoryContext
        logger.critical(f"Error fetching data from '{repo_path}': {e}", exc_info=True)
        raise e
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred while fetching data from '{repo_path}': {e}",
            exc_info=True,
        )
        raise e
