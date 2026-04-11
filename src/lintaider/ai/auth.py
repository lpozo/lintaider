"""Authentication and environment management for AI providers."""

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from lintaider.ai.registry import get_provider_spec

try:
    import keyring as keyring_module
except ImportError:  # pragma: no cover - depends on optional install
    keyring_module = None  # type: ignore[assignment]

# Mapping of providers to their expected environment variable names
PROVIDER_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

KEYRING_SERVICE_NAME = "lintaider"


def get_env_var_for_provider(provider: str) -> str | None:
    """Get the environment variable name for a given provider.

    Args:
        provider: The name of the AI provider.

    Returns:
        The environment variable name or None if not found.
    """
    provider_spec = get_provider_spec(provider)
    if provider_spec:
        return provider_spec.env_var
    return PROVIDER_ENV_MAP.get(provider.lower())


def get_api_key_for_provider(provider: str) -> str | None:
    """Get the API key for a provider from environment or keyring.

    Environment variables take precedence over keyring, which is useful
    for CI environments and explicit shell-based overrides.

    Args:
        provider: The name of the AI provider (e.g., ``openai``).

    Returns:
        The API key string, or ``None`` if not found in any source.
    """
    load_dotenv()
    env_var = get_env_var_for_provider(provider)
    if not env_var:
        return None

    env_value = os.getenv(env_var)
    if env_value:
        return env_value

    if keyring_module is None:
        return None

    try:
        return keyring_module.get_password(KEYRING_SERVICE_NAME, env_var)
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def save_api_key(env_var: str, api_key: str) -> None:
    """Save an API key to the .env file.

    Args:
        env_var: The environment variable name.
        api_key: The API key value.
    """
    env_path = Path(".env")
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    new_line = f'{env_var}="{api_key}"'

    if env_var in content:
        # Use regex to replace the existing value carefully
        content = re.sub(f'{env_var}=".*"', new_line, content)
    else:
        # Ensure there is a newline before appending
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{new_line}\n"

    env_path.write_text(content.strip() + "\n", encoding="utf-8")


def save_provider_api_key(provider: str, api_key: str) -> str:
    """Save a provider API key to OS keychain, falling back to ``.env``.

    Args:
        provider: The name of the AI provider.
        api_key: The API key value to store.

    Returns:
        The storage backend used: ``"keychain"``, ``".env"``, or ``"none"``
        when the provider has no associated environment variable.
    """
    env_var = get_env_var_for_provider(provider)
    if not env_var:
        return "none"

    if keyring_module is not None:
        try:
            keyring_module.set_password(KEYRING_SERVICE_NAME, env_var, api_key)
            return "keychain"
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Log but don't fail - will fallback to .env
            logging.debug("Failed to save to keyring: %s", exc)

    save_api_key(env_var, api_key)
    return ".env"
