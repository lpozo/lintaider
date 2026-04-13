"""Handler for the 'scan' command."""

import json
from collections import Counter
from pathlib import Path

from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from lintaider.cli.ui import HUMAN_READABLE_REPORT_FILE, console
from lintaider.config import Config
from lintaider.linters import LINTER_MAP, Engine
from lintaider.linters.result import LinterResult


async def handle_scan(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    target: Path,
    only: str | None,
    skip: str | None,
    output: Path,
    verbose: bool = False,
    human_readable: bool = False,
) -> None:
    """Run all active linters on a target path and write results to JSON.

    Linters are executed in parallel. Progress is rendered in the terminal.
    When no issues are found, a success message is printed and no file is
    written.

    Args:
        target: The file or directory to scan.
        only: Optional comma-separated list of linter names to run exclusively.
            Overrides the ``only_linters`` value from config.
        skip: Optional comma-separated list of linter names to skip.
            Overrides the ``skip_linters`` value from config.
        output: Path to the JSON file where results will be saved.
        verbose: When ``True``, prints a detailed panel for every issue found.
        human_readable: When ``True``, also writes a markdown report to
            ``linting-report.md``.
    """
    console.print(f"[bold blue]Scanning {target}...[/bold blue]")

    config = Config.load()
    active_linters = _get_active_linters(config, only, skip)

    # Use the linter mapping to instantiate the active linters
    engine = Engine(linters=[LINTER_MAP[name]() for name in active_linters])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            "[cyan]Running linters...", total=len(active_linters)
        )

        def progress_cb() -> None:
            progress.update(task_id, advance=1)

        results = await engine.run_all(target, progress_callback=progress_cb)

    # Logical Sort: by file then line
    results.sort(key=lambda r: (str(r.file_path), r.line_start))

    if not results:
        console.print("[bold green]No issues found! 🎉[/bold green]")

    if results:
        _print_scan_summary(results, verbose)

    # Always serialize to JSON to keep output behavior deterministic.
    output.write_text(
        json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8"
    )
    console.print(f"\n[bold green]Results saved to {output}[/bold green]")

    if human_readable:
        report_markdown = _build_markdown_report(target, results)
        HUMAN_READABLE_REPORT_FILE.write_text(
            report_markdown, encoding="utf-8"
        )
        console.print(
            "[bold green]Human-readable report saved to "
            f"{HUMAN_READABLE_REPORT_FILE}[/bold green]"
        )

    console.print(
        "[dim]Run 'lintaider fix' to get AI suggestions and apply patches.[/dim]"
    )


def _build_markdown_report(target: Path, results: list[LinterResult]) -> str:
    """Build a markdown linting report from linter results.

    Args:
        target: The file or directory that was scanned.
        results: Sorted list of linter results.

    Returns:
        A markdown string suitable for human-readable sharing.
    """
    counts: Counter[str] = Counter(r.linter_name for r in results)
    lines: list[str] = [
        "# Linting Report",
        "",
        f"- Target: `{target}`",
        f"- Total issues: **{len(results)}**",
        "",
        "## Summary",
        "",
        "| Linter | Issues |",
        "| --- | ---: |",
    ]

    if counts:
        for linter, count in sorted(counts.items()):
            lines.append(f"| {linter} | {count} |")
    else:
        lines.append("| None | 0 |")

    lines.extend(["", "## Findings", ""])

    if not results:
        lines.append("No issues found.")
        lines.append("")
        return "\n".join(lines)

    for idx, result in enumerate(results, start=1):
        location = f"{result.file_path}:{result.line_start}"
        if result.col_start is not None:
            location += f":{result.col_start}"

        lines.extend(
            [
                f"### {idx}. {result.linter_name} [{result.error_code}]",
                "",
                f"- Location: `{location}`",
                f"- Message: {result.message}",
            ]
        )

        if result.snippet_context:
            lines.extend(["", "```python", result.snippet_context, "```"])

        lines.append("")

    return "\n".join(lines)


def _parse_linter_names(names: str | None, default: list[str]) -> list[str]:
    """Parse a comma-separated linter name string into a normalised list.

    Args:
        names: Comma-separated linter names, or ``None`` to use the default.
        default: The list to return when ``names`` is ``None`` or empty.

    Returns:
        A list of lowercase linter name strings.
    """
    if not names:
        return default
    return [name.strip().lower() for name in names.split(",")]


def _get_active_linters(
    config: Config, only: str | None, skip: str | None
) -> list[str]:
    """Determine which linters to run based on config and CLI flag overrides.

    CLI flags take precedence over config file values. ``only`` is applied
    before ``skip``.

    Args:
        config: The loaded configuration supplying default filter lists.
        only: Optional comma-separated linter names to run exclusively.
        skip: Optional comma-separated linter names to exclude.

    Returns:
        An ordered list of active linter name strings.
    """
    only_list = _parse_linter_names(only, config.only_linters)
    skip_list = _parse_linter_names(skip, config.skip_linters)

    active_linters = list(LINTER_MAP.keys())
    if only_list:
        active_linters = [name for name in active_linters if name in only_list]
    if skip_list:
        active_linters = [
            name for name in active_linters if name not in skip_list
        ]
    return active_linters


def _print_scan_summary(results: list[LinterResult], verbose: bool) -> None:
    """Print a findings summary table, and detailed panels when verbose.

    Args:
        results: The list of linter results to display.
        verbose: When ``True``, prints a rich panel for each individual issue
            including the code snippet context.
    """
    counts: Counter[str] = Counter(r.linter_name for r in results)

    table = Table(title="[bold red]Findings Summary[/bold red]")
    table.add_column("Linter", style="cyan", no_wrap=True)
    table.add_column("Issues Found", justify="right", style="magenta")

    for linter, count in sorted(counts.items()):
        table.add_row(linter, str(count))

    console.print(table)

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
