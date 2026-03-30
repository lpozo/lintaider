"""Tests for Pyright linter."""

import json

import pytest

from codereview.linters.base import AsyncCompletedProcess
from codereview.linters.pyright import PyrightLinter


@pytest.mark.asyncio
async def test_pyright_run(mocker, tmp_path) -> None:
    """Test Pyright execution and JSON parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x: int = 'a'", encoding="utf-8")

    fake_output = {
        "generalDiagnostics": [
            {
                "file": str(test_file),
                "severity": "error",
                "message": 'Expression of type "str" cannot be assigned',
                "rule": "reportGeneralTypeIssues",
                "range": {
                    "start": {"line": 0, "character": 9},
                    "end": {"line": 0, "character": 12},
                },
            }
        ]
    }

    mock_result = AsyncCompletedProcess(
        stdout=json.dumps(fake_output), stderr="", returncode=0
    )
    mocker.patch.object(PyrightLinter, "_run_command", return_value=mock_result)

    linter = PyrightLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Pyright"
    assert results[0].line_start == 1
    assert results[0].col_start == 10
    assert "[ERROR]" in results[0].message
