import ast
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SymbolInfo:
    """Information about a public symbol (class or function)."""

    name: str
    kind: str  # "class" or "function"
    line: int
    file_path: Path


@dataclass
class ProjectSummary:
    """Compact summary of a target project."""

    file_tree: list[str] = field(default_factory=list)
    public_symbols: list[SymbolInfo] = field(default_factory=list)
    common_imports: set[str] = field(default_factory=set)
    target_config: dict[str, Any] = field(default_factory=dict)


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
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        innermost_node = None
        innermost_level = -1

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Check if it contains the line
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno)
                if start <= line_start <= end:
                    # Find depth (approximate by node hierarchy if we used a visitor, 
                    # but simple lineno comparison works for nested blocks)
                    if innermost_node is None or node.lineno >= innermost_node.lineno:
                        innermost_node = node

        if innermost_node:
            kind = "class" if isinstance(innermost_node, ast.ClassDef) else "def"
            return innermost_node.lineno - 1, f"in {kind} {innermost_node.name}"

        return max(0, line_start - 10), "in module scope"
    except (OSError, UnicodeDecodeError, SyntaxError):
        # Fallback to simple string search if AST fails
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            current_idx = line_start - 1
            for i in range(current_idx, -1, -1):
                line = lines[i].strip()
                if line.startswith(("def ", "class ")):
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
    snippet_start_idx, semantic_info = get_context_bounds(file_path, line_start)
    raw_snippet = extract_snippet(file_path, line_start, line_end, context_lines)
    snippet_start_line = snippet_start_idx + 1

    return raw_snippet, snippet_start_line, semantic_info


def get_project_summary(target_path: Path) -> ProjectSummary:
    """Generate a compact summary of the target project.

    Scans the directory for Python files, extracts public symbols, and
    parses project configuration.

    Args:
        target_path: Path to the project root or a single file.

    Returns:
        A ProjectSummary object.
    """
    summary = ProjectSummary()
    if target_path.is_file():
        summary.file_tree = [target_path.name]
        summary.public_symbols.extend(_extract_symbols(target_path))
        return summary

    # Discover and parse target config
    summary.target_config = parse_target_config(target_path)

    # Scan for files and symbols
    python_files = list(target_path.rglob("*.py"))
    # Limit number of files and symbols to avoid token bloat
    target_files = sorted(python_files)[:50]

    for py_file in target_files:
        rel_path = py_file.relative_to(target_path)
        summary.file_tree.append(str(rel_path))

        if "__init__" not in py_file.name:
            summary.public_symbols.extend(_extract_symbols(py_file, target_path))

    return summary


def parse_target_config(target_path: Path) -> dict[str, Any]:
    """Search for and parse target-specific linter configurations.

    Args:
        target_path: Path to the project root.

    Returns:
        A dictionary containing relevant linter configurations.
    """
    config_data: dict[str, Any] = {}
    pyproject = target_path / "pyproject.toml"

    if pyproject.is_file():
        try:
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
                # Extract relevant tool sections
                tool = data.get("tool", {})
                for key in ["ruff", "pylint", "mypy", "vulture"]:
                    if key in tool:
                        config_data[key] = tool[key]
        except (OSError, ValueError):
            pass

    return config_data


def _extract_symbols(file_path: Path, root_path: Path | None = None) -> list[SymbolInfo]:
    """Extract top-level public classes and functions from a file."""
    symbols = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    symbols.append(
                        SymbolInfo(
                            name=node.name,
                            kind=kind,
                            line=node.lineno,
                            file_path=file_path.relative_to(root_path)
                            if root_path
                            else file_path,
                        )
                    )
    except (OSError, UnicodeDecodeError, SyntaxError):
        pass
    return symbols[:10]  # Limit symbols per file
