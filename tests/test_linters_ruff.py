"""Tests for linter configurations and runners."""

import json

import pytest

from codereview.linters import RuffLinter
from codereview.linters.base import AsyncCompletedProcess


@pytest.mark.asyncio
async def test_ruff_linter_run(mocker, tmp_path) -> None:
    """Test Ruff execution and JSON parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("import os  # unused", encoding="utf-8")

    fake_output = [
        {
            "code": "F401",
            "message": "'os' imported but unused",
            "filename": str(test_file),
            "location": {"row": 1, "column": 1},
            "end_location": {"row": 1, "column": 10},
        }
    ]

    mock_result = AsyncCompletedProcess(
        stdout=json.dumps(fake_output), stderr="", returncode=0
    )

    mocker.patch.object(RuffLinter, "_run_command", return_value=mock_result)

    linter = RuffLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Ruff"
    assert results[0].error_code == "F401"
    assert results[0].file_path == test_file
    assert "import os" in results[0].snippet_context
