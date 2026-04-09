"""Authentication and environment management for AI providers."""

import re
from pathlib import Path

# Mapping of providers to their expected environment variable names
PROVIDER_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def get_env_var_for_provider(provider: str) -> str | None:
    """Get the environment variable name for a given provider.

    Args:
        provider: The name of the AI provider.

    Returns:
        The environment variable name or None if not found.
    """
    return PROVIDER_ENV_MAP.get(provider.lower())


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
