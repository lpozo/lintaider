"""Tests for the configuraton system."""

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


def test_config_load_non_existent(tmp_path) -> None:
    """Test loading a non-existent config returns defaults."""
    config = Config.load(tmp_path / "non_existent.toml")
    assert config.provider == "ollama"


def test_config_normalize_provider(tmp_path) -> None:
    """Test normalization occurs during save/load."""
    config_file = tmp_path / "test.toml"
    Config(provider="OpenAI").save(config_file)
    loaded = Config.load(config_file)
    assert loaded.provider == "openai"


def test_config_normalize_model(tmp_path) -> None:
    """Test model normalization via save/load."""
    config_file = tmp_path / "test.toml"
    Config(model="  gpt-4o  ").save(config_file)
    loaded = Config.load(config_file)
    assert loaded.model == "gpt-4o"


def test_config_normalize_linter_lists(tmp_path) -> None:
    """Test normalization of linter lists via save/load."""
    config_file = tmp_path / "test.toml"
    Config(
        skip_linters=["Ruff", "PYLINT", "ruff"],
        only_linters=["BanDit", "mypy"],
    ).save(config_file)

    loaded = Config.load(config_file)
    assert loaded.skip_linters == ["ruff", "pylint"]
    assert loaded.only_linters == ["bandit", "mypy"]


def test_config_linter_list_deduplication(tmp_path) -> None:
    """Test that linter lists deduplicate via save/load."""
    config_file = tmp_path / "test.toml"
    Config(skip_linters=["ruff", "pylint", "ruff", "bandit"]).save(config_file)
    loaded = Config.load(config_file)
    assert loaded.skip_linters == ["ruff", "pylint", "bandit"]


def test_config_empty_linter_lists(tmp_path) -> None:
    """Test handling of empty linter lists via save/load."""
    config_file = tmp_path / "test.toml"
    Config(skip_linters=[], only_linters=[]).save(config_file)
    loaded = Config.load(config_file)
    assert not loaded.skip_linters
    assert not loaded.only_linters


def test_config_whitespace_only_linter_entries(tmp_path) -> None:
    """Test that whitespace-only linter entries are removed via save/load."""
    config_file = tmp_path / "test.toml"
    Config(skip_linters=["ruff", "  ", "\t", "pylint"]).save(config_file)
    loaded = Config.load(config_file)
    assert loaded.skip_linters == ["ruff", "pylint"]
