"""Command-line interface for the code reviewer."""

import asyncio
import difflib
import json
import os
from pathlib import Path
from typing import cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from codereview.ai import AIFixProposal, create_ai_provider
from codereview.config import Config
from codereview.linters import (
    BanditLinter,
    BaseLinter,
    Engine,
    MyPyLinter,
    PylintLinter,
    PyrightLinter,
    RuffLinter,
    SemgrepLinter,
    VultureLinter,
)
from codereview.linters.result import LinterResult

console = Console()

LINTER_MAP: dict[str, type[BaseLinter]] = {
    "ruff": RuffLinter,
    "pylint": PylintLinter,
    "bandit": BanditLinter,
    "mypy": MyPyLinter,
    "pyright": PyrightLinter,
    "semgrep": SemgrepLinter,
    "vulture": VultureLinter,
}

SCAN_RESULT_FILE = Path("scan-result.json")


@click.group()
def main() -> None:
    """AI-powered code reviewer and auto-fixer."""


@main.command()
def init() -> None:
    """Initialize configuration for CodeReview."""
    config = Config.load()

    provider = click.prompt(
        "AI Provider",
        default=config.provider,
        type=str,
    )
    model = click.prompt(
        "AI Model",
        default=config.model,
        type=str,
    )
    api_base = (
        click.prompt(
            "AI Provider API base URL (leave empty for default)",
            default=config.api_base or "",
            type=str,
            show_default=False,
        ).strip()
        or None
    )

    # API Key handling for Cloud providers
    if provider.lower() != "ollama":
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_var = env_map.get(provider.lower())
        if env_var:
            current_key = os.getenv(env_var)
            api_key = click.prompt(
                f"Enter your {env_var} (leave empty to keep current or skip)",
                default=current_key or "",
                hide_input=True,
            )
            if api_key:
                # Store in .env
                env_path = Path(".env")
                content = ""
                if env_path.exists():
                    content = env_path.read_text(encoding="utf-8")

                new_line = f'{env_var}="{api_key}"'
                if env_var in content:
                    # Replace existing
                    import re

                    content = re.sub(f'{env_var}=".*"', new_line, content)
                else:
                    content += f"\n{new_line}\n"

                env_path.write_text(content.strip() + "\n", encoding="utf-8")
                console.print("[green]Saved API key to .env[/green]")

    config.provider = provider
    config.model = model
    config.api_base = api_base
    config.save()

    console.print(
        Panel(
            f"Provider: [bold]{config.provider}[/bold]\n"
            f"Model: [bold]{config.model}[/bold]\n"
            f"API Base: [bold]{config.api_base or 'Default'}[/bold]",
            title="Configuration Saved to codereview.toml",
            border_style="green",
        )
    )


@main.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--only", help="Comma-separated list of linters to run")
@click.option("--skip", help="Comma-separated list of linters to skip")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Path for the JSON results file (default: {SCAN_RESULT_FILE})",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Print a detailed report of every issue found.",
)
def scan(
    target: Path,
    only: str | None,
    skip: str | None,
    output: Path | None,
    verbose: bool,
) -> None:
    """Scan a target file or directory and save results to a JSON file."""
    asyncio.run(
        _async_scan(target, only, skip, output or SCAN_RESULT_FILE, verbose),
    )


