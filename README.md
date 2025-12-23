# Git-to-JSON Framework: The Adaptive Intent Engine

> **Bridge the gap between your local git repository and Large Language Models (LLMs).**

This is not just a data extractor. It is a modular framework designed to generate context-aware prompts for AI development workflows. It features an **Adaptive Intent Engine** that uses accurate token counting to intelligently decide whether to copy results to your clipboard (for quick tasks) or save them to files (for deep analysis).

## 🚀 Features

* **🧠 Adaptive Intent Engine**: Automatically detects payload size using `tiktoken` (OpenAI's tokenizer).
    * *Small Payload (< 3.5k tokens)*: Copies directly to your **Clipboard**. Paste straight into ChatGPT/Claude.
    * *Large Payload (> 3.5k tokens)*: Automatically falls back to saving a structured `PROMPT.md` file to prevent clipboard crashes.
* **🔌 Plugin Architecture**: Add new capabilities just by dropping a JSON file into the `templates/` folder.
* **💾 Dual Modes**:
    * **Workflow Mode**: Task-based generation (Commit Messages, Code Reviews, Bug Hunts).
    * **Raw Mode**: Classic extraction of full git history to JSON datasets for custom analysis.
* **🛡️ Production Grade**:
    * **Secure**: Runs 100% locally. Automatically ignores output directories to prevent data leaks.
    * **Robust**: Includes a full `pytest` suite and CI/CD integration via GitHub Actions.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/sunman97-ui/git-to-json.git](https://github.com/sunman97-ui/git-to-json.git)
    cd git-to-json
    ```

2.  **Create a virtual environment (recommended)**:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚡ Usage

Run the main entry point:
```bash
python main.py

```

### The Menu

You will be greeted with an **Intent-Based Menu**:

* **📝 Generate Commit Message** (Template): Extracts staged changes, hydrates a professional prompt, and copies it to your clipboard.
* **💾 Extract Raw Data** (Classic Mode): The utility to dump git history (Last N commits, Date Range, etc.) into a JSON file.

## 🧩 Extending (How to add Templates)

You can create custom workflows by adding a `.json` file to the `templates/` directory.

**Example: `templates/find_bugs.json**`

```json
{
    "meta": {
        "name": "🐛 Analyze Last Commit for Bugs",
        "description": "Scans the most recent commit for logic errors."
    },
    "execution": {
        "source": "history",
        "limit": 1,
        "output_mode": "auto"
    },
    "prompts": {
        "system": "You are a QA Engineer.",
        "user": "Find bugs in this code:\n\n{DIFF_CONTENT}"
    }
}

```

*The framework automatically detects this file and adds it to the CLI menu.*

## 👨‍💻 Development & Testing

This project enforces code quality via `pytest`.

To run the test suite locally:

```bash
pytest

```

Tests are also automatically run on every Push and Pull Request via **GitHub Actions**.

## 📂 Project Structure

```text
├── .github/             # CI/CD Workflows
├── src/                 # Core Framework Logic
│   ├── core.py          # Git Extraction Engine
│   ├── engine.py        # Prompt Hydration & Clipboard Logic
│   ├── cli.py           # Interactive Menu
│   └── utils.py         # Token Counting & Config
├── templates/           # User-defined workflows (JSON)
├── tests/               # Pytest Suite
├── Extracted JSON/      # Output directory (Git-ignored)
└── main.py              # Entry point

```

## 📜 License

MIT License. See `LICENSE` for details.

