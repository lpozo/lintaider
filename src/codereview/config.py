"""Configuration management for CodeReview."""

import tomllib
from dataclasses import dataclass, field
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
    only_linters: list[str] = field(default_factory=list)
    skip_linters: list[str] = field(default_factory=list)

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

                # Extract AI Settings
                ai_data = data.get("ai", {})

                # Extract Linter Settings
                linter_data = data.get("linters", {})
                merged = {**ai_data, **linter_data}

                # Filter unknown keys to prevent init errors
                valid_keys = {
                    "provider",
                    "model",
                    "api_base",
                    "only_linters",
                    "skip_linters",
                }
                filtered = {k: v for k, v in merged.items() if k in valid_keys}

                return cls(**filtered)
        except (OSError, ValueError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        """Save the current configuration to a TOML file.

        Args:
            path: Path to the configuration file. Defaults to codereview.toml.

        Returns:
            None
        """
        config_path = path or Path("codereview.toml")

        # Build TOML manually to separate sections cleanly
        lines = ["[ai]\n"]
        lines.append(f'provider = "{self.provider}"\n')
        lines.append(f'model = "{self.model}"\n')
        if self.api_base:
            lines.append(f'api_base = "{self.api_base}"\n')

        lines.append("\n[linters]\n")
        lines.append(f"only_linters = {self.only_linters}\n")
        lines.append(f"skip_linters = {self.skip_linters}\n")

        config_path.write_text("".join(lines), encoding="utf-8")
