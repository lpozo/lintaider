"""Abstract base class for all linters."""

import abc
import asyncio
from dataclasses import dataclass
from pathlib import Path

from codereview.linters.result import LinterResult


@dataclass  # pylint: disable=too-few-public-methods
class AsyncCompletedProcess:
    """Mock-like class for asyncio.subprocess results."""

    stdout: str
    stderr: str
    returncode: int


class BaseLinter(abc.ABC):
    """Abstract base class for all linters."""

    name: str

    @abc.abstractmethod
    def build_command(self, target: Path) -> list[str]:
        """Build the command used to invoke the linter.

        Args:
            target: The file or directory to lint.

        Returns:
            A list of command arguments to pass to the subprocess.
        """

    @abc.abstractmethod
    def parse_output(
        self,
        process_result: AsyncCompletedProcess,
        target: Path,
    ) -> list[LinterResult]:
        """Parse process output into standardized linter results.

        Args:
            process_result: The completed process with stdout, stderr, and return code.
            target: The file or directory that was linted.

        Returns:
            A list of standardized LinterResult objects.
        """

    async def run(self, target: Path) -> list[LinterResult]:
        """Run the linter on the target path asynchronously.

        Args:
            target: The file or directory to lint.

        Returns:
            A list of standardized LinterResult objects.
        """
        cmd = self.build_command(target)
        process_result = await self._run_command(cmd, Path.cwd())
        return self.parse_output(process_result, target)

    async def _run_command(self, cmd: list[str], cwd: Path) -> AsyncCompletedProcess:
        """Helper to run a shell command asynchronously and capture output.

        Args:
            cmd: A list of command arguments.
            cwd: The working directory for the command.

        Returns:
            The completed process instance with output and return code.
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        return AsyncCompletedProcess(
            stdout=stdout.decode(encoding="utf-8"),
            stderr=stderr.decode(encoding="utf-8"),
            returncode=process.returncode or 0,
        )
