"""Tests for Bandit runner."""

import json

import pytest

from codereview.linters.bandit import BanditLinter
from codereview.linters.base import AsyncCompletedProcess


@pytest.mark.asyncio
async def test_bandit_run(mocker, tmp_path) -> None:
    """Test Bandit execution and JSON parsing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("import subprocess", encoding="utf-8")

    fake_output = {
        "results": [
            {
                "filename": str(test_file),
                "issue_severity": "LOW",
                "issue_text": "subprocess is bad",
                "line_number": 1,
                "line_range": [1],
                "test_id": "B404",
            }
        ]
    }

    mock_result = AsyncCompletedProcess(
        stdout=json.dumps(fake_output), stderr="", returncode=0
    )
    mocker.patch.object(BanditLinter, "_run_command", return_value=mock_result)

    linter = BanditLinter()
    results = await linter.run(test_file)

    assert len(results) == 1
    assert results[0].linter_name == "Bandit"
    assert results[0].error_code == "B404"
    assert "[LOW]" in results[0].message
    assert "import subprocess" in results[0].snippet_context
