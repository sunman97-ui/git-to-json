import pytest
import json
import os
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
from src.utils import (
    CONFIG_FILE,
    count_tokens, 
    setup_logging, 
    load_config, 
    save_path_to_config, 
    save_data_to_file
)

# --- count_tokens ---

@patch("src.utils.tiktoken")
def test_count_tokens_success(mock_tiktoken):
    """Test token counting with valid tiktoken response."""
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
    mock_tiktoken.encoding_for_model.return_value = mock_encoding
    
    count = count_tokens("some text", model="gpt-4")
    assert count == 5
    mock_tiktoken.encoding_for_model.assert_called_with("gpt-4")

@patch("src.utils.tiktoken")
def test_count_tokens_fallback(mock_tiktoken):
    """Test fallback logic when tiktoken.encoding_for_model fails."""
    # Simulate encoding_for_model failing, which is the scenario for the fallback.
    mock_tiktoken.encoding_for_model.side_effect = Exception("Model not found")
    
    # Mock the behavior of the fallback encoding.
    mock_fallback_encoding = MagicMock()
    mock_fallback_encoding.encode.return_value = [1, 2, 3]  # Simulate encoding to 3 tokens.
    mock_tiktoken.get_encoding.return_value = mock_fallback_encoding

    text_to_encode = "This text will be encoded by the fallback."
    token_count = count_tokens(text_to_encode)
    
    # Verify that the fallback encoding was requested.
    mock_tiktoken.get_encoding.assert_called_once_with("cl100k_base")
    # Verify that the text was encoded using the fallback.
    mock_fallback_encoding.encode.assert_called_once_with(text_to_encode, errors='replace')
    # Verify that the final count is the length of the mocked encoded output.
    assert token_count == 3

# --- setup_logging ---

@patch("src.utils.RotatingFileHandler")
@patch("src.utils.logging")
def test_setup_logging(mock_logging, mock_handler):
    """Test that logging is configured correctly."""
    logger = setup_logging()
    
    mock_logging.basicConfig.assert_called_once()
    mock_logging.getLogger.assert_called_with("GitToJson")
    assert logger == mock_logging.getLogger.return_value

# --- load_config ---

@patch("src.utils.CONFIG_FILE")
@patch("builtins.open", new_callable=mock_open, read_data='{"saved_paths": ["/test/path"]}')
def test_load_config_exists(mock_file, mock_config_path):
    """Test loading an existing config file."""
    mock_config_path.is_file.return_value = True
    
    config = load_config()
    assert config == {"saved_paths": ["/test/path"]}
    # Note: We can't easily assert the exact call to open(CONFIG_FILE) because CONFIG_FILE is a mock now
    assert mock_file.called

@patch("src.utils.CONFIG_FILE")
def test_load_config_missing(mock_config_path):
    """Test loading when config file is missing."""
    mock_config_path.is_file.return_value = False
    
    config = load_config()
    assert config == {"saved_paths": []}

@patch("src.utils.CONFIG_FILE")
@patch("builtins.open", side_effect=IOError("Permission Denied"))
def test_load_config_error(mock_file, mock_config_path):
    """Test loading when file read fails."""
    mock_config_path.is_file.return_value = True
    
    config = load_config()
    assert config == {"saved_paths": []}

# --- save_path_to_config ---

@patch("src.utils.json.dump")
@patch("src.utils.load_config")
@patch("builtins.open", new_callable=mock_open)
def test_save_path_to_config_new(mock_file, mock_load, mock_dump):
    """Test saving a new path."""
    mock_load.return_value = {"saved_paths": ["/old/path"]}
    
    save_path_to_config("/new/path")
    
    # Verify we opened the file for writing
    mock_file.assert_called_with(CONFIG_FILE, 'w', encoding='utf-8')
    
    # Verify json.dump was called with updated list
    args, _ = mock_dump.call_args
    saved_data = args[0]
    assert len(saved_data["saved_paths"]) == 2
    assert "/old/path" in saved_data["saved_paths"]
    # We can check if the new path is present (normalized or not)
    # Assuming the function normalizes, we check if *some* form of it is there
    assert any("/new/path" in p or "\\new\\path" in p for p in saved_data["saved_paths"])

@patch("src.utils.json.dump")
@patch("src.utils.load_config")
@patch("builtins.open", new_callable=mock_open)
def test_save_path_to_config_duplicate(mock_file, mock_load, mock_dump):
    """Test that duplicate paths are not added."""
    # Mock normpath to ensure consistent comparison
    with patch("src.utils.os.path.normpath", side_effect=lambda x: x):
        mock_load.return_value = {"saved_paths": ["/existing/path"]}
        
        save_path_to_config("/existing/path")
        
        mock_file.assert_not_called()
        mock_dump.assert_not_called()

# --- save_data_to_file ---

@patch("src.utils.Path.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_save_data_to_file_success(mock_file, mock_mkdir):
    """Test successful file saving."""
    # Create a mock object that behaves like a Pydantic model
    mock_item = MagicMock()
    mock_item.model_dump.return_value = {"key": "value"}
    data = [mock_item]
    
    result = save_data_to_file(data, "output/data.json")
    
    assert result is True
    mock_mkdir.assert_called()
    assert mock_file.called

@patch("builtins.open", side_effect=IOError("Disk Error"))
def test_save_data_to_file_failure(mock_file):
    """Test handling of file save errors."""
    
    result = save_data_to_file([], "output/data.json")
    assert result is False