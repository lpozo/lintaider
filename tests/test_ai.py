"""Tests for AI providers."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from codereview.ai import LiteLLMProvider, create_ai_provider
from codereview.linters.result import LinterResult


def test_create_ai_provider() -> None:
    """Test create_ai_provider logic."""
    ollama = create_ai_provider("local", "llama3")
    assert isinstance(ollama, LiteLLMProvider)
    # Check that it added the prefix and set api_base
    assert ollama.model == "ollama/llama3"
    assert ollama.api_base == "http://localhost:11434"

    openai = create_ai_provider("openai", "gpt-4")
    assert isinstance(openai, LiteLLMProvider)
    assert openai.model == "openai/gpt-4"
    assert openai.api_base is None

    cloud = create_ai_provider("cloud", "anthropic/claude-3")
    assert isinstance(cloud, LiteLLMProvider)
    assert cloud.model == "anthropic/claude-3"


@pytest.mark.asyncio
@patch("codereview.ai.provider.acompletion", new_callable=AsyncMock)
async def test_litellm_provider(mock_acompletion) -> None:
    """Test LiteLLMProvider integration."""
    mock_acompletion.return_value.choices[
        0
    ].message.content = '[{"explanation": "Lite Fix", "code_diff": "print(2)"}]'

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
