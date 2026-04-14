"""Handler for the 'init' command."""

import asyncio

import click
from rich.panel import Panel
from rich.table import Table

from lintaider.ai.auth import (
    get_api_key_for_provider,
    get_env_var_for_provider,
    save_provider_api_key,
)
from lintaider.ai.provider import (
    list_provider_models,
    verify_provider_connection,
)
from lintaider.ai.registry import PROVIDER_SPECS, get_provider_spec
from lintaider.cli.ui import console
from lintaider.config import Config
from lintaider.linters import LINTER_MAP


class ConfigBuilder:
    """Interactive builder for configuration via CLI prompts."""

    def __init__(self, config: Config) -> None:
        """Initialize builder with a Config object.

        Args:
            config: The base configuration to build upon.
        """
        self.config = config
        self.provider: str | None = None
        self.model: str | None = None
        self.api_base: str | None = None
        self.api_key: str | None = None

    def select_provider(self) -> str:
        """Prompt for provider selection and store it.

        Returns:
            The selected provider ID.
        """
        self.provider = self._prompt_provider()
        return self.provider

    def update_provider_api_key(self) -> str | None:
        """Prompt for API key and store it.

        Returns:
            The API key entered or retrieved, or None if not applicable.
        """
        self.api_key = self._prompt_api_key()
        return self.api_key

    def select_api_base(self) -> str | None:
        """Prompt for API base URL and store it.

        Returns:
            The API base URL or None.
        """
        self.api_base = self._prompt_api_base()
        return self.api_base

    def select_model(self) -> str:
        """Prompt for model selection and store it.

        Returns:
            The selected model name.
        """
        self.model = self._prompt_model()
        return self.model

    def select_linter_preferences(self) -> tuple[list[str], list[str]]:
        """Prompt for linter preferences and store them.

        Returns:
            A tuple of (skip_linters, only_linters).
        """
        skip, only = self._prompt_linter_preferences()
        self.config.skip_linters = skip
        self.config.only_linters = only
        return skip, only

    def verify_connection(self) -> bool:
        """Run connectivity check for current configuration.

        Returns:
            True if verification passed, False otherwise.
        """
        if self.provider is None or self.model is None:
            raise ValueError("Provider and model must be selected first")
        return self._run_connectivity_check()

    def print_summary(self, verification_ok: bool) -> None:
        """Display configuration summary before saving.

        Args:
            verification_ok: Whether connectivity check passed.
        """
        if self.provider is None:
            raise ValueError("Provider must be set before printing summary")
        if self.model is None:
            raise ValueError("Model must be set before printing summary")
        self.config.provider = self.provider
        self.config.model = self.model
        self.config.api_base = self.api_base
        self._display_summary(verification_ok)

    def build(self) -> Config:
        """Return the built configuration.

        Returns:
            The populated Config object.
        """
        if self.provider is None:
            raise ValueError("Provider must be set before building config")
        if self.model is None:
            raise ValueError("Model must be set before building config")
        self.config.provider = self.provider
        self.config.model = self.model
        self.config.api_base = self.api_base
        return self.config

    # Private methods - these contain the logic from the old module functions

    def _prompt_provider(self) -> str:
        """Prompt user for provider selection."""
        providers = list(PROVIDER_SPECS.values())
        default_index = 1
        for idx, spec in enumerate(providers, start=1):
            if spec.provider_id == self.config.provider:
                default_index = idx
                break

        table = Table(title="Available AI Providers", show_header=True)
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Provider", style="bold")
        table.add_column("Default Model", style="magenta")
        for idx, spec in enumerate(providers, start=1):
            table.add_row(str(idx), spec.display_name, spec.default_model)
        console.print(table)

        while True:
            raw_choice: str = click.prompt(
                "Select provider number",
                default=str(default_index),
                show_default=True,
            ).strip()

            if raw_choice.isdigit():
                choice_idx = int(raw_choice) - 1
                if 0 <= choice_idx < len(providers):
                    return providers[choice_idx].provider_id

            provider = raw_choice.lower()
            if provider in PROVIDER_SPECS:
                return provider

            console.print(
                "[yellow]Invalid provider. "
                "Select a number from the list.[/yellow]"
            )

    def _prompt_api_key(self) -> str | None:
        """Prompt for and store API key when required."""
        if self.provider is None:
            raise ValueError(
                "Provider must be selected before prompting for API key"
            )
        provider_spec = get_provider_spec(self.provider)
        if not provider_spec or not provider_spec.requires_api_key:
            return None

        env_var = get_env_var_for_provider(self.provider) or "API_KEY"
        existing_key = get_api_key_for_provider(self.provider)
        prompt = (
            f"Enter {env_var} (leave empty to keep existing)"
            if existing_key
            else f"Enter {env_var}"
        )
        api_key: str = click.prompt(
            prompt, default="", hide_input=True
        ).strip()

        if not api_key:
            if existing_key:
                console.print("[dim]Keeping existing API key.[/dim]")
                return existing_key
            console.print(
                "[yellow]No API key provided. Verification may fail.[/yellow]"
            )
            return None

        backend = save_provider_api_key(self.provider, api_key)
        if backend == "keychain":
            console.print("[green]Saved API key to OS keychain.[/green]")
        elif backend == ".env":
            console.print(
                "[green]Saved API key to .env (keychain unavailable).[/green]"
            )

        return api_key

    def _prompt_api_base(self) -> str | None:
        """Prompt for API base URL override."""
        if self.provider is None:
            raise ValueError(
                "Provider must be selected before prompting for API base"
            )
        provider_spec = get_provider_spec(self.provider)
        default_api_base = self.config.api_base
        if not default_api_base and provider_spec:
            default_api_base = provider_spec.default_api_base

        api_base_input: str = click.prompt(
            "API base URL override (leave empty for provider default)",
            default=default_api_base or "",
            show_default=bool(default_api_base),
        ).strip()
        return api_base_input or None

    def _build_model_candidates(self) -> tuple[list[str], str]:
        """Build list of model choices for selection menu."""
        if self.provider is None:
            raise ValueError(
                "Provider must be selected before building models"
            )
        provider_spec = get_provider_spec(self.provider)
        default_model = self.config.model or (
            provider_spec.default_model if provider_spec else ""
        )

        console.print("[dim]Fetching available models...[/dim]")
        discovered_models = list_provider_models(
            self.provider, api_base=self.api_base, api_key=self.api_key
        )

        candidates: list[str] = []
        if discovered_models:
            candidates.extend(discovered_models)
        elif provider_spec and provider_spec.recommended_models:
            candidates.extend(provider_spec.recommended_models)
            console.print(
                "[yellow]Could not fetch models. "
                "Showing recommended options.[/yellow]"
            )

        if default_model and default_model not in candidates:
            candidates.insert(0, default_model)

        return candidates, default_model

    def _prompt_model(self) -> str:
        """Prompt user for model selection."""
        model_candidates, default_model = self._build_model_candidates()

        if not model_candidates:
            model: str = click.prompt(
                "Model name", default=default_model or "llama3"
            )
            return model.strip()

        table = Table(title="Available Models", show_header=True)
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Model", style="bold")
        for idx, model_name in enumerate(model_candidates, start=1):
            table.add_row(str(idx), model_name)
        console.print(table)

        default_index = 1
        if default_model and default_model in model_candidates:
            default_index = model_candidates.index(default_model) + 1

        choice: str = click.prompt(
            "Select model number or type a custom model",
            default=str(default_index),
            show_default=True,
        ).strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(model_candidates):
                return model_candidates[idx]
        if choice:
            return choice
        return default_model or "llama3"

    def _parse_linter_list(self, raw: str) -> list[str]:
        """Normalise a comma-separated string into a deduplicated list."""
        if not raw:
            return []
        normalized = [
            item.strip().lower() for item in raw.split(",") if item.strip()
        ]
        return list(dict.fromkeys(normalized))

    def _validate_and_filter_linters(
        self, linter_list: list[str], list_name: str
    ) -> list[str]:
        """Remove unrecognised linter names and warn the user."""
        invalid = [name for name in linter_list if name not in LINTER_MAP]
        if invalid:
            console.print(
                f"[yellow]Ignoring unknown {list_name} linters:[/yellow] "
                + ", ".join(sorted(invalid))
            )
            return [name for name in linter_list if name in LINTER_MAP]
        return linter_list

    def _prompt_linter_preferences(self) -> tuple[list[str], list[str]]:
        """Prompt for linter preferences."""
        available_linters = sorted(LINTER_MAP.keys())
        console.print(
            f"[dim]Available linters: {', '.join(available_linters)}[/dim]"
        )

        skipped_str = click.prompt(
            "Linters to skip by default (comma-separated)",
            default=",".join(self.config.skip_linters),
            show_default=True,
        )
        only_str = click.prompt(
            "Linters to exclusively run by default (comma-separated)",
            default=",".join(self.config.only_linters),
            show_default=True,
        )

        skip_linters = self._parse_linter_list(skipped_str)
        only_linters = self._parse_linter_list(only_str)

        skip_linters = self._validate_and_filter_linters(skip_linters, "skip")
        only_linters = self._validate_and_filter_linters(only_linters, "only")

        overlap = sorted(set(skip_linters).intersection(only_linters))
        if overlap:
            console.print(
                "[yellow]Removing linters present in both "
                "skip and only:[/yellow] " + ", ".join(overlap)
            )
            skip_linters = [
                name for name in skip_linters if name not in overlap
            ]

        return skip_linters, only_linters

    def _run_connectivity_check(self) -> bool:
        """Run connectivity check for current configuration."""
        if self.provider is None or self.model is None:
            raise ValueError(
                "Provider and model must be selected before connectivity check"
            )
        try:
            ok, message = asyncio.run(
                verify_provider_connection(
                    provider_name=self.provider,
                    model_name=self.model,
                    api_base=self.api_base,
                    api_key=self.api_key,
                )
            )
        except RuntimeError:
            ok, message = (
                False,
                "Connectivity check could not run in this environment.",
            )

        if ok:
            console.print("[green]Connectivity check passed.[/green]")
        else:
            console.print(
                f"[yellow]Connectivity check failed:[/yellow] {message}"
            )
        return ok

    def _display_summary(self, verification_ok: bool) -> None:
        """Display configuration summary before saving."""
        status = "Passed" if verification_ok else "Skipped/Failed"
        skip_str = (
            ", ".join(self.config.skip_linters)
            if self.config.skip_linters
            else "None"
        )
        only_str = (
            ", ".join(self.config.only_linters)
            if self.config.only_linters
            else "All"
        )
        console.print(
            Panel(
                f"Provider: [bold]{self.config.provider}[/bold]\n"
                f"Model: [bold]{self.config.model}[/bold]\n"
                f"API Base: [bold]{self.config.api_base or 'Default'}[/bold]\n"
                f"Skip Linters: [bold]{skip_str}[/bold]\n"
                f"Only Linters: [bold]{only_str}[/bold]\n"
                f"Verification: [bold]{status}[/bold]",
                title="Setup Summary",
                border_style="cyan",
            )
        )


