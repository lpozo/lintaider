"""Tests for AI authentication and secret management."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codereview.ai.auth import (
    KEYRING_SERVICE_NAME,
    get_api_key_for_provider,
    get_env_var_for_provider,
    save_api_key,
    save_provider_api_key,
)


def test_get_env_var_for_provider() -> None:
    """Test env var lookup for known providers."""
    assert get_env_var_for_provider("openai") == "OPENAI_API_KEY"
    assert get_env_var_for_provider("anthropic") == "ANTHROPIC_API_KEY"
    assert get_env_var_for_provider("gemini") == "GEMINI_API_KEY"
    assert get_env_var_for_provider("ollama") is None
    assert get_env_var_for_provider("unknown_provider") is None


def test_get_env_var_for_provider_case_insensitive() -> None:
    """Test provider lookup is case-insensitive."""
    assert get_env_var_for_provider("OpenAI") == "OPENAI_API_KEY"
    assert get_env_var_for_provider("ANTHROPIC") == "ANTHROPIC_API_KEY"


def test_save_api_key_new_file(tmp_path) -> None:
    """Test saving API key to a new .env file."""
    env_file = tmp_path / ".env"
    with patch("codereview.ai.auth.Path", return_value=env_file):
        save_api_key("TEST_KEY", "secret123")

    content = env_file.read_text(encoding="utf-8")
    assert 'TEST_KEY="secret123"' in content
    assert content.endswith("\n")


def test_save_api_key_existing_file(tmp_path) -> None:
    """Test saving API key to existing .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text('OTHER_KEY="value"\n', encoding="utf-8")

    with patch("codereview.ai.auth.Path", return_value=env_file):
        save_api_key("TEST_KEY", "secret123")

    content = env_file.read_text(encoding="utf-8")
    assert 'OTHER_KEY="value"' in content
    assert 'TEST_KEY="secret123"' in content


def test_save_api_key_replace_existing(tmp_path) -> None:
    """Test replacing an existing API key in .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text('TEST_KEY="old_secret"\n', encoding="utf-8")

    with patch("codereview.ai.auth.Path", return_value=env_file):
        save_api_key("TEST_KEY", "new_secret")

    content = env_file.read_text(encoding="utf-8")
    assert 'TEST_KEY="new_secret"' in content
    assert "old_secret" not in content


def test_get_api_key_for_provider_from_env(monkeypatch) -> None:
    """Test retrieving API key from environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "env_secret")
    with patch("codereview.ai.auth.load_dotenv"):
        key = get_api_key_for_provider("openai")

    assert key == "env_secret"


def test_get_api_key_for_provider_no_env_no_keyring() -> None:
    """Test retrieval returns None when no env var and keyring unavailable."""
    with (
        patch("codereview.ai.auth.load_dotenv"),
        patch("codereview.ai.auth.keyring", None),
        patch.dict(os.environ, {}, clear=True),
    ):
        key = get_api_key_for_provider("openai")

    assert key is None


def test_get_api_key_for_provider_from_keyring() -> None:
    """Test retrieving API key from keyring when env var not set."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = "keyring_secret"

    with (
        patch("codereview.ai.auth.load_dotenv"),
        patch("codereview.ai.auth.keyring", mock_keyring),
        patch.dict(os.environ, {}, clear=True),
    ):
        key = get_api_key_for_provider("openai")

    assert key == "keyring_secret"
    mock_keyring.get_password.assert_called_once_with(
        KEYRING_SERVICE_NAME, "OPENAI_API_KEY"
    )


def test_get_api_key_for_provider_env_precedence(monkeypatch) -> None:
    """Test environment variable takes precedence over keyring."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = "keyring_secret"
    monkeypatch.setenv("OPENAI_API_KEY", "env_secret")

    with (
        patch("codereview.ai.auth.load_dotenv"),
        patch("codereview.ai.auth.keyring", mock_keyring),
    ):
        key = get_api_key_for_provider("openai")

    assert key == "env_secret"
    mock_keyring.get_password.assert_not_called()


def test_get_api_key_for_provider_keyring_exception() -> None:
    """Test graceful handling when keyring fails."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = Exception("Keyring error")

    with (
        patch("codereview.ai.auth.load_dotenv"),
        patch("codereview.ai.auth.keyring", mock_keyring),
        patch.dict(os.environ, {}, clear=True),
    ):
        key = get_api_key_for_provider("openai")

    assert key is None


def test_save_provider_api_key_to_keyring() -> None:
    """Test saving provider API key to keyring."""
    mock_keyring = MagicMock()

    with patch("codereview.ai.auth.keyring", mock_keyring):
        backend = save_provider_api_key("openai", "secret123")

    assert backend == "keychain"
    mock_keyring.set_password.assert_called_once_with(
        KEYRING_SERVICE_NAME, "OPENAI_API_KEY", "secret123"
    )


def test_save_provider_api_key_fallback_to_env(tmp_path) -> None:
    """Test falling back to .env when keyring is unavailable."""
    env_file = tmp_path / ".env"
    mock_keyring = MagicMock()
    mock_keyring.set_password.side_effect = Exception("Keyring not available")

    with (
        patch("codereview.ai.auth.keyring", mock_keyring),
        patch("codereview.ai.auth.Path", return_value=env_file),
    ):
        backend = save_provider_api_key("openai", "secret123")

    assert backend == ".env"
    assert 'OPENAI_API_KEY="secret123"' in env_file.read_text(encoding="utf-8")


def test_save_provider_api_key_no_env_var() -> None:
    """Test save returns 'none' for providers without env var (e.g., ollama)."""
    backend = save_provider_api_key("ollama", "ignored")
    assert backend == "none"


def test_get_api_key_for_provider_no_provider_spec() -> None:
    """Test retrieval with provider not in registry falls back to old map."""
    with (
        patch("codereview.ai.auth.load_dotenv"),
        patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}),
    ):
        key = get_api_key_for_provider("openai")

    assert key == "test_key"
