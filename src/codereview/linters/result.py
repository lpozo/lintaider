"""Data models for the code reviewer."""

from dataclasses import dataclass
from pathlib import Path


# pylint: disable=too-many-instance-attributes
@dataclass
class LinterResult:
    """Standardized output representing an error from any linter.

    Attributes:
        file_path: Path to the file containing the error.
        line_start: 1-indexed starting line number of the error.
        line_end: 1-indexed ending line number of the error, if available.
        col_start: 1-indexed starting column number, if available.
        col_end: 1-indexed ending column number, if available.
        linter_name: Name of the linter that produced the error.
        error_code: The specific error code from the linter.
        message: The descriptive error message.
        snippet_context: The code surrounding the error, for AI context.
    """

    file_path: Path
    line_start: int
    line_end: int | None
    col_start: int | None
    col_end: int | None
    linter_name: str
    error_code: str
    message: str
    snippet_context: str = ""
