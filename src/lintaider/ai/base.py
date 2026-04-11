"""Base classes and dataclasses for AI providers."""

import abc
from dataclasses import dataclass
from pathlib import Path

from lintaider.linters.result import LinterResult


@dataclass  # pylint: disable=too-few-public-methods
class AIFixProposal:
    """A proposed fix from the AI."""

    explanation: str
    code_diff: str


# pylint: disable=too-few-public-methods
class BaseAIProvider(abc.ABC):
    """Abstract base class for AI providers."""

    name: str

    @abc.abstractmethod
    async def generate_fixes(self, linter_result: LinterResult) -> list[AIFixProposal]:
        """Generate at least 2 alternative fixes for a linter error.

        Args:
            linter_result: The linter error/warning to fix.

        Returns:
            A list of AI-generated fix proposals.
        """

    def _get_prompts(self, result: LinterResult) -> tuple[str, str]:
        """Construct the system and user prompts for the AI.

        Args:
            result: The linter result to fix.

        Returns:
            A tuple containing (system_prompt, user_prompt).
        """
        # Use absolute path relative to this file's parent (ai/)
        prompts_dir = Path(__file__).parent / "prompts"
        system_prompt = (prompts_dir / "system.txt").read_text(encoding="utf-8")
        user_template = (prompts_dir / "user.txt").read_text(encoding="utf-8")

        user_prompt = user_template.format(
            file_path=result.file_path,
            linter_name=result.linter_name,
            error_code=result.error_code,
            message=result.message,
            snippet_context=result.snippet_context,
            semantic_context=result.semantic_context,
        )
        return system_prompt, user_prompt
