"""Bandit linter implementation."""

import json
from pathlib import Path

from codereview.linters.base import BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class BanditLinter(BaseLinter):
    """Linter implementation for Bandit (Security scanner)."""

    name = "Bandit"

    async def run(self, target: Path) -> list[LinterResult]:
        """Run Bandit on the target and parse the JSON output."""
        target_str = str(target.absolute())
        args = ["-r", target_str] if target.is_dir() else [target_str]
        cmd = ["uv", "run", "bandit", "-f", "json"] + args

        result = await self._run_command(cmd, Path.cwd())

        try:
            output = json.loads(result.stdout)
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
