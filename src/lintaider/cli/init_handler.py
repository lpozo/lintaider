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
from lintaider.ai.provider import list_provider_models, verify_provider_connection
from lintaider.ai.registry import PROVIDER_SPECS, get_provider_spec
from lintaider.cli.ui import console
from lintaider.config import Config
from lintaider.linters import LINTER_MAP


def handle_init() -> None:
    """Execute the interactive initialization flow."""
    config = Config.load()

    console.print("[bold]LintAIder Setup Wizard[/bold]\n")

    provider = _select_provider(config.provider)
    provider_spec = get_provider_spec(provider)

    api_key = _update_provider_api_key(provider)

    api_base = _select_api_base(provider, config.api_base)
    model = _select_model(provider, config.model, api_base, api_key)

    skip_linters, only_linters = _select_linter_preferences(config)

    should_verify = click.confirm(
        "Run a connectivity check now?",
        default=True,
    )
    verification_ok = True
    if should_verify:
        with console.status("[dim]Checking provider connectivity...[/dim]"):
            verification_ok = _run_connectivity_check(
                provider, model, api_base, api_key
            )

    _print_summary(
        provider, model, api_base, skip_linters, only_linters, verification_ok
    )
    if not click.confirm("Save this configuration?", default=True):
        console.print("[yellow]Setup cancelled. No changes were saved.[/yellow]")
        return

    config.provider = provider
    config.model = model
    config.api_base = api_base
    config.skip_linters = skip_linters
    config.only_linters = only_linters
    config.save()

    storage_note = ""
    if provider_spec and provider_spec.requires_api_key:
        env_var = get_env_var_for_provider(provider)
        storage_note = f"\nKey Source: [bold]{env_var or 'configured'}[/bold]"

    console.print(
        Panel(
            f"Provider: [bold]{config.provider}[/bold]\n"
            f"Model: [bold]{config.model}[/bold]\n"
            f"API Base: [bold]{config.api_base or 'Default'}[/bold]{storage_note}",
            title="Configuration Saved to lintaider.toml",
            border_style="green",
        )
    )


def _select_provider(current_provider: str) -> str:
    """Present a guided provider menu and return the selected provider ID.

    Args:
        current_provider: The currently configured provider ID, used to
            pre-select the default menu entry.

    Returns:
        The lowercase provider ID chosen by the user.
    """
    providers = list(PROVIDER_SPECS.values())
    default_index = 1
    for idx, spec in enumerate(providers, start=1):
        if spec.provider_id == current_provider:
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
            "[yellow]Invalid provider. Select a number from the list.[/yellow]"
        )


def _update_provider_api_key(provider: str) -> str | None:
    """Prompt for and securely store the provider API key when required.

    Skips the prompt for providers that do not require an API key (e.g.,
    Ollama). When an existing key is found and the user submits an empty
    input, the existing key is retained.

    Args:
        provider: The lowercase provider identifier.

    Returns:
        The API key entered or retrieved, or ``None`` if not applicable.
    """
    provider_spec = get_provider_spec(provider)
    if not provider_spec or not provider_spec.requires_api_key:
        return None

    env_var = get_env_var_for_provider(provider) or "API_KEY"
    existing_key = get_api_key_for_provider(provider)
    prompt = (
        f"Enter {env_var} (leave empty to keep existing)"
        if existing_key
        else f"Enter {env_var}"
    )
    api_key: str = click.prompt(prompt, default="", hide_input=True).strip()

    if not api_key:
        if existing_key:
            console.print("[dim]Keeping existing API key.[/dim]")
            return existing_key
        console.print("[yellow]No API key provided. Verification may fail.[/yellow]")
        return None

    backend = save_provider_api_key(provider, api_key)
    if backend == "keychain":
        console.print("[green]Saved API key to OS keychain.[/green]")
    elif backend == ".env":
        console.print("[green]Saved API key to .env (keychain unavailable).[/green]")

    return api_key


