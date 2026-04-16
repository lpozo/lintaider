"""Configuration management for LintAIder."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path("lintaider.toml")


@dataclass
class Config:
    """Configuration data for AI providers and models."""

    provider: str = "ollama"
    model: str = "llama3"
    api_base: str | None = None
    only_linters: list[str] = field(default_factory=list)
    skip_linters: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        """Load configuration from a TOML file and environment variables.

        Args:
            path: Path to the configuration file. Defaults to lintaider.toml.

        Returns:
            A Config instance.
        """
        load_dotenv()
        config_path = path or DEFAULT_CONFIG_PATH

        if not config_path.exists():
            return cls()

        try:
            with config_path.open("rb") as file:
                data = tomllib.load(file)

                ai_data = data.get("ai", {})
                linter_data = data.get("linters", {})
                merged = {**ai_data, **linter_data}

                valid_keys = {
                    "provider",
                    "model",
                    "api_base",
                    "only_linters",
                    "skip_linters",
                }
                filtered = {k: v for k, v in merged.items() if k in valid_keys}

                config = cls(**filtered)
                config._normalize()
                return config
        except (OSError, ValueError):
            return cls()

    def _normalize(self) -> None:
        """Normalise all fields to canonical lower-case, stripped values."""
        self.provider = self.provider.strip().lower()
        self.model = self.model.strip()

        self.only_linters = list(
            dict.fromkeys(
                v.strip().lower() for v in self.only_linters if v.strip()
            )
        )
        self.skip_linters = list(
            dict.fromkeys(
                v.strip().lower() for v in self.skip_linters if v.strip()
            )
        )

    def save(self, path: Path | None = None) -> None:
        """Normalise and persist the current configuration to a TOML file.

        Args:
            path: Destination path. Defaults to ``lintaider.toml`` in the
                current working directory.
        """
        self._normalize()
        config_path = path or DEFAULT_CONFIG_PATH

        lines = ["[ai]\n"]
        lines.append(f'provider = "{self.provider}"\n')
        lines.append(f'model = "{self.model}"\n')
        if self.api_base:
            lines.append(f'api_base = "{self.api_base}"\n')

        lines.append("\n[linters]\n")
        lines.append(f"only_linters = {self.only_linters}\n")
        lines.append(f"skip_linters = {self.skip_linters}\n")

        config_path.write_text("".join(lines), encoding="utf-8")
