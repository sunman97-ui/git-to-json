from typing import Dict, TYPE_CHECKING, List, Literal, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from .config import LLMSettings

@dataclass
class ProviderConfig:
    model_name: str
    description: str
    requires_api_key: bool = True
    base_url: Optional[str] = None

class ModelConfigManager:
    _CONFIGS: Dict[str, ProviderConfig] = {
        "openai": ProviderConfig(
            model_name="gpt-5-mini",
            description="General purpose model with high reasoning capabilities."
        ),
        "xai": ProviderConfig(
            model_name="grok-4-1-fast-reasoning",
            description="Optimized for logic and complex deduction tasks."
        ),
        "gemini": ProviderConfig(
            model_name="gemini-2.5-pro",
            description="Multimodal model with large context window."
        ),
        "ollama": ProviderConfig(
            model_name="llama3.1:8b",
            description="Local inference provider.",
            requires_api_key=False,
            base_url="http://localhost:11434/v1" # Default for local Ollama
        )
    }

    @classmethod
    def get_config(cls, provider_name: str) -> ProviderConfig:
        if provider_name not in cls._CONFIGS:
            raise ValueError(f"Provider '{provider_name}' not supported")
        return cls._CONFIGS[provider_name]

    @classmethod
    def get_model_name(cls, provider_name: str, settings: "LLMSettings | None" = None) -> str:
        config = cls.get_config(provider_name)
        
        # Special handling for Ollama to respect runtime settings
        if provider_name == "ollama" and settings and hasattr(settings, "ollama_model") and settings.ollama_model:
            return settings.ollama_model
        
        return config.model_name

    @classmethod
    def validate_provider_settings(cls, provider_name: str, settings: "LLMSettings") -> None:
        config = cls.get_config(provider_name)
        
        if config.requires_api_key:
            api_key = getattr(settings, f"{provider_name}_api_key", None)
            if not api_key:
                raise ValueError(f"Missing {provider_name.upper()}_API_KEY in environment or settings.")