def _select_api_base(provider: str, current_api_base: str | None) -> str | None:
    """Prompt the user for an optional API base URL override.

    Falls back to the provider's default base URL when no override is given.

    Args:
        provider: The lowercase provider identifier.
        current_api_base: The API base URL currently stored in config, used
            as the pre-filled default in the prompt.

    Returns:
        The user-supplied base URL string, or ``None`` to use the provider
        default.
    """
    provider_spec = get_provider_spec(provider)
    default_api_base = current_api_base
    if not default_api_base and provider_spec:
        default_api_base = provider_spec.default_api_base

    api_base_input: str = click.prompt(
        "API base URL override (leave empty for provider default)",
        default=default_api_base or "",
        show_default=bool(default_api_base),
    ).strip()
    return api_base_input or None


def _build_model_candidates(
    provider: str,
    current_model: str,
    api_base: str | None,
    api_key: str | None,
) -> tuple[list[str], str]:
    """Build the list of model choices for the selection menu.

    Attempts live model discovery first. Falls back to the provider's
    recommended models list on failure, and always ensures the currently
    configured model appears as an option.

    Args:
        provider: The lowercase provider identifier.
        current_model: The model name currently stored in config.
        api_base: Optional API base URL override.
        api_key: Optional API key override.

    Returns:
        A two-tuple of ``(candidates, default_model)`` where ``candidates``
        is the ordered list of model names to display and ``default_model``
        is the pre-selected entry.
    """
    provider_spec = get_provider_spec(provider)
    default_model = current_model or (
        provider_spec.default_model if provider_spec else ""
    )

    console.print("[dim]Fetching available models...[/dim]")
    discovered_models = list_provider_models(
        provider, api_base=api_base, api_key=api_key
    )

    candidates: list[str] = []
    if discovered_models:
        candidates.extend(discovered_models)
    elif provider_spec and provider_spec.recommended_models:
        candidates.extend(provider_spec.recommended_models)
        console.print(
            "[yellow]Could not fetch models. Showing recommended options.[/yellow]"
        )

    if default_model and default_model not in candidates:
        candidates.insert(0, default_model)

    return candidates, default_model


def _select_model(
    provider: str,
    current_model: str,
    api_base: str | None,
    api_key: str | None,
) -> str:
    """Present a model selection menu and return the chosen model name.

    Displays discovered or recommended models in a numbered table. The user
    may select by number or type a custom model name directly.

    Args:
        provider: The lowercase provider identifier.
        current_model: The model name currently stored in config.
        api_base: Optional API base URL override.
        api_key: Optional API key override.

    Returns:
        The selected or manually entered model name string.
    """
    model_candidates, default_model = _build_model_candidates(
        provider, current_model, api_base, api_key
    )

    if not model_candidates:
        model: str = click.prompt("Model name", default=default_model or "llama3")
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


def _validate_and_filter_linters(linter_list: list[str], list_name: str) -> list[str]:
    """Remove unrecognised linter names and warn the user about them.

    Args:
        linter_list: The list of linter names to validate.
        list_name: A human-readable label for the list (e.g., ``"skip"``
            or ``"only"``), used in warning messages.

    Returns:
        A filtered list containing only known linter names.
    """
    invalid = [name for name in linter_list if name not in LINTER_MAP]
    if invalid:
        console.print(
            f"[yellow]Ignoring unknown {list_name} linters:[/yellow] "
            + ", ".join(sorted(invalid))
        )
        return [name for name in linter_list if name in LINTER_MAP]
    return linter_list


