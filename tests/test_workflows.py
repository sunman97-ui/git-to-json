# tests/test_workflows.py
import pytest
from unittest.mock import MagicMock, patch

from src.workflows import (
    TemplateWorkflowHandler,
    RawExtractionWorkflowHandler,
    InteractiveWorkflowHandler,
    DirectExecutionWorkflowHandler,
    resolve_output_path,
    OPT_STAGED,  # Import constants used in tests
)
from src.schemas import PromptTemplate, TemplateMeta, TemplateExecution, TemplatePrompts


# --- Fixtures ---


@pytest.fixture
def mock_engine():
    """Mock of the AuditEngine."""
    return MagicMock()


@pytest.fixture
def mock_console():
    """Mock of the Rich Console."""
    return MagicMock()


@pytest.fixture
def mock_tui():
    """Mock of the TUI module."""
    return MagicMock()


@pytest.fixture
def mock_template_obj():
    """A mock PromptTemplate object."""
    tmpl = MagicMock(spec=PromptTemplate)
    tmpl.meta = MagicMock(spec=TemplateMeta)
    tmpl.execution = MagicMock(spec=TemplateExecution)
    tmpl.prompts = MagicMock(spec=TemplatePrompts)

    tmpl.meta.name = "Test Template"
    tmpl.execution.source = "history"
    tmpl.execution.limit = 5
    return tmpl


# --- Test resolve_output_path ---


@patch("src.workflows.os.getcwd", return_value="/fake/cwd")
@patch("src.workflows.os.path.join")
@patch("src.workflows.os.makedirs")
def test_resolve_output_path(mock_makedirs, mock_join, mock_getcwd):
    """Test that the output path is resolved correctly."""
    mock_join.side_effect = lambda *args: "/".join(args)

    resolve_output_path("test.json", subfolder="MySubfolder")

    # Check that the target directory is created
    mock_makedirs.assert_called_once_with(
        "/fake/cwd/Extracted JSON/MySubfolder", exist_ok=True
    )

    # Check that the final path is joined correctly
    mock_join.assert_called_with("/fake/cwd/Extracted JSON/MySubfolder", "test.json")


# --- TemplateWorkflowHandler Tests ---


def test_template_workflow_clipboard(
    mock_engine, mock_console, mock_tui, mock_template_obj
):
    """Test the template workflow with the clipboard action."""
    handler = TemplateWorkflowHandler(mock_engine, mock_console, mock_tui)

    # Setup mocks
    mock_engine.fetch_data.return_value = ["some data"]
    mock_engine.build_prompt.return_value = "Final Prompt"
    mock_tui.get_prompt_handling_choice.return_value = "clipboard"

    handler.execute(
        "/repo", templates=[mock_template_obj], selection_name="Test Template"
    )

    mock_engine.fetch_data.assert_called_once()
    mock_engine.build_prompt.assert_called_once_with(mock_template_obj, ["some data"])
    mock_engine.copy_to_clipboard.assert_called_once_with("Final Prompt")


def test_template_workflow_file(mock_engine, mock_console, mock_tui, mock_template_obj):
    """Test the template workflow with the file save action."""
    handler = TemplateWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_engine.fetch_data.return_value = ["some data"]
    mock_engine.build_prompt.return_value = "Final Prompt"
    mock_tui.get_prompt_handling_choice.return_value = "file"
    mock_tui.get_prompt_filename.return_value = "prompt.txt"

    handler.execute(
        "/repo", templates=[mock_template_obj], selection_name="Test Template"
    )

    mock_engine.save_prompt_to_file.assert_called_once_with(
        "Final Prompt", "prompt.txt"
    )


def test_template_workflow_execute(
    mock_engine, mock_console, mock_tui, mock_template_obj
):
    """Test the template workflow with the AI execution action."""
    handler = TemplateWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_engine.fetch_data.return_value = ["some data"]
    mock_engine.build_prompt.return_value = "Final Prompt"
    mock_tui.get_prompt_handling_choice.return_value = "execute"
    mock_tui.select_llm_provider.return_value = "openai"

    handler.execute(
        "/repo", templates=[mock_template_obj], selection_name="Test Template"
    )

    mock_engine.execute_ai_stream.assert_called_once_with("openai", "Final Prompt")


# --- RawExtractionWorkflowHandler Tests ---


@patch("src.workflows.resolve_output_path", return_value="/fake/path/out.json")
def test_raw_extraction_workflow(mock_resolve, mock_engine, mock_console, mock_tui):
    """Test the raw extraction workflow."""
    handler = RawExtractionWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_tui.get_raw_extraction_mode.return_value = OPT_STAGED
    mock_tui.get_raw_extraction_filters.return_value = {"mode": "staged"}
    mock_tui.get_output_filename.return_value = "out.json"
    mock_tui.confirm_save.return_value = True

    handler.execute("/repo")

    mock_resolve.assert_called_once_with("out.json", "Staged_Changes")
    mock_tui.confirm_save.assert_called_once_with(
        "/fake/path/out.json", "matching items"
    )
    mock_engine.execute_raw_extraction.assert_called_once_with(
        "/repo", {"mode": "staged"}, "/fake/path/out.json"
    )


# --- InteractiveWorkflowHandler Tests ---


@patch("src.workflows.resolve_output_path", return_value="/fake/path/out.json")
def test_interactive_workflow_extract(
    mock_resolve, mock_engine, mock_console, mock_tui
):
    """Test the interactive workflow with the extract action."""
    handler = InteractiveWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_tui.select_commits_interactively.return_value = ["hash1"]
    mock_engine.fetch_data.return_value = ["some data"]
    mock_tui.get_interactive_output_choice.return_value = "extract"
    mock_tui.get_output_filename.return_value = "out.json"

    handler.execute("/repo")

    mock_engine.fetch_data.assert_called_once_with(
        "/repo", {"mode": "hashes", "hashes": ["hash1"]}
    )
    mock_resolve.assert_called_once_with("out.json", "Interactive")
    mock_engine.execute_raw_extraction.assert_called_once_with(
        "/repo", {"mode": "hashes", "hashes": ["hash1"]}, "/fake/path/out.json"
    )


def test_interactive_workflow_ai(mock_engine, mock_console, mock_tui):
    """Test the interactive workflow with the AI action."""
    handler = InteractiveWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_tui.select_commits_interactively.return_value = ["hash1"]
    mock_engine.fetch_data.return_value = ["some data"]
    mock_tui.get_interactive_output_choice.return_value = "ai"
    mock_engine.build_prompt.return_value = "AI Prompt"
    mock_tui.select_llm_provider.return_value = "openai"

    handler.execute("/repo")

    mock_engine.build_prompt.assert_called_once()
    mock_engine.execute_ai_stream.assert_called_once_with("openai", "AI Prompt")


# --- DirectExecutionWorkflowHandler Tests ---


def test_direct_execution_workflow(mock_engine, mock_console, mock_tui):
    """Test the direct AI execution workflow."""
    handler = DirectExecutionWorkflowHandler(mock_engine, mock_console, mock_tui)

    mock_tui.select_llm_provider.return_value = "openai"
    mock_tui.get_user_prompt.return_value = "User question"

    handler.execute("/repo")  # Repo path is ignored in this handler

    mock_engine.execute_ai_stream.assert_called_once_with("openai", "User question")
