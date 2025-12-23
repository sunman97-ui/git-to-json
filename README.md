# Git-to-JSON Framework: The Adaptive Intent Engine

> **Bridge the gap between your local git repository and Large Language Models (LLMs).**

This is not just a data extractor. It is a modular framework designed to generate context-aware prompts for AI development workflows. It features an **Adaptive Intent Engine** that intelligently decides whether to copy results to your clipboard (for quick tasks) or save them to files (for deep analysis).

## 🚀 Features

* **🧠 Adaptive Engine**: Automatically detects payload size.
    * *Small (< 4k tokens)*: Copies directly to your **Clipboard**. Paste straight into ChatGPT/Claude.
    * *Large (> 4k tokens)*: Saves to a structured `PROMPT.md` file.
* **🔌 Plugin Architecture**: Add new capabilities just by dropping a JSON file into the `templates/` folder.
* **💾 Dual Modes**:
    * **Workflow Mode**: Task-based generation (Commit Messages, Code Reviews, Bug Hunts).
    * **Raw Mode**: Classic extraction of full git history to JSON datasets.
* **🔒 Secure by Design**:
    * Runs 100% locally.
    * Automatically ignores output directories (`Extracted JSON/`) to prevent accidental data leaks.
    * Does not require API keys.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/sunman97-ui/git-to-json.git](https://github.com/sunman97-ui/git-to-json.git)
    cd git-to-json
    ```

2.  **Install dependencies**:
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

* **📝 Generate Commit Message**: Extracts staged changes, hydrates a prompt, and copies it to your clipboard.
* **💾 Extract Raw Data**: The classic utility to dump git history (Last N commits, Date Range, etc.) into a JSON file for custom analysis.

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

## 📂 Project Structure

```text
├── src/                 # Core Framework Logic
│   ├── core.py          # Git Extraction Engine
│   ├── engine.py        # Prompt Hydration & Clipboard Logic
│   └── cli.py           # Interactive Menu
├── templates/           # User-defined workflows (JSON)
├── Extracted JSON/      # Output directory (Git-ignored)
└── main.py              # Entry point

```

## 📜 License

MIT License. See `LICENSE` for details.

```
