"""AI provider abstractions and LiteLLM integration for fix generation."""

from lintaider.ai.base import AIFixProposal, BaseAIProvider
from lintaider.ai.provider import (
    LiteLLMProvider,
    create_ai_provider,
    list_provider_models,
    verify_provider_connection,
)

__all__ = [
    "BaseAIProvider",
    "AIFixProposal",
    "LiteLLMProvider",
    "create_ai_provider",
    "list_provider_models",
    "verify_provider_connection",
]
