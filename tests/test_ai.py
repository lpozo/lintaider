"""Tests for AI providers."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from codereview.ai import AIFactory, LiteLLMProvider
from codereview.linters.result import LinterResult


def test_ai_factory() -> None:
    """Test AIFactory creation logic."""
    ollama = AIFactory.create("local", "llama3")
    assert isinstance(ollama, LiteLLMProvider)
    # Check that it added the prefix and set api_base
    assert ollama.model == "ollama/llama3"
    assert ollama.api_base == "http://localhost:11434"

    litellm = AIFactory.create("cloud", "gpt-4")
    assert isinstance(litellm, LiteLLMProvider)
    assert litellm.model == "gpt-4"
    assert litellm.api_base is None


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
