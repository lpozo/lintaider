"""Configuration management for CodeReview."""

import os
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import tomllib  # type: ignore
except ImportError:
    import tomli as tomllib  # type: ignore

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration data for AI providers and models."""

    provider: str = "ollama"
    model: str = "llama3"
    api_base: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from a TOML file and environment variables.

        Args:
            path: Path to the configuration file. Defaults to codereview.toml.

        Returns:
            A Config instance.
        """
        load_dotenv()
        config_path = path or Path("codereview.toml")

        if not config_path.exists():
            return cls()

        try:
            with config_path.open("rb") as file:
                data = tomllib.load(file)
                ai_data = data.get("ai", {})
                return cls(**ai_data)
        except (OSError, ValueError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        """Save the current configuration to a TOML file.

        Args:
            path: Path to the configuration file. Defaults to codereview.toml.
        """
        config_path = path or Path("codereview.toml")
        lines = ["[ai]\n"]
        for key, value in asdict(self).items():
            if value is not None:
                lines.append(f'{key} = "{value}"\n')

        config_path.write_text("".join(lines), encoding="utf-8")


def get_api_key(provider: str) -> str | None:
    """Retrieve the API key for a given provider from environment variables.

    Args:
        provider: The name of the AI provider.

    Returns:
        The API key if found, otherwise None.
    """
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    env_var = env_map.get(provider.lower())
    if env_var:
        return os.getenv(env_var)
    return None
