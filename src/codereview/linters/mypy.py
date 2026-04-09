"""MyPy linter implementation."""

import re
from pathlib import Path

from codereview.linters.base import AsyncCompletedProcess, BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class MyPyLinter(BaseLinter):
    """Linter implementation for MyPy (Static type checker)."""

    name = "MyPy"

    def build_command(self, target: Path) -> list[str]:
        """Build the MyPy command for the target path.

        Args:
            target: The file or directory to scan.

        Returns:
            A list of command arguments.
        """
        return [
            "uv",
            "run",
            "mypy",
            "--show-column-numbers",
            "--show-error-codes",
            "--no-error-summary",
            str(target.absolute()),
        ]

    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse MyPy text output.

        Args:
            process_result: The completed process result.
            target: The target that was scanned.

        Returns:
            A list of standardized linter results.
        """

        pattern = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*"
            r"(?P<severity>error|warning|note):\s*"
            r"(?P<msg>.+?)\s*\[(?P<code>.+?)\]$"
        )

        parsed_results = []
        for line in process_result.stdout.splitlines():
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
