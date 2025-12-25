from unittest.mock import patch, mock_open
from src.services.output_handler import save_prompt_to_file, copy_to_clipboard

# --- Tests for save_prompt_to_file ---


@patch("builtins.open", new_callable=mock_open)
def test_save_prompt_to_file_success(mock_file):
    """Test successful saving of prompt to file."""
    prompt_text = "Test prompt content"
    filepath = "/tmp/test_prompt.txt"

    result = save_prompt_to_file(prompt_text, filepath)

    assert result is True
    mock_file.assert_called_once_with(filepath, "w", encoding="utf-8")
    mock_file().write.assert_called_once_with(prompt_text)


@patch("builtins.open", new_callable=mock_open)
@patch("src.services.output_handler.logger")
def test_save_prompt_to_file_failure(mock_logger, mock_file):
    """Test handling of IOError during file saving."""
    mock_file.side_effect = IOError("Permission denied")

    prompt_text = "Test prompt content"
    filepath = "/tmp/test_prompt.txt"

    result = save_prompt_to_file(prompt_text, filepath)

    assert result is False
    mock_logger.error.assert_called_once()


# --- Tests for copy_to_clipboard ---


@patch("src.services.output_handler.pyperclip")
def test_copy_to_clipboard_success(mock_pyperclip):
    """Test successful copying to clipboard."""
    text = "Text to copy"

    result = copy_to_clipboard(text)

    assert result is True
    mock_pyperclip.copy.assert_called_once_with(text)


@patch("src.services.output_handler.pyperclip")
@patch("src.services.output_handler.logger")
def test_copy_to_clipboard_failure(mock_logger, mock_pyperclip):
    """Test handling of exceptions during clipboard operation."""
    mock_pyperclip.copy.side_effect = Exception("Clipboard unavailable")

    text = "Text to copy"

    result = copy_to_clipboard(text)

    assert result is False
    mock_logger.error.assert_called_once()
