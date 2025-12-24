import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from src.template_loader import load_templates, validate_schema, TEMPLATE_DIR

# --- validate_schema tests ---

def test_validate_schema_valid():
    """Test that a correct schema passes validation."""
    data = {
        "meta": {"name": "Test Template"},
        "execution": {"source": "staged"},
        "prompts": {"system": "sys", "user": "usr"}
    }
    assert validate_schema(data, "test.json") is True

def test_validate_schema_missing_toplevel_key():
    """Test validation fails if a required root key is missing."""
    data = {
        "meta": {"name": "Test"},
        # "execution" block is missing
        "prompts": {}
    }
    assert validate_schema(data, "test.json") is False

def test_validate_schema_missing_meta_name():
    """Test validation fails if meta block lacks a name."""
    data = {
        "meta": {}, # "name" key is missing
        "execution": {},
        "prompts": {}
    }
    assert validate_schema(data, "test.json") is False

# --- load_templates tests ---

@patch("src.template_loader.os.makedirs")
@patch("src.template_loader.os.path.exists")
def test_load_templates_creates_dir_if_missing(mock_exists, mock_makedirs):
    """Test that the template directory is created if it doesn't exist."""
    mock_exists.return_value = False
    
    templates = load_templates()
    
    assert templates == []
    mock_makedirs.assert_called_once_with(TEMPLATE_DIR)

@patch("src.template_loader.os.listdir")
@patch("src.template_loader.os.path.exists")
def test_load_templates_empty_dir(mock_exists, mock_listdir):
    """Test loading from an empty directory."""
    mock_exists.return_value = True
    mock_listdir.return_value = []
    
    templates = load_templates()
    assert templates == []

@patch("src.template_loader.json.load")
@patch("builtins.open", new_callable=mock_open)
@patch("src.template_loader.os.listdir")
@patch("src.template_loader.os.path.exists")
def test_load_templates_valid_file(mock_exists, mock_listdir, mock_file, mock_json_load):
    """Test loading a valid JSON template file."""
    mock_exists.return_value = True
    mock_listdir.return_value = ["template1.json"]
    
    valid_data = {
        "meta": {"name": "My Template"},
        "execution": {},
        "prompts": {}
    }
    mock_json_load.return_value = valid_data
    
    templates = load_templates()
    
    assert len(templates) == 1
    assert templates[0]["meta"]["name"] == "My Template"
    assert templates[0]["_filename"] == "template1.json"
    
    # Verify file open call (using os.path.join for cross-platform path separator)
    expected_path = os.path.join(TEMPLATE_DIR, "template1.json")
    mock_file.assert_called_with(expected_path, 'r', encoding='utf-8')

@patch("src.template_loader.logger")
@patch("src.template_loader.json.load")
@patch("builtins.open", new_callable=mock_open)
@patch("src.template_loader.os.listdir")
@patch("src.template_loader.os.path.exists")
def test_load_templates_invalid_schema(mock_exists, mock_listdir, mock_file, mock_json_load, mock_logger):
    """Test that files with invalid schemas are skipped and logged."""
    mock_exists.return_value = True
    mock_listdir.return_value = ["bad_schema.json"]
    
    # Missing 'prompts'
    invalid_data = {
        "meta": {"name": "Bad"},
        "execution": {}
    }
    mock_json_load.return_value = invalid_data
    
    templates = load_templates()
    
    assert templates == []
    mock_logger.warning.assert_called()

@patch("src.template_loader.os.listdir")
@patch("src.template_loader.os.path.exists")
def test_load_templates_ignores_non_json(mock_exists, mock_listdir):
    """Test that non-JSON files are ignored."""
    mock_exists.return_value = True
    mock_listdir.return_value = ["readme.txt", "script.py"]
    
    templates = load_templates()
    
    assert templates == []