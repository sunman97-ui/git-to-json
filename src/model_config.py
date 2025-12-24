from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import LLMSettings

# Top-level key is the 'provider_name'
MODEL_CONFIG: Dict[str, Dict[str, str]] = {
    "openai": {
        "model_name": "gpt-5-mini",
        "description": "General purpose model with high reasoning capabilities."
    },
    "xai": {
        "model_name": "grok-4-1-fast-reasoning",
        "description": "Optimized for logic and complex deduction tasks."
    },
    "gemini": {
        "model_name": "gemini-2.5-pro",
        "description": "Multimodal model with large context window."
    },
    "ollama": {
        "model_name": "llama3.1:8b",  # Default fallback if settings.ollama_model is missing
        "description": "Local inference provider."
    }
}

def get_model_name(provider_name: str, settings: "LLMSettings | None" = None) -> str:
    """
    Retrieves the model name for a given provider.
    
    Args:
        provider_name: The key identifying the provider (e.g., 'openai').
        settings: Optional settings object (expected to have 'ollama_model' attribute).
        
    Returns:
        The model string identifier, or a default if provider is not found.
    """
    # 1. Get the config for the specific provider
    config = MODEL_CONFIG.get(provider_name)
    
    if not config:
        raise ValueError(f"Provider '{provider_name}' is not defined in model_config.py")

    # 2. Special handling for Ollama to respect runtime settings
    if provider_name == "ollama" and settings and hasattr(settings, "ollama_model") and settings.ollama_model:
        return settings.ollama_model

    # 3. Return the static configuration
    return config["model_name"]