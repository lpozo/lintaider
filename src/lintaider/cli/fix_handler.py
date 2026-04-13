"""Handler for the 'fix' command."""

import asyncio
import difflib
import json
from pathlib import Path
from typing import Any

import click
from rich.panel import Panel
from rich.syntax import Syntax

from lintaider.ai import AIFixProposal, create_ai_provider
from lintaider.cli.scan_handler import handle_scan
from lintaider.cli.ui import console
from lintaider.config import Config
from lintaider.linters.context import (
    ProjectSummary,
    format_snippet,
    get_project_summary,
)
from lintaider.linters.result import LinterResult


async def handle_fix(
    input_file: Path,
    target: Path | None = None,
) -> None:
    """Load scan results and run the interactive AI fix workflow.

    If the results file does not exist and a ``target`` is provided, a scan
    is run first. AI fix proposals for all issues are requested concurrently
    in the background while the user steps through them one by one.

    Args:
        input_file: Path to the JSON file produced by ``lintaider scan``.
        target: Optional file or directory to auto-scan when ``input_file``
            is missing.
    """
    results = await _load_scan_results(input_file, target)
    if not results:
        return

    config = Config.load()
    console.print(
        f"[bold blue]Loaded {len(results)} issues from {input_file}[/bold blue]"
    )
    console.print(
        f"[dim]Using configured provider: {config.provider}:{config.model}[/dim]"
    )

    try:
        ai = create_ai_provider(config.provider, config.model, config.api_base)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return

    # Logical Sort: by file then line
    results.sort(key=lambda r: (str(r.file_path), r.line_start))

    # Determine target path for context summary
    target_path = target or Path.cwd()
    with console.status("[dim]Analyzing project context...[/dim]", spinner="dots"):
        project_summary = get_project_summary(target_path)

    # Launch AI tasks background orchestration
    ai_tasks = _orchestrate_ai_tasks(ai, results, project_summary)

    for idx, result in enumerate(results):
        await _process_fix_interactive(idx, len(results), result, ai_tasks[idx])


async def _load_scan_results(
    input_file: Path, target: Path | None
) -> list[LinterResult]:
    """Load scan results from disk, triggering an auto-scan if the file is missing.

    Args:
        input_file: Path to the JSON results file produced by ``lintaider scan``.
        target: Optional file or directory to scan when ``input_file`` is absent.

    Returns:
        A list of ``LinterResult`` objects, or an empty list on any failure.
    """
    if not input_file.exists():
        if target:
            console.print(
                f"[yellow]{input_file} not found. "
                f"Starting automatic scan of {target}...[/yellow]"
            )
            await handle_scan(target, only=None, skip=None, output=input_file)
        else:
            console.print(
                f"[bold red]Error:[/bold red] {input_file} not found.\n"
                "Please provide a target to scan: [bold]lintaider fix <target>[/bold]"
            )
            return []

    try:
        data = json.loads(input_file.read_text(encoding="utf-8"))
        results: list[LinterResult] = [LinterResult.from_dict(item) for item in data]
        if not results:
            console.print("[bold green]No issues to fix.[/bold green]")
            return []
        return results
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[bold red]Error reading {input_file}:[/bold red] {exc}")
        return []


def _orchestrate_ai_tasks(
    ai: Any, results: list[LinterResult], project_summary: ProjectSummary
) -> list[asyncio.Task[list[AIFixProposal]]]:
    """Launch concurrent AI fix-generation tasks, rate-limited by a semaphore.

    Args:
        ai: The active AI provider instance.
        results: All linter results to generate fixes for.
        project_summary: Project-wide context passed to each AI call.

    Returns:
        A list of asyncio tasks, one per result, each resolving to a list
        of ``AIFixProposal`` objects.
    """
    # Background AI Task Orchestration with Semaphore to avoid overloading
    ai_semaphore = asyncio.Semaphore(1)

    async def _wrapped_generate_fixes(
        res: LinterResult, summary: ProjectSummary
    ) -> list[AIFixProposal]:
        async with ai_semaphore:
            fixes: list[AIFixProposal] = await ai.generate_fixes(res, summary)
            await asyncio.sleep(0.5)
            return fixes

    return [
        asyncio.create_task(_wrapped_generate_fixes(result, project_summary))
        for result in results
    ]


async def _process_fix_interactive(
    idx: int,
    total: int,
    result: LinterResult,
    ai_task: asyncio.Task[list[AIFixProposal]],
) -> None:
    """Display one linter issue and apply the user-selected AI fix.

    Awaits the AI task, renders each proposal as a syntax-highlighted diff,
    and prompts the user to select an option or skip. Applies the chosen
    patch immediately.

    Args:
        idx: Zero-based index of the current issue.
        total: Total number of issues being processed.
        result: The linter result describing the issue.
        ai_task: Background task that resolves to a list of AI fix proposals.
    """
    console.print(
        Panel(
            f"[bold]{result.linter_name}[/bold] error {result.error_code} at "
            f"[yellow]{result.file_path}:{result.line_start}[/yellow]\n"
            f"{result.message}",
            title=f"Linter Error {idx + 1}/{total}",
            border_style="red",
        )
    )

    if result.snippet_context:
        formatted = format_snippet(result.snippet_context, result.snippet_start_line)
        syntax = Syntax(formatted, "python", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Original Context", border_style="yellow"))

    with console.status("[dim]Asking AI for a solution...[/dim]", spinner="dots"):
        proposals = await ai_task

    if not proposals:
        console.print("[red]AI failed to generate solutions for this issue.[/red]")
        return

    for i, prop in enumerate(proposals, start=1):
        console.print(f"\n[bold green]Option {i}:[/bold green]")
        console.print(Panel(prop.explanation, border_style="dim", title="AI Reasoning"))
        syntax = Syntax(prop.code_diff, "python", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Proposed Fix", border_style="green"))

    choice = await asyncio.to_thread(
        click.prompt,
        "Select an option to apply (1, 2, 3...) or 's' to skip",
        type=str,
        default="s",
    )
    choice = choice.lower()

    if choice == "s" or not choice.isdigit():
        console.print("[dim]Skipping...[/dim]\n")
        return

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
    """Apply an AI-generated patch to a file using fuzzy content matching.

    First attempts an exact match at the reported line number. Falls back to
    a ``difflib.SequenceMatcher`` search within a 100-line window, and then
    across the entire file, accepting a match when it covers at least 70 %
    of the original snippet length.

    Args:
        file_path: Path to the file to patch.
        line_start: 1-indexed line number where the original code begins.
        original_context: The snippet text to locate and replace.
        new_code: The replacement code to write in place of the original.

    Returns:
        ``True`` if the patch was applied successfully, ``False`` otherwise.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

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
            lines[start_idx:end_idx] = new_snippet.splitlines()
        else:
            window_lines = 100
            search_start_line = max(0, start_idx - window_lines)
            search_end_line = min(len(lines), end_idx + window_lines)

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
                matcher = difflib.SequenceMatcher(None, content, target_snippet)
                match = matcher.find_longest_match(
                    0, len(content), 0, len(target_snippet)
                )
                match_offset = 0
            else:
                match_offset = search_start_char

            if match.size < len(target_snippet) * 0.7:
                return False

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
