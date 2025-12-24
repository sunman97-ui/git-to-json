import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError

class LLMSettings(BaseSettings):
    """
    Validates environment variables for LLM providers.
    """
    # Keys are optional because the user might only want Local/Ollama
    openai_api_key: str | None = None
    xai_api_key: str | None = None
    gemini_api_key: str | None = None
    
    # Ollama Defaults (Local)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b" 

    # We tell Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

def load_settings():
    try:
        return LLMSettings()
    except ValidationError as e:
        print(f"Configuration Error: {e}")
        return LLMSettings() # Return defaults if file missing