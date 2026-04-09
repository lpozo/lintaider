"""Handler for the 'init' command."""

import os

import click
from rich.panel import Panel

from codereview.ai.auth import get_env_var_for_provider, save_api_key
from codereview.cli.ui import console
from codereview.config import Config


def handle_init() -> None:
    """Execute the interactive initialization flow."""
    config = Config.load()

    provider = click.prompt(
        "AI Provider",
        default=config.provider,
        type=str,
    )
    model = click.prompt(
        "AI Model",
        default=config.model,
        type=str,
    )
    api_base = (
        click.prompt(
            "AI Provider API base URL (leave empty for default)",
            default=config.api_base or "",
            type=str,
            show_default=False,
        ).strip()
        or None
    )

    # API Key handling for Cloud providers
    if provider.lower() != "ollama":
        _update_env_api_key(provider)

    skipped_str = click.prompt(
        "Linters to skip by default (comma-separated, leave empty for none)",
        default=",".join(config.skip_linters),
        type=str,
        show_default=True,
    )
    only_str = click.prompt(
        "Linters to exclusively run by default (comma-separated, leave empty for all)",
        default=",".join(config.only_linters),
        type=str,
        show_default=True,
    )

    config.skip_linters = (
        [linter_name.strip().lower() for linter_name in skipped_str.split(",")]
        if skipped_str
        else []
    )
    config.only_linters = (
        [linter_name.strip().lower() for linter_name in only_str.split(",")]
        if only_str
        else []
    )

    config.provider = provider
    config.model = model
    config.api_base = api_base
    config.save()

    console.print(
        Panel(
            f"Provider: [bold]{config.provider}[/bold]\n"
            f"Model: [bold]{config.model}[/bold]\n"
            f"API Base: [bold]{config.api_base or 'Default'}[/bold]",
            title="Configuration Saved to codereview.toml",
            border_style="green",
        )
    )


def _update_env_api_key(provider: str) -> None:
    """Helper to ask and update the .env file with the provider's API key."""
    env_var = get_env_var_for_provider(provider)
    if not env_var:
        return

    current_key = os.getenv(env_var)
    api_key = click.prompt(
        f"Enter your {env_var} (leave empty to keep current or skip)",
        default=current_key or "",
        hide_input=True,
    )
    if not api_key:
        return

    save_api_key(env_var, api_key)
    console.print("[green]Saved API key to .env[/green]")
