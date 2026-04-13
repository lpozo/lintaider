# Copilot Workspace Instructions for LintAIder

## Overview
**LintAIder** is an AI-powered code audit and auto-fix tool that orchestrates multiple Python linters concurrently and uses LLMs to generate and apply fixes.

## Build & Test Commands
```bash
uv sync                        # Install dependencies
uv run lintaider init          # Interactive AI provider setup
uv run lintaider scan src/     # Run linters and collect issues
uv run lintaider scan src/ -r  # Also generate linting-report.md markdown output
uv run lintaider fix           # Use existing scan-result.json to suggest/apply patches
uv run lintaider fix src/      # Auto-scan target first if results file is missing
uv run pytest                  # Run test suite
```

## Project Structure
```
src/lintaider/
  cli/            # CLI entry point and command handlers (main.py, scan_handler.py, fix_handler.py, init_handler.py)
  linters/        # Linter integrations: bandit, mypy, pylint, pyright, radon, ruff, safety, semgrep, vulture
                  #   engine.py = async orchestration, base.py = abstract base, result.py = result types
                  #   context.py = snippet extraction/formatting for AI context and UI display
  ai/             # AI provider abstraction
                  #   registry.py = ProviderSpec metadata for 4 providers (ollama, openai, anthropic, gemini)
                  #   auth.py     = API key retrieval: env var → keyring → None; save: keyring → .env
                  #   provider.py = LiteLLMProvider, model discovery, connectivity verification
                  #   prompts/    = system.txt and user.txt templates
  config.py       # Config: provider, model, api_base, skip_linters, only_linters; normalize() on load/save
```

## Key Conventions
- **Async orchestration**: All linters run in parallel via `asyncio`. Keep linter `run()` and AI calls non-blocking.
- **Provider registry**: Add new providers in `registry.py` as a `ProviderSpec` — don't hardcode provider strings elsewhere.
- **API keys**: Use `get_api_key_for_provider()` to retrieve keys (env var wins over keyring). Use `save_provider_api_key()` to persist.
- **Config normalization**: `Config.normalize()` is called on every load/save — provider and linter names are always lowercased and deduplicated.
- **Patch application**: Fuzzy matching is used for patch apply; may fail if code changed since scan.
- **Linter filtering**: Users can pass `--only ruff,bandit` or `--skip semgrep` at scan time, or set defaults via `init`.
- **Dual scan outputs**: `scan` always writes JSON and can also write `linting-report.md` with `-r/--human-readable`.

## Potential Pitfalls
- **Python 3.12+ required** — check `pyproject.toml` before changing syntax.
- **Radon is a linter too** — it's in `linters/` alongside static analysis tools; include it when iterating all linters.
- **Credential fallback must be preserved** — API key retrieval prioritizes env vars, then keyring; key save should fall back to `.env` if keyring operations fail.
- **asyncio test mode** is set to `strict` in `pyproject.toml` — async tests need `@pytest.mark.asyncio`.

## Documentation
- See `README.md` for usage, supported linters, and configuration reference.
