"""Configuration management for CodeReview."""

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

PROVIDER_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


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