def handle_init() -> None:
    """Execute the interactive initialization flow."""
    config = Config.load()
    builder = ConfigBuilder(config)

    console.print("[bold]LintAIder Setup Wizard[/bold]\n")

    builder.select_provider()
    if builder.provider is None:
        raise ValueError("Provider selection did not produce a value")
    provider_spec = get_provider_spec(builder.provider)

    builder.update_provider_api_key()
    builder.select_api_base()
    builder.select_model()
    builder.select_linter_preferences()

    should_verify = click.confirm(
        "Run a connectivity check now?",
        default=True,
    )
    verification_ok = False
    if should_verify:
        with console.status("[dim]Checking provider connectivity...[/dim]"):
            verification_ok = builder.verify_connection()

    builder.print_summary(verification_ok)
    if not click.confirm("Save this configuration?", default=True):
        console.print(
            "[yellow]Setup cancelled. No changes were saved.[/yellow]"
        )
        return

    built_config = builder.build()
    built_config.save()

    storage_note = ""
    if builder.provider is None:
        raise ValueError("Provider must be set before storing config")
    if provider_spec and provider_spec.requires_api_key:
        env_var = get_env_var_for_provider(builder.provider)
        storage_note = f"\nKey Source: [bold]{env_var or 'configured'}[/bold]"

    console.print(
        Panel(
            f"Provider: [bold]{built_config.provider}[/bold]\n"
            f"Model: [bold]{built_config.model}[/bold]\n"
            f"API Base: [bold]{built_config.api_base or 'Default'}"
            f"[/bold]{storage_note}",
            title="Configuration Saved to lintaider.toml",
            border_style="green",
        )
    )
