"""MyPy linter implementation."""

import re
from pathlib import Path

from codereview.linters.base import BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class MyPyLinter(BaseLinter):
    """Linter implementation for MyPy (Static type checker)."""

    name = "MyPy"

    async def run(self, target: Path) -> list[LinterResult]:
        """Run MyPy on the target and parse the text output."""
        cmd = [
            "uv",
            "run",
            "mypy",
            "--show-column-numbers",
            "--show-error-codes",
            "--no-error-summary",
            str(target.absolute()),
        ]
        result = await self._run_command(cmd, Path.cwd())

        pattern = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*"
            r"(?P<severity>error|warning|note):\s*"
            r"(?P<msg>.+?)\s*\[(?P<code>.+?)\]$"
        )

        parsed_results = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if not match:
                continue

            file_path = Path(match.group("file"))
            line_start = int(match.group("line"))
            col_start = int(match.group("col"))
            message = match.group("msg")
            error_code = match.group("code")

            snippet = extract_snippet(
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,
                context_lines=3,
            )

            parsed_results.append(
                LinterResult(
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_start,
                    col_start=col_start,
                    col_end=None,
                    linter_name=self.name,
                    error_code=error_code,
                    message=message,
                    snippet_context=snippet,
                )
            )

        return parsed_results
