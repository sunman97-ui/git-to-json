# 🤖 Git-to-JSON Framework (v3.0)

> **The missing bridge between your Local Git Repository and AI Agents.**

**Git-to-JSON** has evolved from a simple data extractor into a fully-fledged **AI Execution Engine** for your terminal. 

With **v3.0**, it allows you to stream prompts directly to Large Language Models—either in the cloud (OpenAI, XAI, Gemini) or running **100% locally and privately** (Ollama). It features an interactive CLI loop, real-time matrix-style text streaming, and a modular provider system.

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10+-yellow.svg) ![Privacy](https://img.shields.io/badge/privacy-100%25_local_mode-green.svg)

---

## ✨ Key Features (v3.0)

*   **🚀 Interactive Workflow:** A continuous CLI loop allows you to generate commit messages, analyze bugs, and query AI agents without restarting the session.
*   **🤝 Interactive Commit Selection:** Dive deep into your repository history. Select multiple specific commits from an interactive list, combine their diffs, and send them to your chosen AI agent for consolidated analysis or save them to a single JSON file.
*   **🛡️ Private Mode (Ollama):** Run models like `llama3`, `mistral`, or `deepseek` entirely on your hardware. Your code **never** leaves your machine.
*   **☁️ Cloud Integration:** Native support for **OpenAI** (GPT-4o), **XAI** (Grok), and **Google Gemini** (2.0 Flash/Pro).
*   **⚡ Async Streaming:** Real-time text generation directly in your terminal using the `Rich` UI library.
*   **🔌 Template System:** Pre-built workflows that hydrate prompts with your git diffs:
    *   *Generate Semantic Commit Messages*
    *   *Analyze Staged Changes for Bugs*
    *   *Generate Documentation*
*   **💾 Smart Output:** Flexible handling—copy to clipboard, save to file, or execute immediately.

![Git-to-JSON Terminal Interface](https://raw.githubusercontent.com/sunman97-ui/git-to-json/main/assets/screenshot.png)

---

## 🛠️ Installation

### 1. Prerequisites
*   **Python 3.10+**
*   **Git** installed and available in your terminal.

### 2. Setup

```bash
# 1. Clone the repository
git clone https://github.com/sunman97-ui/git-to-json.git
cd git-to-json

# 2. Create a virtual environment (Recommended)
python -m venv venv

# 3. Activate the environment
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration (The .env File)

The tool uses a `.env` file to manage secrets securely.

1.  Copy the example file (if available) or create a new one:
```bash
# Create a new .env file
touch .env

```


2.  Edit `.env` and add keys **only for the providers you intend to use**:

```ini
# --- OPTION 1: PRIVATE MODE (Local) ---
# No API Key required. Points to your local Ollama instance.
# IMPORTANT: Must end with /v1 for compatibility
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b

# --- OPTION 2: CLOUD PROVIDERS ---
# You must provide your own API keys for cloud services.
# Leave blank if not using these providers.
OPENAI_API_KEY="put-your-key-here"
GEMINI_API_KEY="put-your-key-here"
XAI_API_KEY="put-your-key-here"


```

---

## 🛡️ Private Mode Setup (Ollama)

To use the **100% Local & Private** mode, you must have the Ollama software installed on your machine.

1.  **Install Ollama:** Download from [ollama.com](https://ollama.com).
2.  **Pull a Model:** Open your terminal and run the command for the model you wish to use (must match your `.env` config):
```bash
ollama pull llama3.1:8b

```


3.  **Start the Server:** Ensure Ollama is running in the background (check your system tray) or run:
```bash
ollama serve

```



> **Privacy Guarantee:** When using the Ollama provider, Git-to-JSON connects strictly to `localhost`. Your code, diffs, and prompts are processed entirely on your CPU/GPU. **No data is sent to the internet.**

---

## 🚀 Usage

Run the main application:

```bash
python main.py

```

### The Interactive Menu

When you run the app, you will be presented with a dynamic menu that mixes your templates with core tools:

*   **🤝 Interactive Commit Selection:** This new mode allows you to browse recent commits, select multiple ones from a checklist, and then either send their combined changes to an AI for a consolidated review or save them into a single JSON file.
*   **🚀 Execute AI Prompt (Direct Mode):** Chat directly with your chosen AI provider (Ollama/OpenAI) without any git context. Great for general coding questions.
*   **💾 Extract Raw Data (Classic Mode):** The utility to dump git history (Last N commits, Date Range, etc.) into a JSON file for custom analysis.
*   **📝 [Templates]:** Any JSON file found in the `templates/` directory will appear here (e.g., "Generate Commit Message").
*   These workflows automatically extract diffs, hydrate prompts, and offer to **Copy**, **Save**, or **Execute** the result.



---

## 🧩 Extending (How to add Templates)

You can create custom workflows by adding a `.json` file to the `templates/` directory.

Example:**templates/refactor-suggester.json**`

```json
{
    "meta": {
        "name": "💡 Suggest Code Refinements",
        "description": "Analyzes staged changes for potential refactoring and quality improvements."
    },
    "execution": {
        "source": "staged",
        "output_mode": "auto"
    },
    "prompts": {
        "system": "You are a Principal Software Engineer specializing in code quality and elegant design. Your task is to review code changes and provide actionable suggestions for improvement. Focus on clarity, performance, and adherence to modern best practices. Do not comment on trivial style issues like whitespace.",
        "user": "Review the git diff below and identify areas for refactoring or improvement. For each suggestion, provide a brief, clear explanation of the benefit and a code snippet of the proposed change.'\n\n{DIFF_CONTENT}"
    }
}
```

*The framework automatically detects this file and adds it to the CLI menu.*

---

## 👨‍💻 Development & Testing

This project enforces code quality via `pytest`.

To run the test suite locally:

```bash
pytest

```

---

## 📂 Project Structure

```text
git-to-json/
├── src/
│   ├── cli.py             # Main interactive loop & menu logic
│   ├── engine.py          # Async AI orchestration & Prompt handling
│   ├── providers.py       # Adapter factory (Ollama/OpenAI/Gemini/XAI)
│   ├── template_loader.py # Plugin system for loading JSON workflows
│   ├── config.py          # Pydantic settings & validation
│   └── core.py            # Git extraction logic
├── templates/             # JSON files defining prompt workflows
├── Extracted JSON/        # Output directory for raw extractions (e.g., Staged_Changes, Combined_Commits)
├── repo_config.json       # Stores your recently used repository paths
├── .env                   # API Keys (Ignored by Git)
└── main.py                # Entry point

```

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feat/amazing-feature`).
3.  Commit your changes (**Atomic commits preferred**).
4.  Push to the branch.
5.  Open a Pull Request.

---

## 📜 License

MIT License. See `LICENSE` for details.
