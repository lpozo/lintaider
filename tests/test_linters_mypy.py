"""Tests for MyPy runner."""

import pytest

from codereview.linters.base import AsyncCompletedProcess
from codereview.linters.mypy import MyPyLinter


@pytest.mark.asyncio
async def test_mypy_run(mocker, tmp_path) -> None:
    """Test MyPy execution and regex parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1", encoding="utf-8")

    fake_stdout = f"{test_file}:1:5: error: Incompatible types [misc]\n"

    mock_result = AsyncCompletedProcess(stdout=fake_stdout, stderr="", returncode=1)
    mocker.patch.object(MyPyLinter, "_run_command", return_value=mock_result)

    linter = MyPyLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "MyPy"
    assert results[0].error_code == "misc"
    assert results[0].line_start == 1
    assert results[0].col_start == 5
    assert "x = 1" in results[0].snippet_context
