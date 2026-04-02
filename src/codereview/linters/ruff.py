"""Linter implementation for Ruff."""

import json
from pathlib import Path

from codereview.linters.base import AsyncCompletedProcess, BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class RuffLinter(BaseLinter):
    """Linter implementation for Ruff."""

    name = "Ruff"

    def build_command(self, target: Path) -> list[str]:
        """Build the Ruff command for the target path."""
        return [
            "uv",
            "run",
            "ruff",
            "check",
            "--output-format=json",
            str(target.absolute()),
        ]

    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse Ruff JSON output."""
        # pylint: disable=too-many-locals

        try:
            errors = json.loads(process_result.stdout)
        except json.JSONDecodeError:
            return []

        parsed_results = []
        for error in errors:
            file_path = Path(error.get("filename", ""))

            line_start = error.get("location", {}).get("row", 1)
            col_start = error.get("location", {}).get("column", 1)
            line_end = error.get("end_location", {}).get("row")
            col_end = error.get("end_location", {}).get("column")

            error_code = error.get("code", "Unknown")
            message = error.get("message", "Unknown error")

            snippet = extract_snippet(
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                context_lines=3,
            )

            parsed_results.append(
                LinterResult(
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_end,
                    col_start=col_start,
                    col_end=col_end,
                    linter_name=self.name,
                    error_code=error_code,
                    message=message,
                    snippet_context=snippet,
                )
            )

        return parsed_results
