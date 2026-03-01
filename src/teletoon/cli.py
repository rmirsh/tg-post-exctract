from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import typer

from . import core

app = typer.Typer(
    name="teletoon", help="TeleToon harvests Telegram posts into exportable files."
)


def prompt_with_default(
    label: str,
    default: Optional[str],
    cli_value: Optional[str],
    *,
    hide_input: bool = False,
) -> str:
    if cli_value is not None:
        return cli_value

    prompt_kwargs = {}
    if hide_input:
        prompt_kwargs["hide_input"] = True
    if default is not None:
        prompt_kwargs["default"] = default

    result = typer.prompt(label, **prompt_kwargs)
    if not result:
        raise typer.BadParameter(f"{label} cannot be empty")
    return result


def prompt_hidden(label: str) -> str:
    return typer.prompt(label, hide_input=True)


def prompt_phone_number() -> str:
    return typer.prompt(
        "Enter the phone number linked to Telegram (include country code)"
    )


@app.command()
def configure(
    api_id: Optional[int] = typer.Option(
        None,
        help="Telegram API ID from https://my.telegram.org.",
        rich_help_panel="Credentials",
    ),
    api_hash: Optional[str] = typer.Option(
        None,
        help="Telegram API hash from https://my.telegram.org.",
        rich_help_panel="Credentials",
    ),
    channel_username: Optional[str] = typer.Option(
        None, "--channel", "-c", help="Telegram channel username to scrape."
    ),
    session_name: Optional[str] = typer.Option(
        None,
        "--session",
        "-s",
        help="Session file name to store Telethon auth data.",
    ),
    output_format: Optional[core.OutputFormat] = typer.Option(
        None,
        "--format",
        "-f",
        help="Default export format (json, txt, or toon).",
        case_sensitive=False,
    ),
) -> None:
    """Prompt for credentials and persist them inside .env."""

    config = core.load_config()
    collected: Dict[str, str] = {}

    existing_api_id = config.get("API_ID")
    api_id_str = prompt_with_default(
        "API ID",
        existing_api_id,
        str(api_id) if api_id is not None else None,
    )
    if not api_id_str.isdigit():
        raise typer.BadParameter("API ID must be a number.")
    collected["API_ID"] = api_id_str

    collected["API_HASH"] = prompt_with_default(
        "API Hash",
        config.get("API_HASH"),
        api_hash,
        hide_input=True,
    )

    collected["CHANNEL_USERNAME"] = prompt_with_default(
        "Channel username (ex: @telegram)",
        config.get("CHANNEL_USERNAME"),
        channel_username,
    )

    collected[core.SESSION_KEY] = prompt_with_default(
        f"Session file name (stored under {core.DATA_DIR}/)",
        config.get(core.SESSION_KEY, core.DEFAULT_SESSION),
        session_name,
    )

    desired_format = prompt_with_default(
        f"Output format ({'/'.join(core.VALID_FORMATS)})",
        config.get(core.FORMAT_KEY, core.DEFAULT_FORMAT),
        output_format,
    )
    try:
        collected[core.FORMAT_KEY] = core.normalize_format(desired_format)
    except ValueError as exc:  # noqa: PERF203 - user input validation
        raise typer.BadParameter(str(exc)) from exc

    core.persist_config(collected)
    typer.secho(f"Configuration saved to {core.ENV_FILE}", fg=typer.colors.GREEN)


@app.command()
def harvest(
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum number of messages to fetch."
    ),
    channel: Optional[str] = typer.Option(
        None, "--channel", "-c", help="Override channel username for this run."
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help=f"Export file relative to {core.DATA_DIR}/ (defaults to messages.<format>). Absolute paths must also live inside it.",
    ),
    output_format: Optional[core.OutputFormat] = typer.Option(
        None,
        "--format",
        "-f",
        help="Export format for this run (json, txt, or toon).",
        case_sensitive=False,
    ),
    phone_number: Optional[str] = typer.Option(
        None,
        "--phone",
        help="Phone number (include +country code) for Telegram login, used when the session is not yet authorized.",
    ),
) -> None:
    """Fetch Telegram posts and export them in the requested format."""

    typer.echo("Preparing harvest...")
    try:
        result = core.harvest(
            limit=limit,
            channel=channel,
            output=output,
            output_format=output_format,
            phone_number=phone_number,
            prompt_phone=prompt_phone_number,
            prompt_code=lambda: prompt_hidden("Enter the login code sent to Telegram"),
            prompt_password=lambda: prompt_hidden("Enter your 2FA password"),
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Channel {result.channel} via session '{result.session_name}' -> {result.output} [{result.format}]"
    )

    if result.count == 0:
        typer.echo("No text messages retrieved. Nothing to write.")
        return

    typer.secho(
        f"Wrote {result.count} messages to {result.output} as {result.format}",
        fg=typer.colors.GREEN,
    )
