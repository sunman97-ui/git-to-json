from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
import google.generativeai as google_genai
from src.config import LLMSettings
from src.model_config import ModelConfigManager

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    @abstractmethod
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Yields response chunks as an async generator."""
        yield

class OpenAICompatibleProvider(LLMProvider):
    """
    Base provider for services that are API-compatible with OpenAI,
    including OpenAI itself, XAI, and Ollama.
    """
    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self._api_key = api_key
        self._base_url = base_url
        self._client: AsyncOpenAI | None = None

    async def __aenter__(self):
        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.close()

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        if not self._client:
            raise RuntimeError("Provider not properly initialized. Use async context manager.")
        
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class OpenAIProvider(OpenAICompatibleProvider):
    """Provider for OpenAI's models."""
    def __init__(self, api_key: str, model: str):
        super().__init__(model=model, api_key=api_key)

class XAIProvider(OpenAICompatibleProvider):
    """Provider for XAI's Grok model."""
    def __init__(self, api_key: str, model: str):
        super().__init__(model=model, api_key=api_key, base_url="https://api.x.ai/v1")

class OllamaProvider(OpenAICompatibleProvider):
    """Provider for local Ollama models."""
    def __init__(self, base_url: str, model: str):
        # Ollama API key is required but not used, so we provide a placeholder.
        super().__init__(model=model, api_key="ollama", base_url=base_url)

class GeminiProvider(LLMProvider):
    """Provider for Google's Gemini models."""
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        # Configure the client at the instance level
        google_genai.configure(api_key=self.api_key)

    async def __aenter__(self):
        # Gemini's library uses a global config, so no client to setup.
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # No client to close, so we can pass.
        pass

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        model = google_genai.GenerativeModel(self.model)
        async for chunk in await model.generate_content_async(prompt, stream=True):
            if chunk.text:
                yield chunk.text

# --- The Factory ---
def get_provider(choice: str, settings: LLMSettings) -> LLMProvider:
    """
    Factory function to get an instance of the chosen LLM provider.
    """
    ModelConfigManager.validate_provider_settings(choice, settings)
    model_name = ModelConfigManager.get_model_name(choice, settings)

    if choice == "openai":
        return OpenAIProvider(settings.openai_api_key, model=model_name)
    
    if choice == "xai":
        return XAIProvider(settings.xai_api_key, model=model_name)
    
    if choice == "gemini":
        return GeminiProvider(settings.gemini_api_key, model=model_name)
    
    if choice == "ollama":
        # Ollama's base_url might be dynamically determined or from config
        config = ModelConfigManager.get_config("ollama")
        base_url = settings.ollama_base_url or config.base_url
        if not base_url:
            raise ValueError("Ollama base URL not configured.")
        return OllamaProvider(base_url, model=model_name)
    
    raise ValueError(f"Unknown or unsupported provider: '{choice}'")