"""LiteLLM AI provider implementation for universal model access."""

import json

import requests
from dotenv import load_dotenv
from litellm import acompletion

from codereview.ai.auth import get_api_key_for_provider
from codereview.ai.base import AIFixProposal, BaseAIProvider
from codereview.ai.registry import get_provider_spec
from codereview.linters.result import LinterResult

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


def list_provider_models(
    provider_name: str,
    api_base: str | None = None,
    api_key: str | None = None,
) -> list[str]:
    """Best-effort model discovery for supported providers.

    Returns an empty list on failures so onboarding can gracefully fall back
    to manual model entry.
    """
    provider_name = provider_name.lower().strip()
    provider_spec = get_provider_spec(provider_name)
    if not provider_spec or not provider_spec.model_list_endpoint:
        return []

    base_url = api_base or provider_spec.default_api_base
    if not base_url:
        if provider_name == "openai":
            base_url = "https://api.openai.com/v1"
        elif provider_name == "anthropic":
            base_url = "https://api.anthropic.com/v1"
        elif provider_name == "gemini":
            base_url = "https://generativelanguage.googleapis.com/v1beta"
        else:
            return []

    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    token = api_key or get_api_key_for_provider(provider_name)

    if provider_name in ("openai", "anthropic") and token:
        headers["Authorization"] = f"Bearer {token}"
    if provider_name == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    if provider_name == "gemini" and token:
        params["key"] = token

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

    if provider_name == "ollama":
        models = payload.get("models", [])
        return sorted(
            str(item.get("name", "")).strip() for item in models if item.get("name")
        )

    raw_models = payload.get("data") or payload.get("models") or []
    names: list[str] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        name = item.get("id") or item.get("name")
        if isinstance(name, str) and name:
            if provider_name == "gemini" and name.startswith("models/"):
                name = name.replace("models/", "", 1)
            names.append(name)
    return sorted(set(names))


async def verify_provider_connection(
    provider_name: str,
    model_name: str,
    api_base: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, str]:
    """Run a lightweight connectivity check for the selected provider/model."""
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
