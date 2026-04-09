"""Main entry point for the CodeReview CLI package."""

import asyncio
from pathlib import Path

import click

from codereview.cli.fix_handler import handle_fix
from codereview.cli.init_handler import handle_init
from codereview.cli.scan_handler import handle_scan
from codereview.cli.ui import SCAN_RESULT_FILE


@click.group()
def main() -> None:
    """AI-powered code reviewer and auto-fixer."""


@main.command()
def init() -> None:  # vulture: ignore
    """Initialize configuration for CodeReview."""
    handle_init()


@main.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path))
@click.option("--only", help="Comma-separated list of linters to run")
@click.option("--skip", help="Comma-separated list of linters to skip")
@click.option(
    "-o",
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
def scan(  # vulture: ignore
    target: Path,
    only: str | None,
    skip: str | None,
    output: Path | None,
    verbose: bool,
) -> None:
    """Scan a target file or directory and save results to a JSON file."""
    asyncio.run(
        handle_scan(target, only, skip, output or SCAN_RESULT_FILE, verbose),
    )


@main.command()
@click.argument("target", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "-i",
    "--input",
    "input_file",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Path to the scan results JSON file (default: {SCAN_RESULT_FILE})",
)
def fix(  # vulture: ignore
    target: Path | None,
    input_file: Path | None,
) -> None:
    """Read scan results and interactively apply AI-suggested fixes.

    If the input results file does not exist, a scan will be performed
    automatically on the provided target.
    """
    asyncio.run(
        handle_fix(input_file or SCAN_RESULT_FILE, target),
    )


if __name__ == "__main__":
    main()
