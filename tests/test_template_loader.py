from unittest.mock import patch, MagicMock
from src.template_loader import load_templates

# --- Tests for load_templates ---


@patch("src.template_loader.TEMPLATE_DIR")
def test_load_templates_creates_dir_if_missing(mock_template_dir):
    """Test that the template directory is created if it doesn't exist."""
    # Mock pathlib.Path.is_dir behavior
    mock_template_dir.is_dir.return_value = False

    templates = load_templates()

    assert templates == []
    mock_template_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)


@patch("src.template_loader.TEMPLATE_DIR")
def test_load_templates_empty_dir(mock_template_dir):
    """Test loading from an empty directory."""
    mock_template_dir.is_dir.return_value = True
    mock_template_dir.glob.return_value = []

    templates = load_templates()
    assert templates == []


@patch("src.template_loader.PromptTemplate")  # Mock the Pydantic model
@patch("src.template_loader.json.load")
@patch("src.template_loader.TEMPLATE_DIR")
def test_load_templates_valid_file(mock_template_dir, mock_json_load, mock_prompt_cls):
    """Test loading a valid JSON template file."""
    mock_template_dir.is_dir.return_value = True

    # Mock a file path object yielded by glob
    mock_path = MagicMock()
    mock_template_dir.glob.return_value = [mock_path]

    valid_data = {"meta": {"name": "My Template"}, "execution": {}, "prompts": {}}
    mock_json_load.return_value = valid_data

    # Setup the mock object returned by PromptTemplate.model_validate(data)
    mock_instance = MagicMock()
    mock_instance.meta.name = "My Template"
    # The loader likely attaches the filename to the object or a wrapper
    mock_instance._filename = "template1.json"
    mock_prompt_cls.model_validate.return_value = mock_instance

    templates = load_templates()

    assert len(templates) == 1
    # Verify we got the object back
    assert templates[0].meta.name == "My Template"

    # Verify Pydantic model was initialized with the data
    mock_prompt_cls.model_validate.assert_called_with(valid_data)

    # Verify file open call on the path object
    mock_path.open.assert_called_with("r", encoding="utf-8")


@patch("src.template_loader.PromptTemplate")
@patch("src.template_loader.logger")
@patch("src.template_loader.json.load")
@patch("src.template_loader.TEMPLATE_DIR")
def test_load_templates_invalid_schema(
    mock_template_dir, mock_json_load, mock_logger, mock_prompt_cls
):
    """Test that files with invalid schemas are skipped and logged."""
    mock_template_dir.is_dir.return_value = True
    mock_path = MagicMock()
    mock_template_dir.glob.return_value = [mock_path]

    # Simulate Pydantic validation error
    mock_prompt_cls.model_validate.side_effect = Exception("Validation Error")

    templates = load_templates()

    assert templates == []
    # Ensure the error was logged
    assert mock_logger.warning.called or mock_logger.error.called


@patch("src.template_loader.TEMPLATE_DIR")
def test_load_templates_ignores_non_json(mock_template_dir):
    """Test that glob only picks up json files (implicit in glob call)."""
    mock_template_dir.is_dir.return_value = True
    # If glob returns empty, it means non-json files were ignored by the glob pattern
    mock_template_dir.glob.return_value = []

    templates = load_templates()

    assert templates == []
