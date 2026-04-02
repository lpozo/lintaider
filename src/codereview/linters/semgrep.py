"""Semgrep linter implementation for semantic analysis."""

import json
from pathlib import Path

from codereview.linters.base import AsyncCompletedProcess, BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class SemgrepLinter(BaseLinter):
    """Linter implementation for Semgrep."""

    name = "Semgrep"

    def build_command(self, target: Path) -> list[str]:
        """Build the Semgrep command for the target path."""
        return [
            "uv",
            "run",
            "semgrep",
            "scan",
            "--config",
            "auto",
            "--json",
            str(target.absolute()),
        ]

    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse Semgrep JSON output."""

        try:
            data = json.loads(process_result.stdout)
            findings = data.get("results", [])
        except json.JSONDecodeError:
            return []

        parsed_results = []
        for finding in findings:
            file_path = Path(finding.get("path", str(target)))

            line_start = finding.get("start", {}).get("line", 1)
            col_start = finding.get("start", {}).get("col", 1)
            line_end = finding.get("end", {}).get("line")
            col_end = finding.get("end", {}).get("col")

            extra = finding.get("extra", {})
            error_code = finding.get("check_id", "Unknown")
            severity = extra.get("severity", "WARNING").upper()
            message = f"[{severity}] {extra.get('message', 'No message')}"

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
