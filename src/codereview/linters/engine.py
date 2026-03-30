"""Engine to orchestrate multiple linters."""

import asyncio
from pathlib import Path

from codereview.linters.base import BaseLinter
from codereview.linters.result import LinterResult


class Engine:
    """Orchestrator to run multiple linters."""

    # pylint: disable=too-few-public-methods

    def __init__(self, linters: list[BaseLinter]) -> None:
        """Initialize the engine with a list of linters.

        Args:
            linters: A list of linter instances to execute.
        """
        self.linters = linters

    async def run_all(self, target: Path) -> list[LinterResult]:
        """Run all configured linters on the target in parallel using asyncio.

        Args:
            target: The file or directory to scan.

        Returns:
            A combined list of all linter results.
        """
        all_results: list[LinterResult] = []

        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(linter.run(target)) for linter in self.linters]

        for task in tasks:
            try:
                results = task.result()
                all_results.extend(results)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Log the error but keep results from other linters
                print(f"Linter task failed: {exc}")

        return all_results
