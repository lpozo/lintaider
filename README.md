# LintAIder

LintAIder is an AI-assisted code auditing and auto-fix CLI for Python projects.
It runs multiple linters concurrently, aggregates findings into a unified format,
and lets you apply AI-generated fixes interactively.

## Highlights

- Async linter orchestration with `asyncio`
- AI provider support via LiteLLM (`ollama`, `openai`, `anthropic`, `gemini`)
- Interactive onboarding (`init`) with model discovery and connectivity checks
- Unified issue model across linters
- Interactive patch application with fuzzy matching fallback

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

## Installation

```bash
git clone https://github.com/lpozo/lintaider.git
cd lintaider
uv sync
```

## Quick Start

### 1. Initialize

```bash
uv run lintaider init
```

This command creates or updates:

- `lintaider.toml` for provider/model/linter defaults
- `.env` for API keys when keychain storage is unavailable

### 2. Scan

```bash
uv run lintaider scan src/
```

Verbose output:

```bash
uv run lintaider scan src/ -v
```

Custom output file:

```bash
uv run lintaider scan src/ -o my-scan.json
```

### 3. Fix

Use existing scan results (`scan-result.json` by default):

```bash
uv run lintaider fix
```

Provide a specific results file:

```bash
uv run lintaider fix --input my-scan.json
```

Scan then fix in one command:

```bash
uv run lintaider fix src/
```

## Linter Filtering

Run only selected linters:

```bash
uv run lintaider scan . --only ruff,mypy
```

Skip selected linters:

```bash
uv run lintaider scan . --skip safety
```

You can also set default `only_linters` and `skip_linters` values in
`lintaider.toml` via `uv run lintaider init`.

## Supported Linters

- [Ruff](https://github.com/astral-sh/ruff)
- [Pylint](https://github.com/pylint-dev/pylint)
- [Bandit](https://github.com/PyCQA/bandit)
- [MyPy](https://github.com/python/mypy)
- [Pyright](https://github.com/microsoft/pyright)
- [Semgrep](https://github.com/semgrep/semgrep)
- [Vulture](https://github.com/jendrikseipp/vulture)
- [Radon](https://github.com/rubik/radon)
- [Safety](https://github.com/pyupio/safety)

## Development

Run tests:

```bash
uv run pytest
```

Run a project scan:

```bash
uv run lintaider scan src
```