async def _async_scan(
    target: Path,
    only: str | None,
    skip: str | None,
    output: Path,
    verbose: bool = False,
) -> None:
    """Run all configured linters and write results to a JSON file."""
    console.print(f"[bold blue]Scanning {target}...[/bold blue]")

    # Filtering logic
    active_linters = list(LINTER_MAP.keys())
    if only:
        only_list = [name.strip().lower() for name in only.split(",")]
        active_linters = [name for name in active_linters if name in only_list]
    if skip:
        skip_list = [name.strip().lower() for name in skip.split(",")]
        active_linters = [name for name in active_linters if name not in skip_list]

    # Use cast to satisfy MyPy that we are not instantiating the abstract BaseLinter
    engine = Engine(
        linters=[cast(type[BaseLinter], LINTER_MAP[name])() for name in active_linters]
    )
    results = await engine.run_all(target)

    if not results:
        console.print("[bold green]No issues found! 🎉[/bold green]")
        return

    # Per-linter summary
    from collections import Counter

    counts: Counter[str] = Counter(r.linter_name for r in results)
    summary_lines = "\n".join(
        f"  {linter}: {count}" for linter, count in sorted(counts.items())
    )
    console.print(f"[bold red]Found {len(results)} issues:[/bold red]\n{summary_lines}")

    if verbose:
        for idx, result in enumerate(results):
            location = f"{result.file_path}:{result.line_start}"
            if result.col_start is not None:
                location += f":{result.col_start}"
            console.print(
                Panel(
                    f"[bold]{result.linter_name}[/bold] [{result.error_code}] "
                    f"[yellow]{location}[/yellow]\n\n"
                    f"{result.message}"
                    + (
                        f"\n\n[dim]{result.snippet_context}[/dim]"
                        if result.snippet_context
                        else ""
                    ),
                    title=f"Issue {idx + 1}/{len(results)}",
                    border_style="red",
                )
            )

    # Serialize to JSON
    output.write_text(
        json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8"
    )
    console.print(f"\n[bold green]Results saved to {output}[/bold green]")
    console.print(
        "[dim]Run 'codereview fix' to get AI suggestions and apply patches.[/dim]"
    )


@main.command()
@click.option(
    "--input",
    "input_file",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Path to the scan results JSON file (default: {SCAN_RESULT_FILE})",
)
@click.option("--provider", help="AI Provider override")
@click.option("--model", help="AI Model name override")
@click.option("--api-base", help="AI Provider API base URL override")
def fix(
    input_file: Path | None,
    provider: str | None,
    model: str | None,
    api_base: str | None,
) -> None:
    """Read scan results and interactively apply AI-suggested fixes."""
    asyncio.run(
        _async_fix(input_file or SCAN_RESULT_FILE, provider, model, api_base),
    )