def _select_linter_preferences(config: Config) -> tuple[list[str], list[str]]:
    """Prompt the user for default linter skip and only preferences.

    Validates both lists against the known linter registry, warns on
    unknown names, and resolves conflicts when a linter appears in both.

    Args:
        config: The current configuration, used to pre-fill the prompts.

    Returns:
        A two-tuple of ``(skip_linters, only_linters)`` lists of validated
        linter name strings.
    """
    available_linters = sorted(LINTER_MAP.keys())
    console.print(f"[dim]Available linters: {', '.join(available_linters)}[/dim]")

    skipped_str = click.prompt(
        "Linters to skip by default (comma-separated)",
        default=",".join(config.skip_linters),
        show_default=True,
    )
    only_str = click.prompt(
        "Linters to exclusively run by default (comma-separated)",
        default=",".join(config.only_linters),
        show_default=True,
    )

    skip_linters = _parse_linter_list(skipped_str)
    only_linters = _parse_linter_list(only_str)

    skip_linters = _validate_and_filter_linters(skip_linters, "skip")
    only_linters = _validate_and_filter_linters(only_linters, "only")

    overlap = sorted(set(skip_linters).intersection(only_linters))
    if overlap:
        console.print(
            "[yellow]Removing linters present in both skip and only:[/yellow] "
            + ", ".join(overlap)
        )
        skip_linters = [name for name in skip_linters if name not in overlap]

    return skip_linters, only_linters


def _parse_linter_list(raw: str) -> list[str]:
    """Normalise a comma-separated string into a deduplicated list of linter names.

    Args:
        raw: Comma-separated linter names as entered by the user.

    Returns:
        An order-preserving, lowercased, deduplicated list of name strings.
        Returns an empty list when ``raw`` is blank.
    """
    if not raw:
        return []
    normalized = [item.strip().lower() for item in raw.split(",") if item.strip()]
    # Keep user order while deduplicating.
    return list(dict.fromkeys(normalized))


def _run_connectivity_check(
    provider: str,
    model: str,
    api_base: str | None,
    api_key: str | None,
) -> bool:
    """Run a blocking connectivity check and print the result to the console.

    Wraps the async ``verify_provider_connection`` coroutine using
    ``asyncio.run``. Gracefully handles ``RuntimeError`` when called inside
    an already-running event loop.

    Args:
        provider: The lowercase provider identifier.
        model: The model name to use for the test request.
        api_base: Optional API base URL override.
        api_key: Optional API key override.

    Returns:
        ``True`` if the connectivity check passed, ``False`` otherwise.
    """
    try:
        ok, message = asyncio.run(
            verify_provider_connection(
                provider_name=provider,
                model_name=model,
                api_base=api_base,
                api_key=api_key,
            )
        )
    except RuntimeError:
        ok, message = False, "Connectivity check could not run in this environment."

    if ok:
        console.print("[green]Connectivity check passed.[/green]")
    else:
        console.print(f"[yellow]Connectivity check failed:[/yellow] {message}")
    return ok


def _print_summary(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    provider: str,
    model: str,
    api_base: str | None,
    skip_linters: list[str],
    only_linters: list[str],
    verification_ok: bool,
) -> None:
    """Render a rich panel summarising the pending configuration before saving.

    Args:
        provider: The selected provider identifier.
        model: The selected model name.
        api_base: The selected API base URL, or ``None`` for the provider default.
        skip_linters: Linter names to skip by default.
        only_linters: Linter names to run exclusively by default.
        verification_ok: Whether the connectivity check passed.
    """
    status = "Passed" if verification_ok else "Skipped/Failed"
    skip_str = ", ".join(skip_linters) if skip_linters else "None"
    only_str = ", ".join(only_linters) if only_linters else "All"
    console.print(
        Panel(
            f"Provider: [bold]{provider}[/bold]\n"
            f"Model: [bold]{model}[/bold]\n"
            f"API Base: [bold]{api_base or 'Default'}[/bold]\n"
            f"Skip Linters: [bold]{skip_str}[/bold]\n"
            f"Only Linters: [bold]{only_str}[/bold]\n"
            f"Verification: [bold]{status}[/bold]",
            title="Setup Summary",
            border_style="cyan",
        )
    )
