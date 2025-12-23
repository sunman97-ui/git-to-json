from abc import ABC, abstractmethod
from typing import AsyncGenerator
import os
from openai import AsyncOpenAI
import google.generativeai as genai
from src.config import LLMSettings

class LLMProvider(ABC):
    @abstractmethod
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def stream_response(self, prompt: str):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class XAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        # XAI (Grok) is API-compatible with OpenAI
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url="https://api.x.ai/v1"
        )
        self.model = "grok-4-1-fast-reasoning"

    async def stream_response(self, prompt: str):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")

    async def stream_response(self, prompt: str):
        response = await self.model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            yield chunk.text

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        # Ollama is ALSO API-compatible with OpenAI client
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama" # Required but unused by Ollama
        )
        self.model = model

    async def stream_response(self, prompt: str):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

# --- The Factory ---
def get_provider(choice: str, settings: LLMSettings) -> LLMProvider:
    if choice == "openai":
        if not settings.openai_api_key: raise ValueError("Missing OPENAI_API_KEY in .env")
        return OpenAIProvider(settings.openai_api_key)
    
    elif choice == "xai":
        if not settings.xai_api_key: raise ValueError("Missing XAI_API_KEY in .env")
        return XAIProvider(settings.xai_api_key)
    
    elif choice == "gemini":
        if not settings.gemini_api_key: raise ValueError("Missing GEMINI_API_KEY in .env")
        return GeminiProvider(settings.gemini_api_key)
    
    elif choice == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    
    raise ValueError(f"Unknown provider: {choice}")