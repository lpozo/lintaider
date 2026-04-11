"""Provider registry used by onboarding and runtime provider setup."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:  # pylint: disable=too-many-instance-attributes
    """Declarative metadata for an AI provider."""

    provider_id: str
    display_name: str
    env_var: str | None
    requires_api_key: bool
    default_model: str
    default_api_base: str | None = None
    model_list_endpoint: str | None = None
    recommended_models: tuple[str, ...] = ()


PROVIDER_SPECS: dict[str, ProviderSpec] = {
    "ollama": ProviderSpec(
        provider_id="ollama",
        display_name="Ollama (Local)",
        env_var=None,
        requires_api_key=False,
        default_model="llama3",
        default_api_base="http://localhost:11434",
        model_list_endpoint="/api/tags",
        recommended_models=("llama3", "qwen2.5-coder", "mistral"),
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        display_name="OpenAI",
        env_var="OPENAI_API_KEY",
        requires_api_key=True,
        default_model="gpt-4o-mini",
        model_list_endpoint="/models",
        recommended_models=("gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"),
    ),
    "anthropic": ProviderSpec(
        provider_id="anthropic",
        display_name="Anthropic",
        env_var="ANTHROPIC_API_KEY",
        requires_api_key=True,
        default_model="claude-3-5-sonnet-latest",
        model_list_endpoint="/models",
        recommended_models=(
            "claude-3-5-haiku-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
        ),
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        display_name="Google Gemini",
        env_var="GEMINI_API_KEY",
        requires_api_key=True,
        default_model="gemini-2.0-flash",
        model_list_endpoint="/models",
        recommended_models=("gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"),
    ),
}


def get_provider_spec(provider: str) -> ProviderSpec | None:
    """Get provider metadata from a provider identifier."""
    return PROVIDER_SPECS.get(provider.lower().strip())


def get_supported_providers() -> tuple[str, ...]:
    """Return provider identifiers in registry order."""
    return tuple(PROVIDER_SPECS.keys())  # noqa: VULTURE
