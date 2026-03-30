"""Context extraction utilities."""

from pathlib import Path


def extract_snippet(
    file_path: Path,
    line_start: int,
    line_end: int | None = None,
    context_lines: int = 3,
) -> str:
    """Extract a snippet of code with surrounding context lines.

    Args:
        file_path: Path to the target file.
        line_start: 1-indexed starting line number of the error.
        line_end: 1-indexed ending line number of the error (optional).
        context_lines: Number of surrounding lines to include.

    Returns:
        String containing the code snippet formatted with line numbers.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file cannot be read as UTF-8.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    start_index = max(0, line_start - 1 - context_lines)

    if line_end is None:
        end_index = min(len(lines), line_start + context_lines)
    else:
        end_index = min(len(lines), line_end + context_lines)

    extracted_lines = lines[start_index:end_index]

    return "\n".join(
        f"{start_index + index + 1:4d} | {line}"
        for index, line in enumerate(extracted_lines)
    )
