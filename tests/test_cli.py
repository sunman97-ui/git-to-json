from unittest.mock import patch
from src.cli import get_repository_path

@patch('src.cli.save_path_to_config')
@patch('src.cli.questionary')
@patch('src.cli.load_config')
def test_get_repository_path_select_saved(mock_load_config, mock_questionary, mock_save_config):
    """Test selecting a saved path."""
    # ARRANGE
    mock_load_config.return_value = {"saved_paths": ["/path/one", "/path/two"]}
    mock_questionary.select.return_value.ask.return_value = "/path/one"

    # ACT
    selected_path = get_repository_path()

    # ASSERT
    assert selected_path == "/path/one"
    mock_questionary.select.assert_called_once()
    mock_save_config.assert_not_called()

@patch('src.cli.os')
@patch('src.cli.save_path_to_config')
@patch('src.cli.questionary')
@patch('src.cli.load_config')
def test_get_repository_path_enter_new_path_from_menu(mock_load_config, mock_questionary, mock_save_config, mock_os):
    """Test entering a new path when saved paths exist."""
    # ARRANGE
    mock_load_config.return_value = {"saved_paths": ["/path/one"]}
    mock_questionary.select.return_value.ask.return_value = "-- Enter a New Path --"
    mock_questionary.path.return_value.ask.return_value = "/new/path"
    mock_os.path.exists.return_value = True
    mock_os.path.isdir.return_value = True

    # ACT
    selected_path = get_repository_path()

    # ASSERT
    assert selected_path == "/new/path"
    mock_questionary.select.assert_called_once()
    mock_questionary.path.assert_called_once()
    mock_save_config.assert_called_once_with("/new/path")

@patch('src.cli.os')
@patch('src.cli.save_path_to_config')
@patch('src.cli.questionary')
@patch('src.cli.load_config')
def test_get_repository_path_no_saved_paths(mock_load_config, mock_questionary, mock_save_config, mock_os):
    """Test entering a path when no saved paths exist."""
    # ARRANGE
    mock_load_config.return_value = {}
    mock_questionary.path.return_value.ask.return_value = "/new/path"
    mock_os.path.exists.return_value = True
    mock_os.path.isdir.return_value = True

    # ACT
    selected_path = get_repository_path()

    # ASSERT
    assert selected_path == "/new/path"
    mock_questionary.select.assert_not_called()
    mock_questionary.path.assert_called_once()
    mock_save_config.assert_called_once_with("/new/path")
    
@patch('src.cli.os')
@patch('src.cli.save_path_to_config')
@patch('src.cli.questionary')
@patch('src.cli.load_config')
def test_get_repository_path_enter_new_path_with_quotes(mock_load_config, mock_questionary, mock_save_config, mock_os):
    """Test entering a new path that has quotes and ensuring they are stripped."""
    # ARRANGE
    mock_load_config.return_value = {}
    mock_questionary.path.return_value.ask.return_value = "'/new/path/quoted'"
    mock_os.path.exists.return_value = True
    mock_os.path.isdir.return_value = True

    # ACT
    selected_path = get_repository_path()

    # ASSERT
    assert selected_path == "/new/path/quoted"
    mock_questionary.select.assert_not_called()
    mock_save_config.assert_called_once_with("/new/path/quoted")

@patch('src.cli.save_path_to_config')
@patch('src.cli.questionary')
@patch('src.cli.load_config')
def test_get_repository_path_cancel_selection(mock_load_config, mock_questionary, mock_save_config):
    """Test cancelling the path selection."""
    # ARRANGE
    mock_load_config.return_value = {}
    mock_questionary.path.return_value.ask.return_value = None

    # ACT
    selected_path = get_repository_path()

    # ASSERT
    assert selected_path is None
    mock_save_config.assert_not_called()