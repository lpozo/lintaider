"""LiteLLM AI provider implementation for universal model access."""

import json
from typing import TYPE_CHECKING

import requests
from dotenv import load_dotenv
from litellm import acompletion

from codereview.ai.auth import get_api_key_for_provider
from codereview.ai.base import AIFixProposal, BaseAIProvider
from codereview.ai.registry import get_provider_spec
from codereview.linters.result import LinterResult

if TYPE_CHECKING:
    from codereview.ai.registry import ProviderSpec

# Load .env file if it exists
load_dotenv()


MODEL_DISCOVERY_TIMEOUT = 3.0


# pylint: disable=too-few-public-methods
class LiteLLMProvider(BaseAIProvider):
    """Universal AI provider using LiteLLM."""

    name = "LiteLLM"

    def __init__(
        self,
        model: str = "gpt-4o",
        api_base: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize LiteLLM provider.

        Args:
            model: The name of the model to use.
            api_base: Optional base URL for the model API (required for local/private).
            api_key: Optional API key override for cloud providers.
        """
        self.model = model
        self.api_base = api_base
        self.api_key = api_key

    async def generate_fixes(self, linter_result: LinterResult) -> list[AIFixProposal]:
        """Request fixes using LiteLLM asynchronously.

        Args:
            linter_result: The linter result to fix.

        Returns:
            A list of AI-generated fix proposals.
        """
        system_prompt, user_prompt = self._get_prompts(linter_result)

        try:
            # LiteLLM manages API keys from environment variables automatically
            response = await acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                api_base=self.api_base,
                api_key=self.api_key,
            )

            # Access content from the response
            content = response.choices[0].message.content or "[]"  # type: ignore

            # LiteLLM sometimes returns the string representation of JSON
            parsed = json.loads(content)

            # Expected format is a list or a dict with a list of fixes
            if isinstance(parsed, dict) and "fixes" in parsed:
                parsed = parsed["fixes"]
            elif isinstance(parsed, dict):
                # If it returned a single object, wrap it
                parsed = [parsed]

            if not isinstance(parsed, list):
                return []

            proposals = []
            for item in parsed:
                proposals.append(
                    AIFixProposal(
                        explanation=item.get("explanation", ""),
                        code_diff=item.get("code_diff", ""),
                    )
                )
            return proposals
        except Exception:  # pylint: disable=broad-exception-caught
            return []


def create_ai_provider(
    provider_name: str,
    model_name: str | None = None,
    api_base: str | None = None,
) -> BaseAIProvider:
    """Factory function to create an AI provider.

    Args:
        provider_name: AI Provider (e.g. "openai", "anthropic", "ollama").
        model_name: Optional model override.
        api_base: Optional API base URL.

    Returns:
        A BaseAIProvider instance.
    """
    provider_name = provider_name.lower().strip()
    provider_spec = get_provider_spec(provider_name)
    model = model_name or (provider_spec.default_model if provider_spec else "llama3")

    # If it's a provider name (e.g. "openai"), ensure the prefix exists.
    if "/" not in model:
        model = f"{provider_name}/{model}"

    resolved_api_base = api_base or (
        provider_spec.default_api_base if provider_spec else None
    )
    api_key = get_api_key_for_provider(provider_name)
    return LiteLLMProvider(model=model, api_base=resolved_api_base, api_key=api_key)


def _resolve_base_url(
    provider_name: str, api_base: str | None, provider_spec: "ProviderSpec | None"
) -> str | None:
    """Resolve the effective API base URL for a provider.

    Checks, in order: the explicit ``api_base`` argument, the provider
    spec's default, and finally a hard-coded fallback for well-known providers.

    Args:
        provider_name: Lowercase provider identifier (e.g., ``"openai"``).
        api_base: Optional caller-supplied base URL override.
        provider_spec: Provider metadata from the registry, or ``None``.

    Returns:
        The resolved base URL, or ``None`` if it cannot be determined.
    """
    base_url = api_base or (provider_spec.default_api_base if provider_spec else None)
    if base_url:
        return base_url

    # Fallback URLs for known providers
    fallbacks = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
    }
    return fallbacks.get(provider_name)


def _prepare_request_headers_and_params(
    provider_name: str, api_key: str | None
) -> tuple[dict[str, str], dict[str, str]]:
    """Build HTTP headers and query params for a model list discovery request.

    Handles provider-specific authentication schemes: bearer token for
    OpenAI/Anthropic, API key query param for Gemini, and nothing for Ollama.

    Args:
        provider_name: Lowercase provider identifier.
        api_key: Optional API key override; falls back to environment/keyring.

    Returns:
        A two-tuple of ``(headers, params)`` dicts ready for use in a request.
    """
    headers: dict[str, str] = {}
    params: dict[str, str] = {}

    token = api_key or get_api_key_for_provider(provider_name)
    if provider_name in ("openai", "anthropic") and token:
        headers["Authorization"] = f"Bearer {token}"
    if provider_name == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    if provider_name == "gemini" and token:
        params["key"] = token

    return headers, params


def _parse_openai_style_models(provider_name: str, raw_models: list) -> list[str]:
    """Extract model names from an OpenAI-style model list response.

    Used by OpenAI, Anthropic, and Gemini, which all return either a ``data``
    list of objects with an ``id`` field, or a ``models`` list. Gemini model
    names are stripped of their ``models/`` prefix.

    Args:
        provider_name: Lowercase provider identifier, used to apply
            provider-specific name transformations.
        raw_models: The raw list of model objects from the JSON response.

    Returns:
        A sorted, deduplicated list of model name strings.
    """
    names: list[str] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        name = item.get("id") or item.get("name")
        if not (isinstance(name, str) and name):
            continue
        if provider_name == "gemini" and name.startswith("models/"):
            name = name.replace("models/", "", 1)
        names.append(name)
    return sorted(set(names))


def _parse_model_response(provider_name: str, payload: dict) -> list[str]:
    """Dispatch model name parsing based on provider response format.

    Ollama uses a ``models`` list with ``name`` fields. All other providers
    use an OpenAI-compatible format handled by ``_parse_openai_style_models``.

    Args:
        provider_name: Lowercase provider identifier.
        payload: Parsed JSON response body from the model list endpoint.

    Returns:
        A sorted, deduplicated list of model name strings.
    """
    if provider_name == "ollama":
        models = payload.get("models", [])
        return sorted(
            str(item.get("name", "")).strip() for item in models if item.get("name")
        )

    raw_models = payload.get("data") or payload.get("models") or []
    return _parse_openai_style_models(provider_name, raw_models)


def list_provider_models(
    provider_name: str,
    api_base: str | None = None,
    api_key: str | None = None,
) -> list[str]:
    """Discover available models for a provider via its model list endpoint.

    Makes a best-effort HTTP request to the provider's model list endpoint.
    Returns an empty list on any failure so callers can gracefully fall back
    to manual model entry or recommended models.

    Args:
        provider_name: The provider to query (e.g., ``"ollama"``, ``"openai"``).
        api_base: Optional base URL override (useful for self-hosted providers).
        api_key: Optional API key override; falls back to environment/keyring.

    Returns:
        A sorted list of model name strings, or an empty list on failure.
    """
    provider_name = provider_name.lower().strip()
    provider_spec = get_provider_spec(provider_name)
    if not provider_spec or not provider_spec.model_list_endpoint:
        return []

    base_url = _resolve_base_url(provider_name, api_base, provider_spec)
    if not base_url:
        return []

    headers, params = _prepare_request_headers_and_params(provider_name, api_key)

    url = f"{base_url.rstrip('/')}{provider_spec.model_list_endpoint}"
    if provider_name == "ollama" and url.endswith("/v1/api/tags"):
        url = url.replace("/v1/api/tags", "/api/tags")

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=MODEL_DISCOVERY_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    return _parse_model_response(provider_name, payload)


async def verify_provider_connection(
    provider_name: str,
    model_name: str,
    api_base: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, str]:
    """Run a lightweight connectivity check for the given provider and model.

    Sends a minimal completion request (``ping`` → ``OK``) to verify that
    credentials and network access are working before saving configuration.

    Args:
        provider_name: The provider to check (e.g., ``"openai"``).
        model_name: The model to use for the test request.
        api_base: Optional base URL override.
        api_key: Optional API key override; falls back to environment/keyring.

    Returns:
        A two-tuple of ``(success, message)`` where ``success`` is ``True``
        when the provider responded without error.
    """
    provider_name = provider_name.lower().strip()
    model = model_name if "/" in model_name else f"{provider_name}/{model_name}"

    try:
        await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": "Return only OK."},
                {"role": "user", "content": "ping"},
            ],
            api_base=api_base,
            api_key=api_key or get_api_key_for_provider(provider_name),
            max_tokens=4,
            temperature=0,
            timeout=10,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return False, str(exc)

    return True, "Connection successful"
