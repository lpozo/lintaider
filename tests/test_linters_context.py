"""Tests for context extraction."""

from codereview.linters.context import extract_snippet


def test_extract_snippet(tmp_path) -> None:
    """Test extracting a snippet from a file."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "def foo():\n    pass\n\ndef bar():\n    return 1\n", encoding="utf-8"
    )

    snippet = extract_snippet(test_file, line_start=2, context_lines=1)

    expected = "   1 | def foo():\n   2 |     pass\n   3 | "
    assert snippet == expected
