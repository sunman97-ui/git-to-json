from abc import ABC, abstractmethod
from typing import AsyncGenerator
from openai import AsyncOpenAI
from google import genai as google_genai
from src.config import LLMSettings
from src.model_config import get_model_name

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
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
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
    model_name = get_model_name(choice, settings)

    if choice == "openai":
        if not settings.openai_api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env file.")
        return OpenAIProvider(settings.openai_api_key, model=model_name)
    
    if choice == "xai":
        if not settings.xai_api_key:
            raise ValueError("Missing XAI_API_KEY in .env file.")
        return XAIProvider(settings.xai_api_key, model=model_name)
    
    if choice == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env file.")
        return GeminiProvider(settings.gemini_api_key, model=model_name)
    
    if choice == "ollama":
        return OllamaProvider(settings.ollama_base_url, model=model_name)
    
    raise ValueError(f"Unknown or unsupported provider: '{choice}'")