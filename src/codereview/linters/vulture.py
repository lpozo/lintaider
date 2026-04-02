"""Vulture linter implementation for finding dead code."""

import re
from pathlib import Path

from codereview.linters.base import BaseLinter
from codereview.linters.context import extract_snippet
from codereview.linters.result import LinterResult


class VultureLinter(BaseLinter):
    """Linter implementation for Vulture."""

    name = "Vulture"

    async def run(self, target: Path) -> list[LinterResult]:
        """Run Vulture on the target and parse the text output."""
        cmd = ["uv", "run", "vulture", str(target.absolute())]
        result = await self._run_command(cmd, Path.cwd())

        # Regex for Vulture output: filename:lineno: message
        pattern = re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*(?P<msg>.+)$")

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
            message = match.group("msg")

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
                    col_start=None,
                    col_end=None,
                    linter_name=self.name,
                    error_code="unused-code",
                    message=message,
                    snippet_context=snippet,
                )
            )

        return parsed_results
