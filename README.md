# Git History to JSON Extractor

This script extracts git commit history from a local repository and saves it to a JSON file. It provides an interactive command-line interface to select repositories, filter commits, and specify the output file.

## Features

- **Interactive UI**: A user-friendly command-line interface powered by `questionary`.
- **Repository Selection**: Choose from a list of previously used repositories or enter a new path.
- **Commit Filtering**: Filter commits by:
    - The last N commits.
    - A date range (since/until).
    - A specific author.
- **Diff Extraction**: Includes the diff of each commit in the output.
- **Configuration**: Saves repository paths for easy re-use.
- **Logging**: Logs errors to `git_extraction.log`.

## How to Use

1. **Run the script**:
   ```bash
   python extract-git-interactive.py
   ```
2. **Select a repository**:
   - Choose a repository from the list of saved paths.
   - Or, enter a new path to a local git repository.
3. **Choose a filter**:
   - **Extract Everything**: Get all commits from the repository.
   - **Last N Commits**: Specify the number of recent commits to extract.
   - **Date Range**: Provide a start and/or end date (YYYY-MM-DD).
   - **By Author**: Enter an author's name to get their commits.
4. **Specify output file**:
   - Enter a name for the output JSON file (default is `git_history.json`).
5. **Confirm**:
   - Review your selections and confirm to start the extraction.

## Dependencies

The script requires the following Python libraries:

- `gitpython`
- `questionary`

Install them using pip:
```bash
pip install GitPython questionary
```

## Configuration

The script uses a `repo_config.json` file to store the paths of repositories you've accessed. This file is created and managed automatically.

Example `repo_config.json`:
```json
{
    "saved_paths": [
        "C:\\Users\\user\\projects\\project1",
        "/home/user/projects/project2"
    ]
}
```

## Output Format

The output is a JSON array, where each object represents a commit with the following structure:

```json
[
    {
        "hash": "a1b2c3d...",
        "short_hash": "a1b2c3d",
        "author": "Author Name",
        "date": "YYYY-MM-DDTHH:MM:SS",
        "message": "Commit message...",
        "diff": "--- FILE: path/to/file.py ---\n...diff content..."
    }
]
```
