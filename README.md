# Git History to JSON Extractor

This script extracts git commit history (or current staged changes) from a local repository and serializes it into a structured JSON file. It is designed to prepare git data for analysis or ingestion by Large Language Models (LLMs).

## Features

- **Interactive UI**: A guided command-line interface powered by `questionary`.
- **Dual Modes**:
    - **📜 History Mode**: Extract past commits based on depth, date, or author.
    - **📝 Staged Mode**: Extract currently staged (pre-commit) changes. Useful for generating commit messages with AI.
- **Automated Organization**: Outputs are automatically sorted into categorized directories (e.g., `Extracted JSON/All_History/`).
- **Diff Extraction**: Captures the full text diff for every entry.
- **Smart Configuration**: Remembers your recently accessed repositories.

## How to Use

1. **Run the script**:
   ```bash
   python extract-git-interactive.py

```

2. **Select a repository**:
* Choose from previously saved paths.
* Or enter a new absolute path to a local `.git` repository.


3. **Choose an Extraction Mode**:
* **Staged Changes**: Analyzes what is currently in the Index (ready to be committed).
* **All History**: Iterates through the entire commit tree.
* **Last N Commits**: Limits extraction to the most recent N items.
* **Date Range**: Filters by start (since) and end (until) dates.
* **By Author**: Filters by specific committer name.


4. **Name the output**:
* Enter a filename (e.g., `feature-update.json`).
* The script will automatically place it in: `Extracted JSON/<Category>/<filename>`.



## Dependencies

* `gitpython`: For interacting with the git repository.
* `questionary`: For the interactive terminal UI.

Install via pip:

```bash
pip install GitPython questionary

```

## Directory Structure

The script keeps your workspace clean by organizing outputs into the `Extracted JSON` folder:

```text
/Extracted JSON
    /Staged_Changes/    <-- Pre-commit analyses
    /All_History/       <-- Full dumps
    /Last_N_Commits/    <-- Recent snapshots
    /Date_Range/        <-- Time-boxed extracts
    /By_Author/         <-- User-specific audits

```

## Output Format

The output is a JSON array.

### Standard Commit

```json
[
    {
        "hash": "a1b2c3d4...",
        "short_hash": "a1b2c3d",
        "author": "Jane Doe",
        "date": "2023-10-25T14:30:00",
        "message": "Fix(auth): update login logic",
        "diff": "--- FILE: auth.py ---\n- old_code()\n+ new_code()"
    }
]

```

### Staged Change (Virtual Commit)

If you select "Staged Changes", the script creates a virtual commit object:

```json
[
    {
        "hash": "STAGED_CHANGES",
        "short_hash": "STAGED",
        "author": "You (Current User)",
        "message": "PRE-COMMIT: Staged changes ready for analysis.",
        "diff": "..."
    }
]

```
