"""Tests for the Linter Engine Orchestrator."""

from pathlib import Path

import pytest

from codereview.linters import BaseLinter, Engine
from codereview.linters.result import LinterResult


class MockLinter(BaseLinter):
    """A mock linter that returns predefined results."""

    def __init__(self, name: str, return_list: list[LinterResult]) -> None:
        self._name = name
        self._returns = return_list

    @property
    def name(self) -> str:
        return self._name

    async def run(self, target: Path) -> list[LinterResult]:
        return self._returns


@pytest.mark.asyncio
async def test_engine_run_all() -> None:
    """Test that the engine combines results from multiple linters."""
    res1 = LinterResult(Path("x.py"), 1, None, None, None, "L1", "E1", "Msg1", "")
    res2 = LinterResult(Path("y.py"), 2, None, None, None, "L2", "E2", "Msg2", "")

    mock_linter1 = MockLinter("Linter1", [res1])
    mock_linter2 = MockLinter("Linter2", [res1, res2])

    engine = Engine(linters=[mock_linter1, mock_linter2])
    results = await engine.run_all(Path())

    assert len(results) == 3
    assert results[0].linter_name == "L1"
    assert results[2].linter_name == "L2"
