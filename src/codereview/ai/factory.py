"""Factory for creating AI providers."""

from codereview.ai.base import BaseAIProvider
from codereview.ai.provider import LiteLLMProvider


# pylint: disable=too-few-public-methods
class AIFactory:
    """Factory class to create the requested AI provider."""

    @staticmethod
    def create(provider_name: str, model_name: str | None = None) -> BaseAIProvider:
        """Create a provider instance.

        Args:
            provider_name: One of ("local", "cloud").
            model_name: Optional model override.

        Returns:
            A BaseAIProvider instance.

        Raises:
            ValueError: If the provider name is unknown.
        """
        provider_name = provider_name.lower()

        if provider_name in ("local", "ollama"):
            # For local (Ollama) provider, we map it to LiteLLM with Prefix
            model = model_name or "llama3"
            if not model.startswith("ollama/"):
                model = f"ollama/{model}"
            return LiteLLMProvider(model=model, api_base="http://localhost:11434")

        if provider_name in ("cloud", "litellm"):
            if model_name:
                return LiteLLMProvider(model=model_name)
            return LiteLLMProvider()

        raise ValueError(f"Unknown AI provider: {provider_name}")
