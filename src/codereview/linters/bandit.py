"""Bandit linter implementation."""

import json
from pathlib import Path

from codereview.linters.base import AsyncCompletedProcess, BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class BanditLinter(BaseLinter):
    """Linter implementation for Bandit (Security scanner)."""

    name = "Bandit"

    def build_command(self, target: Path) -> list[str]:
        """Build the Bandit command for the target path."""
        target_str = str(target.absolute())
        args = ["-r", target_str] if target.is_dir() else [target_str]
        return ["uv", "run", "bandit", "-f", "json"] + args

    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse Bandit JSON output."""

        try:
            output = json.loads(process_result.stdout)
            errors = output.get("results", [])
        except json.JSONDecodeError:
            return []

        parsed_results = []
        for error in errors:
            file_path = Path(error.get("filename", target.name))

            line_start = error.get("line_number", 1)
            line_range = error.get("line_range", [])
            line_end = max(line_range) if line_range else line_start

            error_code = error.get("test_id", "Unknown")
            issue_text = error.get("issue_text", "Unknown security issue")
            severity = error.get("issue_severity", "LOW")
            message = f"[{severity}] {issue_text}"

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
                    col_start=None,
                    col_end=None,
                    linter_name=self.name,
                    error_code=error_code,
                    message=message,
                    snippet_context=snippet,
                )
            )

        return parsed_results
