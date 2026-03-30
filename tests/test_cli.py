"""Tests for the CodeReviewer CLI interface."""

from click.testing import CliRunner

from codereview.ai import AIFixProposal
from codereview.cli import main
from codereview.linters.result import LinterResult


def test_cli_scan_no_issues(mocker, tmp_path) -> None:
    """Test scanning a file with no issues."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("def ok():\n    return 1\n", encoding="utf-8")

    from unittest.mock import AsyncMock

    mocker.patch(
        "codereview.cli.Engine.run_all", new_callable=AsyncMock, return_value=[]
    )

    result = runner.invoke(main, ["scan", str(test_file)])
    assert result.exit_code == 0
    assert "No issues found" in result.output


def test_cli_scan_with_issues_skip(mocker, tmp_path) -> None:
    """Test scanning a file with an issue and typing 's' to skip."""
    runner = CliRunner()
    test_file = tmp_path / "error.py"
    test_file.write_text("import bad\n", encoding="utf-8")

    fake_result = LinterResult(
        file_path=test_file,
        line_start=1,
        line_end=1,
        col_start=1,
        col_end=10,
        linter_name="TestLinter",
        error_code="E1",
        message="A test error",
        snippet_context="import bad",
    )

    from unittest.mock import AsyncMock

    mocker.patch(
        "codereview.cli.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    proposal = AIFixProposal(explanation="Fix", code_diff="import good")
    mocker.patch(
        "codereview.ai.provider.LiteLLMProvider.generate_fixes",
        return_value=[proposal],
    )

    result = runner.invoke(main, ["scan", str(test_file)], input="s\n")

    assert result.exit_code == 0
    assert "Option 1: Fix" in result.output
    assert "Skipping" in result.output


def test_cli_scan_only_filter(mocker, tmp_path) -> None:
    """Test the --only flag for filtering linters."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("print(1)\n", encoding="utf-8")

    mock_engine = mocker.patch("codereview.cli.Engine")

    runner.invoke(main, ["scan", str(test_file), "--only", "ruff"])

    # Engine should be instantiated with only RuffLinter
    args, kwargs = mock_engine.call_args
    linters = kwargs.get("linters", []) or (args[0] if args else [])
    assert len(linters) == 1
    assert linters[0].__class__.__name__ == "RuffLinter"


def test_cli_scan_skip_filter(mocker, tmp_path) -> None:
    """Test the --skip flag for filtering linters."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("print(1)\n", encoding="utf-8")

    mock_engine = mocker.patch("codereview.cli.Engine")

    runner.invoke(
        main,
        ["scan", str(test_file), "--skip", "ruff,pylint,bandit,mypy,pyright,semgrep"],
    )

    args, kwargs = mock_engine.call_args
    linters = kwargs.get("linters", []) or (args[0] if args else [])
    # Only Vulture should remain
    assert len(linters) == 1
    assert linters[0].__class__.__name__ == "VultureLinter"


def test_cli_apply_patch_fuzzy(tmp_path) -> None:
    """Test that _apply_patch works even if lines have shifted."""
    from codereview.cli import _apply_patch

    test_file = tmp_path / "fuzzy.py"
    # Original content: 3 lines
    test_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    # We shift it by adding a line at the top
    test_file.write_text("new_line\nline1\nline2\nline3\n", encoding="utf-8")

    # We try to patch line 2 (line2) based on original context
    # In the current file, 'line2' is at line 3.
    applied = _apply_patch(test_file, 2, "line2", "patched_line")

    assert applied is True
    content = test_file.read_text(encoding="utf-8")
    assert "patched_line" in content
    assert "line2" not in content
    assert "new_line" in content
    assert "line1" in content
