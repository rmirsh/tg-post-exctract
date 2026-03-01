# TeleToon CLI

**TeleToon** authenticates with Telegram via [Telethon](https://docs.telethon.dev/) and exports channel posts to JSON, plain text, or native [Toon](https://github.com/toon-format/toon-python) archives. All credentials, session files, and message exports are stored inside the local `data/` directory.

## Prerequisites

- Python 3.12+
- Telegram API ID/API Hash from <https://my.telegram.org>
- Install deps via `uv sync` or `pip install -e .`

## Configure Credentials

Run the interactive wizard to store your credentials in `data/.env`:

```bash
teletoon configure
```

> Running from source? Use `./teletoon configure` (or `uv run teletoon configure`) inside the repo before installing as a package.

The command prompts for API ID, API hash, channel username, session file name (stored as `data/<name>.session`), and preferred export format (`json`, `txt`, or `toon`, default `json`). Re-run the command any time to update values; pressing Enter keeps the existing default.

## Scrape a Channel

```bash
teletoon harvest --limit 100 --output harvest.txt --format txt --phone +18624550861
```

> From the repository without installing: `./teletoon harvest ...`
>
> All exports land under `data/`, so the example above produces `data/harvest.txt`.

Options:

- `--limit / -l`: restrict the number of fetched messages (default: all).
- `--channel / -c`: override the stored channel username for a single run.
- `--output / -o`: export file relative to `data/` (defaults to `data/messages.<format>`). Absolute paths must also live under `data/`.
- `--format / -f`: override the configured export format for one run (`json`, `txt`, or `toon`).
- `--phone`: phone number (with country code) used for the Telethon login prompt. Optional—if omitted, you'll be prompted interactively.

On the first run Telethon opens an interactive login flow (sent to your Telegram app). The resulting session data is saved using the configured session name (default `session.session`).

## Usage / Distribution

Anyone landing on GitHub can get started in a few minutes:

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-org>/tg-post-exctract.git
   cd tg-post-exctract
   ```
2. **Install dependencies**
   - With [uv](https://docs.astral.sh/uv/):
     ```bash
     uv sync
     uv pip install -e .
     ```
   - Or with pip only:
     ```bash
     pip install -e .
     ```
     (The `-e` flag makes the `teletoon` console script available immediately.)
3. **Configure TeleToon**
   ```bash
   teletoon configure
   ```
   Follow the prompts for API ID/Hash, channel username, session name, and default export format.
4. **Harvest posts**
   ```bash
   teletoon harvest --channel @mychannel --format toon --phone +1234567890
   ```
   Adjust flags as needed (`teletoon harvest --help` for the full list). The default export file is `data/messages.<format>` unless overridden.

### Running without installing

If you prefer not to install the package globally, all commands can be executed via the bundled script:

```bash
./teletoon configure
./teletoon harvest --limit 50 --output dump.txt --format txt
```

Or through `uv run teletoon ...`, which resolves dependencies on-the-fly without touching your global environment.

## Data Directory

`data/` is created automatically and contains:

- `data/.env` – stored API keys, hashes, and channel configuration.
- `data/<session>.session` – Telethon session files (auth tokens, login state).
- `data/<exports>` – message dumps written via `teletoon harvest`.

## Output Formats

| Format | Description | Suggested extension |
| --- | --- | --- |
| `json` (default) | Structured list of message objects (`id`, `text`), UTF‑8 encoded with indentation for readability. | `.json` |
| `txt` | Simple newline-delimited text with each line formatted as `message_id: message body`. | `.txt` |
| `toon` | Serialized Toon payload compatible with Toon tooling (binary-safe but emitted as a single string). | `.toon` |

## Notes

- Non-text messages are skipped.
- `data/.env` stores `API_ID`, `API_HASH`, `CHANNEL_USERNAME`, `SESSION_NAME`, and `OUTPUT_FORMAT`. Handle it like any other secret.
- The CLI overwrites files under `data/` on every run; choose names/extensions that match the chosen format.
- If you prefer not to install the CLI entry point, you can still run `python main.py configure` / `python main.py harvest` directly.
