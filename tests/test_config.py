"""Tests for the configuraton system."""

from pathlib import Path

from lintaider.config import Config


def test_config_default() -> None:
    """Test default config initialization."""
    config = Config()
    assert config.provider == "ollama"
    assert config.model == "llama3"
    assert config.api_base is None


def test_config_save_load(tmp_path) -> None:
    """Test saving and loading configuration from TOML."""
    config_file = tmp_path / "lintaider.toml"
    config = Config(
        provider="openai", model="gpt-4", api_base="https://api.openai.com/v1"
    )
    config.save(config_file)

    assert config_file.exists()
    content = config_file.read_text(encoding="utf-8")
    assert "[ai]" in content
    assert 'provider = "openai"' in content

    loaded = Config.load(config_file)
    assert loaded.provider == "openai"
    assert loaded.model == "gpt-4"
    assert loaded.api_base == "https://api.openai.com/v1"


def test_config_load_non_existent() -> None:
    """Test loading a non-existent config returns defaults."""
    config = Config.load(Path("non_existent.toml"))
    assert config.provider == "ollama"


def test_config_normalize_provider() -> None:
    """Test normalization converts provider to lowercase."""
    config = Config(provider="OpenAI")
    config.normalize()
    assert config.provider == "openai"


def test_config_normalize_model() -> None:
    """Test normalization trims model whitespace."""
    config = Config(model="  gpt-4o  ")
    config.normalize()
    assert config.model == "gpt-4o"


def test_config_normalize_linter_lists() -> None:
    """Test normalization of linter lists."""
    config = Config(
        skip_linters=[
            "Ruff",
            "PYLINT",
            "ruff",
        ],  # Has duplicate and mixed case
        only_linters=["BanDit", "mypy"],
    )
    config.normalize()
    assert config.skip_linters == [
        "ruff",
        "pylint",
    ]  # Deduplicated and lowercase
    assert config.only_linters == ["bandit", "mypy"]


def test_config_save_normalizes() -> None:
    """Test that save() calls normalize()."""
    config_file = Path(".test_normalize.toml")
    try:
        config = Config(provider="OpenAI", model="  GPT-4  ")
        config.save(config_file)

        content = config_file.read_text(encoding="utf-8")
        assert 'provider = "openai"' in content
        assert 'model = "GPT-4"' in content
    finally:
        if config_file.exists():
            config_file.unlink()


def test_config_load_normalizes() -> None:
    """Test that load() calls normalize() on loaded config."""
    config_file = Path(".test_load_normalize.toml")
    try:
        config_file.write_text(
            '[ai]\nprovider = "OpenAI"\nmodel = "gpt-4"\n\n[linters]\n'
            'skip_linters = ["RUFF", "pylint"]\nonly_linters = []\n',
            encoding="utf-8",
        )

        loaded = Config.load(config_file)
        assert loaded.provider == "openai"  # Should be normalized to lowercase
        assert loaded.skip_linters == [
            "ruff",
            "pylint",
        ]  # Normalized to lowercase
    finally:
        if config_file.exists():
            config_file.unlink()


def test_config_linter_list_deduplication() -> None:
    """Test that linter lists deduplicate while preserving order."""
    config = Config(skip_linters=["ruff", "pylint", "ruff", "bandit"])
    config.normalize()
    assert config.skip_linters == ["ruff", "pylint", "bandit"]


def test_config_empty_linter_lists() -> None:
    """Test handling of empty linter lists."""
    config = Config(skip_linters=[], only_linters=[])
    config.normalize()
    assert not config.skip_linters
    assert not config.only_linters


def test_config_whitespace_only_linter_entries() -> None:
    """Test that whitespace-only linter entries are removed."""
    config = Config(skip_linters=["ruff", "  ", "\t", "pylint"])
    config.normalize()
    assert config.skip_linters == ["ruff", "pylint"]
