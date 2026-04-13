# LintAIder

LintAIder is an AI-assisted code auditing and auto-fix CLI for Python projects.
It runs multiple linters concurrently, aggregates findings into a unified format,
and lets you apply AI-generated fixes interactively.

## Highlights

- **Async linter orchestration** — all linters run in parallel via `asyncio`
- **Linters supported** — Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep, Vulture, Radon, Safety
- **Zero-config** — works immediately on any Python project with smart bundled defaults
- **Context-aware rules** — automatically applies stricter rules to production code and relaxed rules to test code
- **AI provider support** via LiteLLM (`ollama`, `openai`, `anthropic`, `gemini`)
- **Interactive onboarding** (`init`) with live model discovery and connectivity checks
- **Unified issue model** across all linters
- **Interactive patch application** with fuzzy matching fallback

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

The interactive wizard will:
- Ask you to choose an AI provider (`ollama`, `openai`, `anthropic`, or `gemini`)
- Discover available models automatically (where supported)
- Test the connection before saving
- Write `lintaider.toml` and optionally store your API key in the system keychain

### 2. Scan

```bash
uv run lintaider scan src/
```

Verbose output that prints every finding with code context:

```bash
uv run lintaider scan src/ -v
```

Generate a Markdown report:

```bash
uv run lintaider scan src/ --human-readable
```

Save results to a custom file:

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

## Zero-Config & Context-Aware

LintAIder works out of the box on **any** Python codebase — no linter config files required in the target project.

### How it works

When scanning a file or directory, each linter follows this priority order to find its configuration:

1. **Nearest local config** — walks up from the target to the current working directory, looking for the linter's native config file (e.g. `ruff.toml`, `.pylintrc`, `bandit.yaml`, or a `[tool.<linter>]` section in `pyproject.toml`).
2. **Bundled defaults** — if no local config is found, LintAIder falls back to built-in best-practice configurations shipped with the tool itself.

### Production vs. test code

LintAIder detects whether a file belongs to test code by inspecting its path:

- Paths under `tests/` or files named `test_*.py` / `*_test.py` use the **test** configuration (e.g. `assert` statements are allowed, security rules are relaxed).
- Everything else uses the **production** configuration (stricter typing, full security checks).

This means you never have to maintain separate CI configs for `src/` vs. `tests/`.

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

| Linter | Category | Detects |
| --- | --- | --- |
| [Ruff](https://github.com/astral-sh/ruff) | Style | PEP 8, imports, code smells |
| [Pylint](https://github.com/pylint-dev/pylint) | Style | Code quality, conventions |
| [Bandit](https://github.com/PyCQA/bandit) | Security | Common security vulnerabilities |
| [MyPy](https://github.com/python/mypy) | Typing | Static type checking |
| [Pyright](https://github.com/microsoft/pyright) | Typing | Advanced type inference |
| [Semgrep](https://github.com/semgrep/semgrep) | Semantic | Pattern-based analysis |
| [Vulture](https://github.com/jendrikseipp/vulture) | Dead code | Unused variables, functions |
| [Radon](https://github.com/rubik/radon) | Complexity | Cyclomatic complexity |
| [Safety](https://github.com/pyupio/safety) | Dependencies | Known vulnerabilities |

## Configuration File

`lintaider.toml` (created by `lintaider init`) controls provider and linter defaults:

```toml
[ai]
provider = "ollama"
model = "llama3"
# api_base = "http://localhost:11434"  # optional, for self-hosted providers

[linters]
only_linters = []   # run all linters when empty
skip_linters = []   # skip none by default
```

## Development

Run tests:

```bash
uv run pytest
```

Run a project scan:

```bash
uv run lintaider scan src
```

Run tests scan:

```bash
uv run lintaider scan tests
```
