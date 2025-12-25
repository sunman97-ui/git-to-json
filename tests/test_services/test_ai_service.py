import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.config import LLMSettings
from src.services.ai_service import stream_ai_response


# --- Helper for Async Mocking ---
async def async_iter(items):
    """Helper to create an async generator from a list."""
    for item in items:
        yield item


# --- Fixtures ---


@pytest.fixture
def mock_console():
    return MagicMock()


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=LLMSettings)
    settings.openai_api_key = "test_openai_key"
    settings.xai_api_key = "test_xai_key"
    settings.gemini_api_key = "test_gemini_key"
    settings.ollama_base_url = "http://localhost:11434"
    return settings


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.__aenter__ = AsyncMock(return_value=provider)
    provider.__aexit__ = AsyncMock(return_value=None)
    provider.stream_response = MagicMock()  # Changed to MagicMock
    return provider


# --- Tests for stream_ai_response ---


@pytest.mark.asyncio
@patch("src.services.ai_service.get_provider")
@patch("src.services.ai_service.Live")
@patch("src.services.ai_service.Markdown")
async def test_stream_ai_response_success(
    mock_markdown,
    mock_live_cls,
    mock_get_provider,
    mock_console,
    mock_settings,
    mock_provider,
):
    """Test successful streaming of AI response."""
    mock_get_provider.return_value = mock_provider
    mock_provider.stream_response.return_value = async_iter(["Chunk 1", "Chunk 2"])

    mock_live_instance = mock_live_cls.return_value
    mock_live_instance.__enter__ = MagicMock(return_value=mock_live_instance)
    mock_live_instance.__exit__ = MagicMock(return_value=None)

    # Run the async function
    result = await stream_ai_response(
        mock_console, mock_settings, "openai", "test prompt"
    )

    assert result == "Chunk 1Chunk 2"
    mock_get_provider.assert_called_once_with("openai", mock_settings)
    mock_console.print.assert_any_call("\n[bold green]Connecting to OPENAI...[/]")
    mock_live_cls.assert_called_once()
    mock_live_instance.update.assert_called()


@pytest.mark.asyncio
@patch("src.services.ai_service.get_provider")
@patch("src.services.ai_service.logger")
async def test_stream_ai_response_failure(
    mock_logger, mock_get_provider, mock_console, mock_settings, mock_provider
):
    """Test error handling during AI response streaming."""
    mock_get_provider.return_value = mock_provider
    mock_provider.stream_response.side_effect = Exception("API error")

    # Run the async function
    result = await stream_ai_response(
        mock_console, mock_settings, "openai", "test prompt"
    )

    assert result is None
    mock_console.print.assert_any_call("\n[bold red]AI Execution Error:[/]\nAPI error")
    mock_logger.error.assert_called_once()
