"""Tests for Vulture linter."""

import pytest

from codereview.linters.base import AsyncCompletedProcess
from codereview.linters.vulture import VultureLinter


@pytest.mark.asyncio
async def test_vulture_run(mocker, tmp_path) -> None:
    """Test Vulture execution and regex parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("unused_var = 1", encoding="utf-8")

    fake_stdout = f"{test_file}:1: unused variable 'unused_var' (60% confidence)\n"

    mock_result = AsyncCompletedProcess(stdout=fake_stdout, stderr="", returncode=0)
    mocker.patch.object(VultureLinter, "_run_command", return_value=mock_result)

    linter = VultureLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Vulture"
    assert results[0].line_start == 1
    assert "unused variable" in results[0].message
