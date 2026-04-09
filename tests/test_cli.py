"""Tests for the CodeReviewer CLI interface."""

from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from codereview.ai import AIFixProposal
from codereview.cli import main
from codereview.config import Config
from codereview.linters.result import LinterResult


@pytest.fixture
def mock_config(mocker):
    """Fixture to mock Config.load with defaults."""
    return mocker.patch("codereview.cli.init_handler.Config.load", return_value=Config())


def test_cli_scan_no_issues(mocker, tmp_path, mock_config) -> None:
    """Test scanning a file with no issues."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("def ok():\n    return 1\n", encoding="utf-8")

    mocker.patch(
        "codereview.cli.scan_handler.Engine.run_all", new_callable=AsyncMock, return_value=[]
    )

    result = runner.invoke(main, ["scan", str(test_file)])
    assert result.exit_code == 0
    assert "No issues found" in result.output


def test_cli_scan_with_issues(mocker, tmp_path, mock_config) -> None:
    """Test scanning a file with issues saves results to a JSON file."""
    import json

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

    mocker.patch(
        "codereview.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    output_file = tmp_path / "scan-result.json"
    result = runner.invoke(main, ["scan", str(test_file), "--output", str(output_file)])

    assert result.exit_code == 0
    assert "Findings Summary" in result.output
    assert "Results saved to" in result.output
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["linter_name"] == "TestLinter"
    assert data[0]["error_code"] == "E1"


def test_cli_fix_with_issue_skip(mocker, tmp_path, mock_config) -> None:
    """Test fix command loads scan results, presents AI proposal, and skips."""
    import json

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

    input_file = tmp_path / "scan-result.json"
    input_file.write_text(json.dumps([fake_result.to_dict()]), encoding="utf-8")

    proposal = AIFixProposal(explanation="Fix", code_diff="import good")
    mocker.patch(
        "codereview.cli.fix_handler.create_ai_provider",
    ).return_value.generate_fixes = AsyncMock(return_value=[proposal])

    result = runner.invoke(main, ["fix", "--input", str(input_file)], input="s\n")

    assert result.exit_code == 0
    assert "Option 1: Fix" in result.output
    assert "Skipping" in result.output


def test_cli_scan_verbose(mocker, tmp_path, mock_config) -> None:
    """Test that --verbose prints per-issue panels."""
    import json

    runner = CliRunner()
    test_file = tmp_path / "error.py"
    test_file.write_text("import bad\n", encoding="utf-8")

    fake_result = LinterResult(
        file_path=test_file,
        line_start=3,
        line_end=3,
        col_start=5,
        col_end=10,
        linter_name="TestLinter",
        error_code="E1",
        message="A test error",
        snippet_context="import bad",
    )

    mocker.patch(
        "codereview.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    output_file = tmp_path / "scan-result.json"
    result = runner.invoke(
        main, ["scan", str(test_file), "--output", str(output_file), "--verbose"]
    )

    assert result.exit_code == 0
    assert "Issue 1/1" in result.output
    assert "E1" in result.output
    assert "A test error" in result.output
    assert "import bad" in result.output


def test_cli_scan_only_filter(mocker, tmp_path, mock_config) -> None:
    """Test the --only flag for filtering linters."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("print(1)\n", encoding="utf-8")

    mock_engine = mocker.patch("codereview.cli.scan_handler.Engine")

    runner.invoke(main, ["scan", str(test_file), "--only", "ruff"])

    # Engine should be instantiated with only RuffLinter
    args, kwargs = mock_engine.call_args
    linters = kwargs.get("linters", []) or (args[0] if args else [])
    assert len(linters) == 1
    assert linters[0].__class__.__name__ == "RuffLinter"


def test_cli_scan_skip_filter(mocker, tmp_path, mock_config) -> None:
    """Test the --skip flag for filtering linters."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("print(1)\n", encoding="utf-8")

    mock_engine = mocker.patch("codereview.cli.scan_handler.Engine")

    runner.invoke(
        main,
        ["scan", str(test_file), "--skip", "ruff,pylint,bandit,mypy,pyright,semgrep"],
    )

    args, kwargs = mock_engine.call_args
    linters = kwargs.get("linters", []) or (args[0] if args else [])
    # Vulture, Radon, and Safety should remain
    assert len(linters) == 3
    remaining_names = [l.__class__.__name__ for l in linters]
    assert "VultureLinter" in remaining_names
    assert "RadonLinter" in remaining_names
    assert "SafetyLinter" in remaining_names


def test_cli_init_command(mocker, tmp_path) -> None:
    """Test the init command flow."""
    runner = CliRunner()
    config_file = tmp_path / "codereview.toml"

    # Create a real config object and mock load to return it
    config = Config()
    mocker.patch("codereview.cli.init_handler.Config.load", return_value=config)
    mock_save = mocker.patch.object(Config, "save")

    # Inputs: Provider, Model, API Base (empty), API Key (empty), Skip (empty), Only (empty)
    result = runner.invoke(main, ["init"], input="openai\ngpt-4\n\n\n\n\n")

    assert result.exit_code == 0
    assert "Configuration Saved" in result.output
    assert config.provider == "openai"
    assert config.model == "gpt-4"
    mock_save.assert_called_once()


def test_cli_apply_patch_fuzzy(tmp_path) -> None:
    """Test that _apply_patch works even if lines have shifted."""
    from codereview.cli.fix_handler import _apply_patch

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
