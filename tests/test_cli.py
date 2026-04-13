"""Tests for the LintAIderer CLI interface."""

from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from lintaider.ai import AIFixProposal
from lintaider.cli import main
from lintaider.config import Config
from lintaider.linters.result import LinterResult


@pytest.fixture
def mock_config(mocker):
    """Fixture to mock Config.load with defaults."""
    return mocker.patch(
        "lintaider.cli.init_handler.Config.load", return_value=Config()
    )


def test_cli_scan_no_issues(mocker, tmp_path, mock_config) -> None:
    """Test scanning a file with no issues."""
    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("def ok():\n    return 1\n", encoding="utf-8")

    mocker.patch(
        "lintaider.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[],
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
        "lintaider.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    output_file = tmp_path / "scan-result.json"
    result = runner.invoke(
        main, ["scan", str(test_file), "--output", str(output_file)]
    )

    assert result.exit_code == 0
    assert "Findings Summary" in result.output
    assert "Results saved to" in result.output
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["linter_name"] == "TestLinter"
    assert data[0]["error_code"] == "E1"


def test_cli_scan_human_readable_generates_markdown(
    mocker, tmp_path, mock_config
) -> None:
    """Test that --human-readable generates linting-report.md and JSON output."""
    import json
    from pathlib import Path

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
        "lintaider.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    output_file = tmp_path / "scan-result.json"
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            main,
            [
                "scan",
                str(test_file),
                "--output",
                str(output_file),
                "--human-readable",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["linter_name"] == "TestLinter"

        report_file = Path("linting-report.md")
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "# Linting Report" in content
        assert "TestLinter" in content
        assert "A test error" in content


def test_cli_scan_human_readable_short_flag(
    mocker, tmp_path, mock_config
) -> None:
    """Test that -r also generates linting-report.md."""
    from pathlib import Path

    runner = CliRunner()
    test_file = tmp_path / "valid.py"
    test_file.write_text("def ok():\n    return 1\n", encoding="utf-8")

    mocker.patch(
        "lintaider.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[],
    )

    output_file = tmp_path / "scan-result.json"
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            main, ["scan", str(test_file), "--output", str(output_file), "-r"]
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert Path("linting-report.md").exists()


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
    input_file.write_text(
        json.dumps([fake_result.to_dict()]), encoding="utf-8"
    )

    proposal = AIFixProposal(explanation="Fix", code_diff="import good")
    mocker.patch(
        "lintaider.cli.fix_handler.create_ai_provider",
    ).return_value.generate_fixes = AsyncMock(return_value=[proposal])

    result = runner.invoke(
        main, ["fix", "--input", str(input_file)], input="s\n"
    )

    assert result.exit_code == 0
    assert "Option 1" in result.output
    assert "Fix" in result.output
    assert "Skipping" in result.output


def test_cli_scan_verbose(mocker, tmp_path, mock_config) -> None:
    """Test that --verbose prints per-issue panels."""

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
        "lintaider.cli.scan_handler.Engine.run_all",
        new_callable=AsyncMock,
        return_value=[fake_result],
    )

    output_file = tmp_path / "scan-result.json"
    result = runner.invoke(
        main,
        ["scan", str(test_file), "--output", str(output_file), "--verbose"],
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

    mock_engine = mocker.patch("lintaider.cli.scan_handler.Engine")

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

    mock_engine = mocker.patch("lintaider.cli.scan_handler.Engine")

    runner.invoke(
        main,
        [
            "scan",
            str(test_file),
            "--skip",
            "ruff,pylint,bandit,mypy,pyright,semgrep",
        ],
    )

    args, kwargs = mock_engine.call_args
    linters = kwargs.get("linters", []) or (args[0] if args else [])
    # Vulture, Radon, and Safety should remain
    assert len(linters) == 3
    remaining_names = [linter.__class__.__name__ for linter in linters]
    assert "VultureLinter" in remaining_names
    assert "RadonLinter" in remaining_names
    assert "SafetyLinter" in remaining_names


def test_cli_init_command(mocker, tmp_path) -> None:
    """Test the redesigned init command flow."""
    runner = CliRunner()
    _ = tmp_path / "lintaider.toml"

    config = Config()
    mocker.patch("lintaider.cli.init_handler.Config.load", return_value=config)
    mocker.patch(
        "lintaider.cli.init_handler.list_provider_models", return_value=[]
    )
    mocker.patch(
        "lintaider.cli.init_handler.save_provider_api_key",
        return_value="keychain",
    )
    mock_save = mocker.patch.object(Config, "save")

    # Inputs: provider #2=openai, API key blank, API base blank, model #1,
    # skip blank, only blank, verify now? no, save? yes
    result = runner.invoke(main, ["init"], input="2\n\n\n1\n\n\nn\ny\n")

    assert result.exit_code == 0
    assert "Configuration Saved" in result.output
    assert config.provider == "openai"
    assert config.model
    mock_save.assert_called_once()


def test_cli_apply_patch_fuzzy(tmp_path) -> None:
    """Test that _apply_patch works even if lines have shifted."""
    from lintaider.cli.fix_handler import _apply_patch

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


def test_init_helper_parse_linter_list() -> None:
    """Test linter list parsing helper."""
    from lintaider.cli.init_handler import _parse_linter_list

    # Normal case
    result = _parse_linter_list("ruff, pylint, bandit")
    assert result == ["ruff", "pylint", "bandit"]

    # Duplicates
    result = _parse_linter_list("ruff, pylint, ruff")
    assert result == ["ruff", "pylint"]

    # Mixed case
    result = _parse_linter_list("Ruff, PYLINT")
    assert result == ["ruff", "pylint"]

    # Empty
    result = _parse_linter_list("")
    assert not result

    # Whitespace only
    result = _parse_linter_list("  ,  ,  ")
    assert not result


def test_init_helper_select_linter_preferences(mocker) -> None:
    """Test linter preference selection with validation."""
    from lintaider.cli.init_handler import _select_linter_preferences

    config = Config(skip_linters=["ruff"], only_linters=[])

    mocker.patch(
        "lintaider.cli.init_handler.click.prompt",
        side_effect=["ruff,pylint", ""],  # skip, only
    )

    skip, only = _select_linter_preferences(config)
    assert "ruff" in skip
    assert "pylint" in skip


def test_init_helper_select_linter_preferences_invalid(mocker) -> None:
    """Test that invalid linter names are handled gracefully."""
    from lintaider.cli.init_handler import _select_linter_preferences

    config = Config()

    mocker.patch(
        "lintaider.cli.init_handler.click.prompt",
        side_effect=["ruff,invalid_linter", ""],
    )

    skip, only = _select_linter_preferences(config)
    assert "ruff" in skip
    assert "invalid_linter" not in skip


def test_init_helper_select_linter_preferences_overlap(mocker) -> None:
    """Test overlap removal between skip and only linters."""
    from lintaider.cli.init_handler import _select_linter_preferences

    config = Config()

    mocker.patch(
        "lintaider.cli.init_handler.click.prompt",
        side_effect=["ruff,pylint", "pylint,bandit"],  # pylint is in both
    )

    skip, only = _select_linter_preferences(config)
    assert "pylint" not in skip  # Should be removed from skip
    assert "pylint" in only
    assert "bandit" in only


def test_init_helper_run_connectivity_check(mocker) -> None:
    """Test connectivity check during init."""
    from lintaider.cli.init_handler import _run_connectivity_check

    mocker.patch(
        "lintaider.cli.init_handler.verify_provider_connection",
        return_value=(True, "Connection successful"),
        new_callable=AsyncMock,
    )

    ok = _run_connectivity_check("openai", "gpt-4o", None, "test_key")
    assert ok is True


def test_init_helper_run_connectivity_check_failure(mocker) -> None:
    """Test connectivity check failure handling."""
    from lintaider.cli.init_handler import _run_connectivity_check

    mocker.patch(
        "lintaider.cli.init_handler.verify_provider_connection",
        return_value=(False, "Invalid API key"),
        new_callable=AsyncMock,
    )

    ok = _run_connectivity_check("openai", "gpt-4o", None, "invalid")
    assert ok is False


def test_init_helper_select_api_base(mocker) -> None:
    """Test API base selection with provider defaults."""
    from lintaider.cli.init_handler import _select_api_base

    mocker.patch("lintaider.cli.init_handler.click.prompt", return_value="")

    result = _select_api_base("ollama", None)
    assert result is None  # Empty input -> None


def test_init_helper_select_api_base_custom(mocker) -> None:
    """Test custom API base override."""
    from lintaider.cli.init_handler import _select_api_base

    mocker.patch(
        "lintaider.cli.init_handler.click.prompt",
        return_value="http://custom:8080",
    )

    result = _select_api_base("ollama", None)
    assert result == "http://custom:8080"


def test_init_helper_update_provider_api_key_local(mocker) -> None:
    """Test that local providers skip API key prompt."""
    from lintaider.cli.init_handler import _update_provider_api_key

    result = _update_provider_api_key("ollama")
    assert result is None  # Ollama needs no API key


def test_init_helper_update_provider_api_key_cloud(mocker) -> None:
    """Test API key capture for cloud providers."""
    from lintaider.cli.init_handler import _update_provider_api_key

    mocker.patch(
        "lintaider.cli.init_handler.get_api_key_for_provider",
        return_value=None,
    )
    mocker.patch(
        "lintaider.cli.init_handler.click.prompt", return_value="sk-test123"
    )
    mocker.patch(
        "lintaider.cli.init_handler.save_provider_api_key",
        return_value="keychain",
    )

    result = _update_provider_api_key("openai")
    assert result == "sk-test123"


def test_init_helper_update_provider_api_key_keep_existing(mocker) -> None:
    """Test keeping existing API key when new one is not provided."""
    from lintaider.cli.init_handler import _update_provider_api_key

    mocker.patch(
        "lintaider.cli.init_handler.get_api_key_for_provider",
        return_value="existing_key",
    )
    mocker.patch("lintaider.cli.init_handler.click.prompt", return_value="")

    result = _update_provider_api_key("openai")
    assert result == "existing_key"


def test_init_helper_select_model_with_discovery(mocker) -> None:
    """Test model selection with successful discovery."""
    from lintaider.cli.init_handler import _select_model

    mocker.patch(
        "lintaider.cli.init_handler.list_provider_models",
        return_value=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    )
    mocker.patch("lintaider.cli.init_handler.click.prompt", return_value="1")

    result = _select_model("openai", "gpt-4o", None, "test_key")
    assert result == "gpt-4o"


def test_init_helper_select_model_discovery_failed(mocker) -> None:
    """Test model selection falls back to recommended when discovery fails."""
    from lintaider.cli.init_handler import _select_model

    mocker.patch(
        "lintaider.cli.init_handler.list_provider_models",
        return_value=[],  # Discovery failed
    )
    mocker.patch("lintaider.cli.init_handler.click.prompt", return_value="1")

    result = _select_model("openai", "", None, None)
    # Should use recommended models from provider spec
    assert isinstance(result, str)


def test_init_helper_select_provider(mocker) -> None:
    """Test provider selection menu."""
    from lintaider.cli.init_handler import _select_provider

    mocker.patch("lintaider.cli.init_handler.click.prompt", return_value="1")

    result = _select_provider("ollama")
    assert result == "ollama"  # First provider in PROVIDER_SPECS


def test_init_helper_select_provider_by_name(mocker) -> None:
    """Test provider selection by entering provider name."""
    from lintaider.cli.init_handler import _select_provider

    mocker.patch(
        "lintaider.cli.init_handler.click.prompt", return_value="openai"
    )

    result = _select_provider("ollama")
    assert result == "openai"
