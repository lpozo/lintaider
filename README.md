# CodeReview: AI-Powered Auto-Fixer

**CodeReview** is an advanced code auditing tool that combines multiple linters with the power of Artificial Intelligence (LLMs) to automatically and concurrently find and fix issues.

## Features

-   **Asynchronous Engine**: Scans your code with multiple linters in parallel using `asyncio`.
-   **Background AI**: Generates fix suggestions while you review previous findings.
-   **Professional Configuration**: `init` command to configure providers (OpenAI, Anthropic, Ollama, Gemini) persistently.
-   **Multi-Linter**: Native support for Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep, Vulture, Radon, and Safety.
-   **Smart Auto-Fixer**: Applies AI-suggested patches using *Fuzzy Matching* algorithms.

## Installation

Requires [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
git clone <repository-url>
cd codereview
uv sync
```

## Initial Setup

Before diving in, configure your preferred AI provider:

```bash
uv run codereview init
```

This will create a `codereview.toml` file with your preferences and a `.env` file for your API keys.

## Quick Start

### 1. Scan the code
Detect issues in files or directories:

```bash
uv run codereview scan src/ -v
```

### 2. Apply fixes
Start the interactive flow. If you haven't run `scan` before, you can pass the target directly:

```bash
# Scans and then starts the fixer in a single step
uv run codereview fix src/
```

If you already have a `scan-result.json` file, simply run:

```bash
uv run codereview fix
```

### Filtering options
You can exclusively run specific linters or skip others:

```bash
# Only run Ruff and MyPy
uv run codereview scan . --only ruff,mypy

# Skip Safety (dependency scanning)
uv run codereview scan . --skip safety
```

## Supported Linters

| Linter | Specialty |
| :--- | :--- |
| **Ruff** | Style and common errors (Blazing fast) |
| **Pylint** | Deep static analysis and maintainability |
| **Bandit** | Code security vulnerabilities |
| **MyPy** | Official static type checking |
| **Pyright** | Ultra-fast Microsoft type checking |
| **Semgrep** | Semantic analysis and advanced security |
| **Vulture** | Dead code and unused function detection |
| **Radon** | Cyclomatic Complexity metric (Maintainability) |
| **Safety** | Vulnerability scanning in installed dependencies |

## Testing

```bash
uv run pytest
```

---
*Developed with advanced asynchronous architecture for an instant experience.*
