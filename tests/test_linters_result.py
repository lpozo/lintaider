"""Tests for data models."""

from pathlib import Path

from codereview.linters.result import LinterResult


def test_linter_result_creation() -> None:
    """Test standard dictionary creation for LinterResult."""
    result = LinterResult(
        file_path=Path("test.py"),
        line_start=1,
        line_end=None,
        col_start=None,
        col_end=None,
        linter_name="TestLinter",
        error_code="T001",
        message="A test error",
        snippet_context="def func(): pass",
    )

    assert result.linter_name == "TestLinter"
    assert result.file_path == Path("test.py")
    assert result.error_code == "T001"
