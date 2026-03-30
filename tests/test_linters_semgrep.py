"""Tests for Semgrep linter."""

import json

import pytest

from codereview.linters.base import AsyncCompletedProcess
from codereview.linters.semgrep import SemgrepLinter


@pytest.mark.asyncio
async def test_semgrep_run(mocker, tmp_path) -> None:
    """Test Semgrep execution and JSON parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("import unsafe", encoding="utf-8")

    fake_output = {
        "results": [
            {
                "check_id": "rules.unsafe-import",
                "path": str(test_file),
                "start": {"line": 1, "col": 1},
                "end": {"line": 1, "col": 15},
                "extra": {
                    "message": "Found unsafe import",
                    "severity": "WARNING",
                },
            }
        ]
    }

    mock_result = AsyncCompletedProcess(
        stdout=json.dumps(fake_output), stderr="", returncode=0
    )
    mocker.patch.object(SemgrepLinter, "_run_command", return_value=mock_result)

    linter = SemgrepLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Semgrep"
    assert results[0].error_code == "rules.unsafe-import"
    assert "[WARNING]" in results[0].message
