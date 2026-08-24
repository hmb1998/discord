"""HMB GLOBAL configuration."""
from __future__ import annotations

import os


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


TOKEN = (os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN") or "").strip()
if not TOKEN:
    raise RuntimeError(
        "Missing Discord bot token. Set DISCORD_TOKEN in Fly.io Secrets."
    )

DEFAULT_VOLUME = _env_float("DEFAULT_VOLUME", 0.50, 0.0, 1.0)

DB_PATH = os.getenv("DB_PATH", "/app/data/hmb_global.sqlite3").strip()
if not DB_PATH:
    DB_PATH = "/app/data/hmb_global.sqlite3"

# YouTube cookies are read from a Fly.io file secret.
# The legacy environment-variable fallback is intentionally disabled by default
# because very large cookie values can exceed the process argument/environment limit.
YOUTUBE_COOKIE_FILE = "/app/cookies.txt"

RICH_PRESENCE_ASSET_KEY = (
    os.getenv("ASSET_KEY")
    or os.getenv("RICH_PRESENCE_ASSET_KEY")
    or "file_0000000049881f49ef3a3b0cb7cdf84"
).strip()
