# src/constants.py

"""
Central configuration for application constants, magic numbers, and UI strings.
Avoids circular imports and enforces DRY (Don't Repeat Yourself).
"""

# --- File System Constants ---
OUTPUT_ROOT_DIR = "Extracted JSON"
LOG_FILE_NAME = "git_extraction.log"

# --- Extraction Limits ---
MAX_COMMITS_TO_FETCH = 1000  # Safety cap to prevent memory overload in core.py

# --- Menu Options (Single Source of Truth) ---
# These strings are displayed in the TUI and used for logic switching in the CLI.
OPT_STAGED = "📝 Staged Changes (Pre-Commit Analysis)"
OPT_ALL = "📜 All History"
OPT_LIMIT = "🔢 Last N Commits"
OPT_DATE = "📅 Date Range"
OPT_AUTHOR = "👤 By Author"

# --- Menu Choices Mapping ---
# Maps the user-facing display string to the internal folder naming convention.
EXTRACTION_MODE_MAPPING = {
    OPT_STAGED: "Staged_Changes",
    OPT_ALL: "All_History",
    OPT_LIMIT: "Last_N_Commits",
    OPT_DATE: "Date_Range",
    OPT_AUTHOR: "By_Author",
}
