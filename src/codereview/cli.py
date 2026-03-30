"""Command-line interface for the code reviewer."""

import asyncio
import difflib
from pathlib import Path
from typing import Any, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from codereview.ai import AIFactory
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


@click.group()
def main() -> None:
    """AI-powered code reviewer and auto-fixer."""


@main.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--provider", default="local", help="AI Provider (local, cloud)")
@click.option("--model", help="AI Model name override")
@click.option("--only", help="Comma-separated list of linters to run")
@click.option("--skip", help="Comma-separated list of linters to skip")
def scan(
    target: Path,
    provider: str,
    model: str | None,
    only: str | None,
    skip: str | None,
) -> None:
    """Scan a target file or directory and suggest AI fixes."""
    asyncio.run(_async_scan(target, provider, model, only, skip))


async def _async_scan(
    target: Path,
    provider_name: str,
    model: str | None,
    only: str | None,
    skip: str | None,
) -> None:
    """Asynchronous implementation of the scan command."""
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

    console.print(f"[bold red]Found {len(results)} issues.[/bold red]")

    # Initialize AI Provider using Factory
    try:
        ai = AIFactory.create(provider_name, model)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return

    # Background AI Task Orchestration with Rate Limiting
    # We use a semaphore to process one AI request at a time and add a small delay
    ai_semaphore = asyncio.Semaphore(1)

    async def _wrapped_generate_fixes(res: Any) -> Any:
        async with ai_semaphore:
            fixes = await ai.generate_fixes(res)
            # Retraso prudente entre peticiones para evitar Rate Limit
            await asyncio.sleep(0.5)
            return fixes

    # Launch all tasks immediately in background
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

        # Await the specific task for this result
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

        # Non-blocking prompt (runs in a separate thread so other AI tasks can continue)
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
