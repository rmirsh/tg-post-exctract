from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional

from dotenv import dotenv_values, set_key
from telethon import TelegramClient
from toon_format import encode

DATA_DIR = Path("data")
ENV_FILE = DATA_DIR / ".env"
REQUIRED_KEYS = ("API_ID", "API_HASH", "CHANNEL_USERNAME")
SESSION_KEY = "SESSION_NAME"
FORMAT_KEY = "OUTPUT_FORMAT"
DEFAULT_SESSION = "session"
DEFAULT_FORMAT = "json"
VALID_FORMATS = ("json", "txt", "toon")
OutputFormat = Literal["json", "txt", "toon"]
Prompt = Callable[[], str]


@dataclass
class HarvestResult:
    channel: str
    session_name: str
    output: Path
    format: OutputFormat
    count: int


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_env_file() -> None:
    ensure_data_dir()
    if not ENV_FILE.exists():
        ENV_FILE.touch()


def load_config() -> Dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    return {k: v for k, v in dotenv_values(ENV_FILE).items() if v is not None}


def persist_config(updates: Dict[str, str]) -> None:
    ensure_env_file()
    for key, value in updates.items():
        set_key(str(ENV_FILE), key, str(value))


def ensure_required_config(config: Dict[str, str]) -> None:
    missing = [key for key in REQUIRED_KEYS if not config.get(key)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            f"Missing configuration values: {joined}. Run `teletoon configure` first."
        )


def normalize_format(value: str) -> OutputFormat:
    lowered = value.lower()
    if lowered not in VALID_FORMATS:
        raise ValueError(
            f"Unsupported format '{value}'. Choose from {', '.join(VALID_FORMATS)}."
        )
    return lowered  # type: ignore[return-value]


def serialize_messages(messages: List[Dict[str, str]], fmt: OutputFormat) -> str:
    if fmt == "json":
        return json.dumps(messages, ensure_ascii=False, indent=2)
    if fmt == "txt":
        lines = [f"{item['id']}: {item['text']}".strip() for item in messages]
        return "\n".join(lines)
    return encode(messages)


def resolve_output_path(path: Path) -> Path:
    ensure_data_dir()
    candidate = path if path.is_absolute() else DATA_DIR / path
    root = DATA_DIR.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Output files must live inside '{DATA_DIR}/'.")
    return resolved


async def ensure_authorized(
    client: TelegramClient,
    phone_number: Optional[str],
    prompt_phone: Prompt,
    prompt_code: Prompt,
    prompt_password: Prompt,
) -> None:
    if await client.is_user_authorized():
        return

    phone_arg: Prompt | str = phone_number or prompt_phone

    await client.start(
        phone=phone_arg,
        code_callback=lambda: prompt_code(),
        password=lambda: prompt_password(),
    )


async def fetch_messages(
    session_path: Path,
    api_id: int,
    api_hash: str,
    channel_username: str,
    limit: Optional[int],
    phone_number: Optional[str],
    prompt_phone: Prompt,
    prompt_code: Prompt,
    prompt_password: Prompt,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    async with TelegramClient(str(session_path), api_id, api_hash) as client:
        await ensure_authorized(
            client, phone_number, prompt_phone, prompt_code, prompt_password
        )
        async for msg in client.iter_messages(channel_username, limit=limit):
            if not msg.text:
                continue
            messages.append({"id": msg.id, "text": msg.text})
    return messages


def harvest(
    *,
    limit: Optional[int],
    channel: Optional[str],
    output: Optional[Path],
    output_format: Optional[OutputFormat],
    phone_number: Optional[str],
    prompt_phone: Prompt,
    prompt_code: Prompt,
    prompt_password: Prompt,
) -> HarvestResult:
    config = load_config()
    ensure_required_config(config)

    channel_username = channel or config["CHANNEL_USERNAME"]
    session_name = config.get(SESSION_KEY, DEFAULT_SESSION)
    session_path = DATA_DIR / session_name
    fmt = normalize_format(output_format or config.get(FORMAT_KEY) or DEFAULT_FORMAT)
    output_path = output or Path(f"messages.{fmt}")
    resolved_output = resolve_output_path(output_path)

    messages = asyncio.run(
        fetch_messages(
            session_path=session_path,
            api_id=int(config["API_ID"]),
            api_hash=config["API_HASH"],
            channel_username=channel_username,
            limit=limit,
            phone_number=phone_number,
            prompt_phone=prompt_phone,
            prompt_code=prompt_code,
            prompt_password=prompt_password,
        )
    )

    if not messages:
        return HarvestResult(
            channel=channel_username,
            session_name=session_name,
            output=resolved_output,
            format=fmt,
            count=0,
        )

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_messages(messages, fmt)
    resolved_output.write_text(payload)

    return HarvestResult(
        channel=channel_username,
        session_name=session_name,
        output=resolved_output,
        format=fmt,
        count=len(messages),
    )
