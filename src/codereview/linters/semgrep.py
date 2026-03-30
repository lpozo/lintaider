"""Semgrep linter implementation for semantic analysis."""

import json
from pathlib import Path

from codereview.linters.base import BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class SemgrepLinter(BaseLinter):
    """Linter implementation for Semgrep."""

    @property
    def name(self) -> str:
        """Return the linter name."""
        return "Semgrep"

    async def run(self, target: Path) -> list[LinterResult]:
        """Run Semgrep on the target and parse the JSON output."""
        cmd = [
            "uv",
            "run",
            "semgrep",
            "scan",
            "--config",
            "auto",
            "--json",
            str(target.absolute()),
        ]
        result = await self._run_command(cmd, Path.cwd())

        try:
            data = json.loads(result.stdout)
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
