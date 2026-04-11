"""Context extraction utilities for linters and AI fixing."""

from pathlib import Path


def extract_snippet(
    file_path: Path,
    line_start: int,
    line_end: int | None = None,
    context_lines: int = 5,
) -> str:
    """Extract a raw snippet of code without line numbers.

    This is used for AI context and for applying patches.

    Args:
        file_path: Path to the target file.
        line_start: 1-indexed starting line number of the error.
        line_end: 1-indexed ending line number of the error (optional).
        context_lines: Number of surrounding lines to include.

    Returns:
        The raw string content of the snippet.
    """
    if not file_path.is_file():
        return ""

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Find bounds
        start_index = max(0, line_start - 1 - context_lines)
        if line_end is None:
            end_index = min(len(lines), line_start + context_lines)
        else:
            end_index = min(len(lines), line_end + context_lines)

        return "\n".join(lines[start_index:end_index])
    except (OSError, UnicodeDecodeError):
        return ""


def format_snippet(snippet: str, start_line: int) -> str:
    """Add line numbers to a raw snippet for terminal display.

    Args:
        snippet: The raw code snippet.
        start_line: The 1-indexed line number of the first line in the snippet.

    Returns:
        A formatted string with line numbers.
    """
    if not snippet:
        return ""

    lines = snippet.splitlines()
    return "\n".join(f"{start_line + i:4d} | {line}" for i, line in enumerate(lines))


def get_context_bounds(file_path: Path, line_start: int) -> tuple[int, str]:
    """Find the semantic context (function/class) containing the line.

    Args:
        file_path: Path to the target file.
        line_start: Line number where the error occurred.

    Returns:
        A tuple of (start_index, info_string) where info_string describes
        the block (e.g., "in function my_func").
    """
    if not file_path.is_file():
        return 0, "unknown context"

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        current_idx = line_start - 1

        # Search upwards for def or class
        for i in range(current_idx, -1, -1):
            line = lines[i].strip()
            if line.startswith(("def ", "class ")):
                # Return the starting index and a description
                return i, f"in {line.split('(')[0].split(':')[0].strip()}"

        return max(0, current_idx - 10), "in module scope"
    except (OSError, UnicodeDecodeError):
        return 0, "unknown context"


def get_linter_context(
    file_path: Path,
    line_start: int,
    line_end: int | None = None,
    context_lines: int = 10,
) -> tuple[str, int, str]:
    """Return the raw snippet, its start line, and semantic info in one call.

    Convenience wrapper that combines ``extract_snippet`` and
    ``get_context_bounds`` into the single tuple expected by linter parsers.

    Args:
        file_path: Path to the source file.
        line_start: 1-indexed line number where the issue begins.
        line_end: 1-indexed ending line number of the issue (optional).
        context_lines: Number of surrounding lines to include in the snippet.

    Returns:
        A three-tuple of ``(raw_snippet, snippet_start_line, semantic_info)``
        where ``raw_snippet`` is the code text, ``snippet_start_line`` is the
        1-indexed first line of the snippet, and ``semantic_info`` is a string
        like ``"in def my_func"``.
    """
    _, semantic_info = get_context_bounds(file_path, line_start)
    raw_snippet = extract_snippet(file_path, line_start, line_end, context_lines)
    snippet_start_line = max(1, line_start - context_lines)

    return raw_snippet, snippet_start_line, semantic_info
