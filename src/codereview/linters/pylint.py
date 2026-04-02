"""Pylint linter implementation."""

import json
from pathlib import Path

from codereview.linters.base import AsyncCompletedProcess, BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class PylintLinter(BaseLinter):
    """Linter implementation for Pylint."""

    name = "Pylint"

    def build_command(self, target: Path) -> list[str]:
        """Build the Pylint command for the target path."""
        return [
            "uv",
            "run",
            "pylint",
            "--output-format=json",
            str(target.absolute()),
        ]

    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse Pylint JSON output."""

        try:
            errors = json.loads(process_result.stdout)
        except json.JSONDecodeError:
            return []

        parsed_results = []
        for error in errors:
            file_path = Path(error.get("path", target.name))

            line_start = error.get("line", 1)
            col_start = error.get("column", 1)
            line_end = error.get("endLine")
            col_end = error.get("endColumn")

            error_code = error.get("message-id", error.get("symbol", "Unknown"))
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
