"""Tests for context extraction."""

from lintaider.linters.context import (
    extract_snippet,
    format_snippet,
    get_context_bounds,
    get_linter_context,
)


def test_extract_snippet(tmp_path) -> None:
    """Test extracting a raw snippet from a file."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "def foo():\n    pass\n\ndef bar():\n    return 1\n", encoding="utf-8"
    )

    # Test raw extraction
    snippet = extract_snippet(test_file, line_start=2, context_lines=1)
    expected = "def foo():\n    pass\n"
    assert snippet == expected


def test_format_snippet() -> None:
    """Test formatting a snippet with line numbers."""
    snippet = "line1\nline2"
    formatted = format_snippet(snippet, start_line=10)
    assert formatted == "  10 | line1\n  11 | line2"


def test_get_context_bounds(tmp_path) -> None:
    """Test finding the semantic context."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "class MyClass:\n    def my_func(self):\n        pass\n",
        encoding="utf-8",
    )

    # Inside function
    _, info = get_context_bounds(test_file, line_start=3)
    assert "def my_func" in info

    # At class level
    _, info = get_context_bounds(test_file, line_start=1)
    assert "class MyClass" in info


def test_get_linter_context(tmp_path) -> None:
    """Test the unified context helper."""
    test_file = tmp_path / "test.py"
    test_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    raw, start, info = get_linter_context(
        test_file, line_start=2, context_lines=1
    )
    assert raw == "line 1\nline 2\nline 3"
    assert start == 1
    assert "module scope" in info
