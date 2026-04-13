# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Zero-config operation: bundled best-practice configurations for Ruff, Pylint, and Bandit are applied automatically when no local config is found.
- Context-aware configuration: production and test code receive separate rule sets automatically based on the target path.
- `--human-readable` (`-r`) flag for `lintaider scan` to generate a Markdown report.
- Google-style docstrings across the entire codebase.
- `Attributes:` sections in all dataclass docstrings.

### Fixed

- Configuration discovery now correctly validates `[tool.<linter>]` sections in `pyproject.toml` before treating it as a local config file.
- `pyproject.toml` test glob changed from `tests/*` to `tests/**/*.py` for broader Ruff rule matching.

### Changed

- Improved CLI help text for all commands and options.
- Expanded all private-function docstrings to include `Args:` and `Returns:`.

## [0.1.0] - 2026-04-13

### Added

- Initial project structure with async linter orchestration.
- Support for Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep, Vulture, Radon, and Safety.
- AI-assisted fix generation via LiteLLM (`ollama`, `openai`, `anthropic`, `gemini`).
- Interactive onboarding wizard (`lintaider init`) with model discovery and connectivity testing.
- Standardized `LinterResult` model for unified issue representation.
- Semantic context extraction (function/class boundaries) for richer AI prompts.
- Fuzzy patch application with `difflib.SequenceMatcher` fallback.
- Human-readable Markdown report generation (`--human-readable`).
- GitHub Actions CI/CD with PyPI Trusted Publishing support.

### Fixed

- Various linting and formatting issues across the codebase.
- Improved error handling in linter output parsing.

### Changed

- Refactored CLI to use dedicated command handlers (`scan_handler`, `fix_handler`, `init_handler`).
- Enhanced configuration management with TOML and environment variables.