async def _async_fix(
    input_file: Path,
    provider_name: str | None,
    model_name: str | None,
    api_base: str | None,
) -> None:
    """AI suggestion and interactive patch workflow."""
    if not input_file.exists():
        console.print(
            f"[bold red]Error:[/bold red] {input_file} not found. "
            "Run 'codereview scan <target>' first."
        )
        return

    try:
        data = json.loads(input_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[bold red]Error reading {input_file}:[/bold red] {exc}")
        return

    results = [LinterResult.from_dict(item) for item in data]

    if not results:
        console.print("[bold green]No issues to fix.[/bold green]")
        return

    config = Config.load()
    final_provider = provider_name or config.provider
    final_model = model_name or config.model
    final_api_base = api_base or config.api_base

    console.print(
        f"[bold blue]Loaded {len(results)} issues from {input_file}[/bold blue]"
    )
    console.print(f"[dim]Using {final_provider}:{final_model}[/dim]")

    try:
        ai = create_ai_provider(final_provider, final_model, final_api_base)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return

    # Background AI Task Orchestration with Rate Limiting
    ai_semaphore = asyncio.Semaphore(1)

    async def _wrapped_generate_fixes(res: LinterResult) -> list[AIFixProposal]:
        async with ai_semaphore:
            fixes = await ai.generate_fixes(res)
            await asyncio.sleep(0.5)
            return fixes

    # Launch all AI tasks immediately in the background
    ai_tasks = [
        asyncio.create_task(_wrapped_generate_fixes(result)) for result in results
    ]

    for idx, result in enumerate(results):
        console.print(
            Panel(
                f"[bold]{result.linter_name}[/bold] error {result.error_code} at "
                f"[yellow]{result.file_path}:{result.line_start}[/yellow]\n"
                f"{result.message}",
                title=f"Linter Error {idx + 1}/{len(results)}",
                border_style="red",
            )
        )

        console.print("[dim]Waiting for AI response...[/dim]")

        proposals = await ai_tasks[idx]

        if not proposals:
            console.print("[red]AI failed to generate solutions for this issue.[/red]")
            continue

        for i, prop in enumerate(proposals, start=1):
            syntax = Syntax(
                prop.code_diff, "python", theme="monokai", line_numbers=False
            )
            console.print(
                Panel(
                    syntax,
                    title=f"Option {i}: {prop.explanation}",
                    border_style="green",
                )
            )

        # Non-blocking prompt so other AI tasks can continue in the background
        choice = await asyncio.to_thread(
            click.prompt,
            "Select an option to apply (1, 2, 3...) or 's' to skip",
            type=str,
            default="s",
        )
        choice = choice.lower()

        if choice == "s" or not choice.isdigit():
            console.print("[dim]Skipping...[/dim]\n")
            continue

        idx_choice = int(choice) - 1
        if 0 <= idx_choice < len(proposals):
            selected = proposals[idx_choice]
            applied = _apply_patch(
                result.file_path,
                result.line_start,
                result.snippet_context,
                selected.code_diff,
            )
            if applied:
                console.print("[bold green]Patch applied successfully![/bold green]\n")
            else:
                console.print(
                    "[bold yellow]Could not apply patch accurately. "
                    "Skipping...[/bold yellow]\n"
                )
        else:
            console.print("[red]Invalid choice. Skipping...[/red]\n")


def _apply_patch(
    file_path: Path, line_start: int, original_context: str, new_code: str
) -> bool:
    """Apply the chosen patch to the file using fuzzy content matching.

    Args:
        file_path: Path to the file.
        line_start: Reported line number (1-indexed).
        original_context: The snippet the linter provided.
        new_code: The replacement snippet from the AI.

    Returns:
        True if the patch was applied, False otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Strategy: find the exact content if possible near the reported line
        # but fallback to searching the whole file if line numbers shifted
        target_snippet = original_context.strip()
        new_snippet = new_code.strip()

        if not target_snippet:
            return False

        # Check if the snippet exists at exactly the reported position (ideal)
        context_lines = target_snippet.splitlines()
        start_idx = max(0, line_start - 1)
        end_idx = min(len(lines), start_idx + len(context_lines))

        current_block = "\n".join(lines[start_idx:end_idx]).strip()

        if current_block == target_snippet:
            # Perfect match at location
            lines[start_idx:end_idx] = new_snippet.splitlines()
        else:
            # Content-based fuzzy matching
            # Search in a window around line_start to avoid far-away matches
            # of common snippets (like 'pass' or 'return')
            window_lines = 100
            search_start_line = max(0, start_idx - window_lines)
            search_end_line = min(len(lines), end_idx + window_lines)

            # Convert line range to character offsets
            search_start_char = content.find("\n".join(lines[:search_start_line]))
            if search_start_char == -1:
                search_start_char = 0
            search_end_char = content.find("\n".join(lines[:search_end_line]))
            if search_end_char == -1:
                search_end_char = len(content)

            matcher = difflib.SequenceMatcher(
                None,
                content[search_start_char:search_end_char],
                target_snippet,
            )
            match = matcher.find_longest_match(
                0, search_end_char - search_start_char, 0, len(target_snippet)
            )

            if match.size < len(target_snippet) * 0.7:
                # If not found in window, try global search as last resort
                matcher = difflib.SequenceMatcher(None, content, target_snippet)
                match = matcher.find_longest_match(
                    0, len(content), 0, len(target_snippet)
                )
                match_offset = 0
            else:
                match_offset = search_start_char

            if match.size < len(target_snippet) * 0.7:  # Threshold for safety
                return False

            # Reconstruct content with replacement
            actual_match_start = match_offset + match.a
            new_content = (
                content[:actual_match_start]
                + new_snippet
                + content[actual_match_start + match.size :]
            )
            file_path.write_text(new_content, encoding="utf-8")
            return True

        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except (OSError, ValueError) as exc:
        console.print(f"[red]Error during patch application: {exc}[/red]")
        return False


if __name__ == "__main__":
    main()
