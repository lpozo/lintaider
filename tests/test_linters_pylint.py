"""Tests for Pylint runner."""

import json

import pytest

from codereview.linters.base import AsyncCompletedProcess
from codereview.linters.pylint import PylintLinter


@pytest.mark.asyncio
async def test_pylint_run(mocker, tmp_path) -> None:
    """Test Pylint execution and JSON parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("import os", encoding="utf-8")

    fake_output = [
        {
            "line": 1,
            "column": 0,
            "endLine": 1,
            "endColumn": 9,
            "path": str(test_file),
            "symbol": "unused-import",
            "message": "Unused import os",
            "message-id": "W0611",
        }
    ]

    mock_result = AsyncCompletedProcess(
        stdout=json.dumps(fake_output), stderr="", returncode=0
    )
    mocker.patch.object(PylintLinter, "_run_command", return_value=mock_result)

    linter = PylintLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Pylint"
    assert results[0].error_code == "W0611"
    assert "import os" in results[0].snippet_context
