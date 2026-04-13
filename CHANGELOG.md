# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-13

### Added
- Initial project structure with async linter orchestration.
- Support for Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep, Vulture, Radon, and Safety.
- AI-assisted fix generation via LiteLLM.
- Interactive onboarding wizard (`lintaider init`).
- Standardized linter result model.

### Fixed
- Various linting and formatting issues across the codebase.
- Improved error handling in linter output parsing.

### Changed
- Refactored CLI to use specific command handlers.
- Enhanced configuration management with TOML and environment variables.
