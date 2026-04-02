"""Data models for the code reviewer."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "file_path": str(self.file_path),
            "line_start": self.line_start,
            "line_end": self.line_end,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "linter_name": self.linter_name,
            "error_code": self.error_code,
            "message": self.message,
            "snippet_context": self.snippet_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinterResult":
        """Reconstruct a LinterResult from a dict (e.g., loaded from JSON)."""
        return cls(
            file_path=Path(data["file_path"]),
            line_start=data["line_start"],
            line_end=data.get("line_end"),
            col_start=data.get("col_start"),
            col_end=data.get("col_end"),
            linter_name=data["linter_name"],
            error_code=data["error_code"],
            message=data["message"],
            snippet_context=data.get("snippet_context", ""),
        )
