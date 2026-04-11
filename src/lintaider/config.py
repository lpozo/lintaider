"""Configuration management for LintAIder."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


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
            path: Path to the configuration file. Defaults to lintaider.toml.

        Returns:
            A Config instance.
        """
        load_dotenv()
        config_path = path or Path("lintaider.toml")

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
                config.normalize()
                return config
        except (OSError, ValueError):
            return cls()

    def normalize(self) -> None:
        """Normalise all fields to canonical lower-case, stripped values.

        Lowercases ``provider``, strips whitespace from ``model``, and
        applies ``_normalize_linter_list`` to both linter lists (lowercase,
        deduplicate, preserve insertion order). Called automatically by
        :meth:`load` and :meth:`save`.
        """
        self.provider = self.provider.strip().lower()
        self.model = self.model.strip()
        self.only_linters = _normalize_linter_list(self.only_linters)
        self.skip_linters = _normalize_linter_list(self.skip_linters)

    def save(self, path: Path | None = None) -> None:
        """Normalise and persist the current configuration to a TOML file.

        Args:
            path: Destination path. Defaults to ``lintaider.toml`` in the
                current working directory.
        """
        self.normalize()
        config_path = path or Path("lintaider.toml")

        lines = ["[ai]\n"]
        lines.append(f'provider = "{self.provider}"\n')
        lines.append(f'model = "{self.model}"\n')
        if self.api_base:
            lines.append(f'api_base = "{self.api_base}"\n')

        lines.append("\n[linters]\n")
        lines.append(f"only_linters = {self.only_linters}\n")
        lines.append(f"skip_linters = {self.skip_linters}\n")

        config_path.write_text("".join(lines), encoding="utf-8")


def _normalize_linter_list(values: list[str]) -> list[str]:
    """Lowercase, strip, and deduplicate a list of linter names.

    Args:
        values: Raw list of linter name strings.

    Returns:
        An order-preserving list with each entry lowercased and stripped,
        and any duplicates removed.
    """
    normalized = [value.strip().lower() for value in values if value.strip()]
    return list(dict.fromkeys(normalized))
