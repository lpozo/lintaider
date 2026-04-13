"""Base classes and interfaces for AI providers."""

import abc
from dataclasses import dataclass
from pathlib import Path

from lintaider.linters.context import ProjectSummary, SymbolInfo
from lintaider.linters.result import LinterResult


@dataclass  # pylint: disable=too-few-public-methods
class AIFixProposal:
    """A proposed fix from the AI.

    Attributes:
        explanation: A human-readable explanation of why this fix is recommended.
        code_diff: A unified-style diff representing the proposed changes.
    """

    explanation: str
    code_diff: str


# pylint: disable=too-few-public-methods
class BaseAIProvider(abc.ABC):
    """Abstract base class for AI providers."""

    name: str

    @abc.abstractmethod
    async def generate_fixes(
        self,
        linter_result: LinterResult,
        project_summary: ProjectSummary | None = None,
    ) -> list[AIFixProposal]:
        """Generate at least 2 alternative fixes for a linter error.

        Args:
            linter_result: The linter error/warning to fix.
            project_summary: Optional summary of the target project for context.

        Returns:
            A list of AI-generated fix proposals.
        """

    def _get_prompts(
        self,
        result: LinterResult,
        project_summary: ProjectSummary | None = None,
    ) -> tuple[str, str]:
        """Construct the system and user prompts for the AI.

        Args:
            result: The linter result to fix.
            project_summary: Optional project summary for additional context.

        Returns:
            A tuple containing (system_prompt, user_prompt).
        """
        # Use absolute path relative to this file's parent (ai/)
        prompts_dir = Path(__file__).parent / "prompts"
        system_prompt = (prompts_dir / "system.txt").read_text(
            encoding="utf-8"
        )
        user_template = (prompts_dir / "user.txt").read_text(encoding="utf-8")

        # Format project context
        project_context = ""
        target_config = ""
        linter_advice = ""

        if project_summary:
            # Compact file tree
            files = "\n".join(f"- {f}" for f in project_summary.file_tree[:20])
            # Filter symbols for current file or relevant names
            symbols = self._format_relevant_symbols(
                result, project_summary.public_symbols
            )
            project_context = (
                f"Project Structure:\n{files}\n\nRelevant Symbols:\n{symbols}"
            )

            if project_summary.target_config:
                target_config = (
                    f"Project Linter Config:\n{project_summary.target_config}"
                )

        # Add general linter advice
        if result.linter_name.lower() == "vulture":
            linter_advice = (
                "Note: Vulture detects unused code. Be cautious of false positives "
                "if this code is called dynamically or via frameworks."
            )
        elif result.linter_name.lower() == "pylint":
            linter_advice = (
                "Note: Pylint checks for code smells and PEP8 violations."
            )

        user_prompt = user_template.format(
            file_path=result.file_path,
            linter_name=result.linter_name,
            error_code=result.error_code,
            message=result.message,
            snippet_context=result.snippet_context,
            semantic_context=result.semantic_context,
            project_context=project_context,
            target_config=target_config,
            linter_advice=linter_advice,
        )
        return system_prompt, user_prompt

    def _format_relevant_symbols(
        self, result: LinterResult, symbols: list[SymbolInfo]
    ) -> str:
        """Format symbols that are relevant to the current file or error.

        Args:
            result: The linter result being addressed.
            symbols: A list of all discovered public symbols in the project.

        Returns:
            A formatted string listing the most relevant symbols.
        """
        relevant = []
        for sym in symbols:
            # If it's in the same file or mentioned in the message/semantic context
            if (
                str(sym.file_path) in str(result.file_path)
                or sym.name in result.message
                or (
                    result.semantic_context
                    and sym.name in result.semantic_context
                )
            ):
                relevant.append(
                    f"- {sym.name} ({sym.kind}) in {sym.file_path}"
                )

        # Limit to top 15 relevant symbols
        if not relevant:
            relevant = [f"- {s.name} ({s.kind})" for s in symbols[:10]]

        return "\n".join(relevant[:15])
