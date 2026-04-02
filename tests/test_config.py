"""Tests for the configuraton system."""

from pathlib import Path

from codereview.config import Config


def test_config_default() -> None:
    """Test default config initialization."""
    config = Config()
    assert config.provider == "ollama"
    assert config.model == "llama3"
    assert config.api_base is None


def test_config_save_load(tmp_path) -> None:
    """Test saving and loading configuration from TOML."""
    config_file = tmp_path / "codereview.toml"
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
