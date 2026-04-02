"""Factory function for creating AI providers."""

from codereview.ai.base import BaseAIProvider
from codereview.ai.provider import LiteLLMProvider


def create_ai_provider(
    provider_name: str,
    model_name: str | None = None,
    api_base: str | None = None,
) -> BaseAIProvider:
    """Create and return a configured AI provider instance.

    Args:
        provider_name: AI Provider (e.g. "openai", "anthropic", "ollama").
        model_name: Optional model override.
        api_base: Optional API base URL.

    Returns:
        A BaseAIProvider instance.
    """
    provider_name = provider_name.lower().strip()
    model = model_name or "llama3"

    # Special handling for Ollama
    if provider_name in ("ollama", "local"):
        if not model.startswith("ollama/"):
            model = f"ollama/{model}"
        return LiteLLMProvider(
            model=model,
            api_base=api_base or "http://localhost:11434",
        )

    # For Cloud/Generic carriers via LiteLLM
    if provider_name in ("cloud", "litellm"):
        # If generic 'cloud' or 'litellm' is used, we just return the provider
        # and let LiteLLM infer from the model name (which should include prefix)
        return LiteLLMProvider(model=model, api_base=api_base)

    # If it's a specific provider name (e.g. "openai"), we ensure the prefix
    if "/" not in model:
        model = f"{provider_name}/{model}"

    return LiteLLMProvider(model=model, api_base=api_base)
