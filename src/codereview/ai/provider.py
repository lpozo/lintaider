"""LiteLLM AI provider implementation for universal model access."""

import json

from dotenv import load_dotenv
from litellm import acompletion

from codereview.ai.base import AIFixProposal, BaseAIProvider
from codereview.linters.result import LinterResult

# Load .env file if it exists
load_dotenv()


class LiteLLMProvider(BaseAIProvider):
    """Universal AI provider using LiteLLM."""

    def __init__(self, model: str = "gpt-4o", api_base: str | None = None) -> None:
        """Initialize LiteLLM provider.

        Args:
            model: The name of the model to use.
            api_base: Optional base URL for the model API (required for local/private).
        """
        self.model = model
        self.api_base = api_base

    @property
    def name(self) -> str:
        """Return provider name."""
        return f"LiteLLM ({self.model})"

    async def generate_fixes(self, linter_result: LinterResult) -> list[AIFixProposal]:
        """Request fixes using LiteLLM asynchronously."""
        system_prompt, user_prompt = self._get_prompts(linter_result)

        try:
            # LiteLLM manages API keys from environment variables automatically
            response = await acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                api_base=self.api_base,
            )

            # Access content from the response
            content = response.choices[0].message.content or "[]"  # type: ignore

            # LiteLLM sometimes returns the string representation of JSON
            parsed = json.loads(content)

            # Expected format is a list or a dict with a list of fixes
            if isinstance(parsed, dict) and "fixes" in parsed:
                parsed = parsed["fixes"]
            elif isinstance(parsed, dict):
                # If it returned a single object, wrap it
                parsed = [parsed]

            if not isinstance(parsed, list):
                return []

            proposals = []
            for item in parsed:
                proposals.append(
                    AIFixProposal(
                        explanation=item.get("explanation", ""),
                        code_diff=item.get("code_diff", ""),
                    )
                )
            return proposals
        except Exception:  # pylint: disable=broad-exception-caught
            return []
