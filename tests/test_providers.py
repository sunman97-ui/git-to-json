import pytest
import asyncio
from unittest.mock import patch, MagicMock, ANY, AsyncMock
from src.providers import get_provider, OpenAIProvider, XAIProvider, GeminiProvider, OllamaProvider
from src.config import LLMSettings

# --- Helper for Async Mocking ---
async def async_iter(items):
    """Helper to create an async generator from a list."""
    for item in items:
        yield item

# --- Factory Tests (get_provider) ---

@patch("src.providers.AsyncOpenAI", autospec=True)
def test_get_provider_openai(mock_openai):
    """Test creating OpenAI provider with valid settings."""
    settings = LLMSettings(openai_api_key="sk-test")
    provider = get_provider("openai", settings)
    
    assert isinstance(provider, OpenAIProvider)
    # Client initialization is now handled by the async context manager.

@patch("src.providers.AsyncOpenAI", autospec=True)
def test_get_provider_xai(mock_openai):
    """Test creating XAI provider with valid settings."""
    settings = LLMSettings(xai_api_key="xai-test")
    provider = get_provider("xai", settings)
    
    assert isinstance(provider, XAIProvider)
    # Client initialization is now handled by the async context manager.

@patch("src.providers.google_genai")
def test_get_provider_gemini(mock_genai):
    """Test creating Gemini provider with valid settings."""
    settings = LLMSettings(gemini_api_key="gemini-test")
    provider = get_provider("gemini", settings)
    
    assert isinstance(provider, GeminiProvider)
    mock_genai.configure.assert_called_with(api_key="gemini-test")


@patch("src.providers.AsyncOpenAI", autospec=True)
def test_get_provider_ollama(mock_openai):
    """Test creating Ollama provider."""
    settings = LLMSettings(ollama_base_url="http://host:1234", ollama_model="llama3")
    provider = get_provider("ollama", settings)
    
    assert isinstance(provider, OllamaProvider)
    # Client initialization is now handled by the async context manager.

def test_get_provider_missing_keys():
    """Test that missing API keys raise ValueError."""
    # Use a mock object to simulate empty settings, avoiding .env file interference
    settings = MagicMock()
    settings.openai_api_key = None
    settings.xai_api_key = None
    settings.gemini_api_key = None
    
    with pytest.raises(ValueError, match="Missing OPENAI_API_KEY"):
        get_provider("openai", settings)
        
    with pytest.raises(ValueError, match="Missing XAI_API_KEY"):
        get_provider("xai", settings)
        
    with pytest.raises(ValueError, match="Missing GEMINI_API_KEY"):
        get_provider("gemini", settings)

def test_get_provider_unknown():
    """Test that unknown provider names raise ValueError."""
    settings = LLMSettings()
    with pytest.raises(ValueError):
        get_provider("mystery_ai", settings)

# --- Streaming Tests (Async) ---

def test_openai_stream_response():
    """Test OpenAI streaming logic."""
    # Mock the chunk structure returned by OpenAI SDK
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Hello AI"

    with patch("src.providers.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        # The client's 'close' method needs to be an awaitable mock
        mock_instance.close = AsyncMock()

        # Mock the create method to return our async iterator
        # It must be an async function (coroutine) because the code awaits it
        async def mock_create(*args, **kwargs):
            return async_iter([mock_chunk])
        mock_instance.chat.completions.create = mock_create
        
        provider = OpenAIProvider("key", "gpt-4")
        
        # Wrapper to run async code in sync test
        async def run():
            chunks = []
            async with provider:
                async for chunk in provider.stream_response("prompt"):
                    chunks.append(chunk)
            return chunks

        result = asyncio.run(run())
        assert result == ["Hello AI"]

def test_gemini_stream_response():
    """Test Gemini streaming logic."""
    # Mock the chunk structure returned by Google GenAI SDK
    mock_chunk = MagicMock()
    mock_chunk.text = "Hello Gemini"

    with patch("src.providers.google_genai") as mock_genai:
        mock_model = mock_genai.GenerativeModel.return_value
        
        async def mock_generate(*args, **kwargs):
            return async_iter([mock_chunk])
        mock_model.generate_content_async.side_effect = mock_generate
        
        provider = GeminiProvider("key", "gemini-pro")
        
        async def run():
            chunks = []
            async for chunk in provider.stream_response("prompt"):
                chunks.append(chunk)
            return chunks

        result = asyncio.run(run())
        assert result == ["Hello Gemini"]

# Note: XAIProvider and OllamaProvider share the exact same logic/SDK as OpenAIProvider.
# The factory tests ensure they are initialized correctly. 
# The OpenAI stream test covers the underlying implementation logic they share.