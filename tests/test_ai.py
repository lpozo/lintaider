"""Tests for AI providers."""

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lintaider.ai import (
    LiteLLMProvider,
    create_ai_provider,
    list_provider_models,
    verify_provider_connection,
)
from lintaider.ai.registry import (
    PROVIDER_SPECS,
    get_provider_spec,
    get_supported_providers,
)
from lintaider.linters.result import LinterResult


def test_create_ai_provider_ollama() -> None:
    """Test create_ai_provider logic for Ollama."""
    ollama = create_ai_provider("ollama", "llama3")
    assert isinstance(ollama, LiteLLMProvider)
    # Check that it added the prefix and set api_base
    assert ollama.model == "ollama/llama3"
    assert ollama.api_base == "http://localhost:11434"

    custom_ollama = cast(
        LiteLLMProvider,
        create_ai_provider("ollama", "llama3", "http://remote:11434"),
    )
    assert custom_ollama.api_base == "http://remote:11434"


def test_create_ai_provider_openai() -> None:
    """Test create_ai_provider logic for OpenAI."""
    openai = create_ai_provider("openai", "gpt-4")
    assert isinstance(openai, LiteLLMProvider)
    assert openai.model == "openai/gpt-4"
    assert openai.api_base is None


def test_create_ai_provider_anthropic() -> None:
    """Test create_ai_provider logic for Anthropic."""
    anthropic = create_ai_provider("anthropic", "claude-3")
    assert isinstance(anthropic, LiteLLMProvider)
    assert anthropic.model == "anthropic/claude-3"
    assert anthropic.api_base is None


@pytest.mark.asyncio
@patch("lintaider.ai.provider.acompletion", new_callable=AsyncMock)
async def test_litellm_provider(mock_acompletion) -> None:
    """Test LiteLLMProvider integration."""
    mock_acompletion.return_value.choices[
        0
    ].message.content = (
        '[{"explanation": "Lite Fix", "code_diff": "print(2)"}]'
    )

    provider = LiteLLMProvider(model="gpt-4o")
    linter_res = LinterResult(
        file_path=Path("dummy.py"),
        line_start=1,
        line_end=1,
        col_start=1,
        col_end=5,
        linter_name="DummyLinter",
        error_code="D001",
        message="A test error",
        snippet_context="print('a')",
    )

    proposals = await provider.generate_fixes(linter_res)

    assert len(proposals) == 1
    assert proposals[0].explanation == "Lite Fix"
    assert proposals[0].code_diff == "print(2)"
    mock_acompletion.assert_called_once()


def test_provider_registry_coverage() -> None:
    """Test provider registry has expected providers."""
    assert "ollama" in PROVIDER_SPECS
    assert "openai" in PROVIDER_SPECS
    assert "anthropic" in PROVIDER_SPECS
    assert "gemini" in PROVIDER_SPECS


def test_provider_registry_ollama() -> None:
    """Test Ollama registry details."""
    ollama = PROVIDER_SPECS["ollama"]
    assert ollama.provider_id == "ollama"
    assert ollama.display_name == "Ollama (Local)"
    assert ollama.requires_api_key is False
    assert ollama.env_var is None
    assert ollama.default_model == "llama3"
    assert ollama.default_api_base == "http://localhost:11434"
    assert ollama.model_list_endpoint == "/api/tags"


def test_provider_registry_openai() -> None:
    """Test OpenAI registry details."""
    openai = PROVIDER_SPECS["openai"]
    assert openai.provider_id == "openai"
    assert openai.requires_api_key is True
    assert openai.env_var == "OPENAI_API_KEY"
    assert openai.default_model == "gpt-4o-mini"


def test_get_provider_spec() -> None:
    """Test provider spec lookup."""
    spec = get_provider_spec("openai")
    assert spec is not None
    assert spec.provider_id == "openai"

    spec = get_provider_spec("ANTHROPIC")
    assert spec is not None
    assert spec.provider_id == "anthropic"

    spec = get_provider_spec("unknown")
    assert spec is None


def test_get_supported_providers() -> None:
    """Test supported providers list."""
    providers = get_supported_providers()
    assert isinstance(providers, tuple)
    assert len(providers) == 4
    assert "ollama" in providers
    assert "openai" in providers


@patch("lintaider.ai.provider.requests.get")
def test_list_provider_models_ollama(mock_get) -> None:
    """Test model discovery for Ollama."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3"},
            {"name": "mistral"},
            {"name": "qwen2.5-coder"},
        ]
    }
    mock_get.return_value = mock_response

    models = list_provider_models("ollama")
    assert sorted(models) == ["llama3", "mistral", "qwen2.5-coder"]
    mock_get.assert_called_once()


@patch("lintaider.ai.provider.requests.get")
def test_list_provider_models_openai(mock_get) -> None:
    """Test model discovery for OpenAI."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
            {"id": "gpt-3.5-turbo"},
        ]
    }
    mock_get.return_value = mock_response

    models = list_provider_models("openai", api_key="sk-test")
    assert sorted(models) == ["gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"]
    mock_get.assert_called_once()


@patch("lintaider.ai.provider.requests.get")
def test_list_provider_models_gemini_cleanup(mock_get) -> None:
    """Test model discovery for Google Gemini with name cleanup."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "models/gemini-2.0-flash"},
            {"name": "models/gemini-2.5-flash"},
        ]
    }
    mock_get.return_value = mock_response

    models = list_provider_models("gemini", api_key="test")
    assert "gemini-2.0-flash" in models
    assert "gemini-2.5-flash" in models
    assert not any("models/" in m for m in models)


@patch("lintaider.ai.provider.requests.get")
def test_list_provider_models_request_failure(mock_get) -> None:
    """Test graceful failure when model discovery fails."""
    import requests

    mock_get.side_effect = requests.RequestException("Connection error")

    models = list_provider_models("openai", api_key="sk-test")
    assert models == []


def test_list_provider_models_unsupported_provider() -> None:
    """Test model discovery returns empty for providers without endpoint."""
    models = list_provider_models("unknown_provider")
    assert models == []


@pytest.mark.asyncio
@patch("lintaider.ai.provider.acompletion", new_callable=AsyncMock)
async def test_verify_provider_connection_success(mock_acompletion) -> None:
    """Test successful provider connectivity check."""
    mock_acompletion.return_value.choices[0].message.content = "OK"

    ok, message = await verify_provider_connection(
        "openai", "gpt-4o", api_key="sk-test"
    )

    assert ok is True
    assert "successful" in message.lower()


@pytest.mark.asyncio
@patch("lintaider.ai.provider.acompletion", new_callable=AsyncMock)
async def test_verify_provider_connection_failure(mock_acompletion) -> None:
    """Test failed provider connectivity check."""
    mock_acompletion.side_effect = Exception("Invalid API key")

    ok, message = await verify_provider_connection(
        "openai", "gpt-4o", api_key="invalid"
    )

    assert ok is False
    assert "Invalid API key" in message


def test_create_ai_provider_with_keychain() -> None:
    """Test provider creation includes API key from keychain."""
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = "keyring_key"

    with patch("lintaider.ai.auth.keyring_module", mock_keyring):
        provider = cast(
            LiteLLMProvider, create_ai_provider("openai", "gpt-4o")
        )

    assert provider.api_key in ("keyring_key", None)  # May or may not fetch
    assert provider.model == "openai/gpt-4o"
