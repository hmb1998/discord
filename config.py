"""Environment-based configuration for the Discord music bot."""
import os

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.50"))
ASSET_KEY = os.getenv("ASSET_KEY") or os.getenv("RICH_PRESENCE_ASSET_KEY") or "file_0000000049881f49ef3a3b0cb7cdf84"
RICH_PRESENCE_ASSET_KEY = os.getenv("ASSET_KEY") or os.getenv("RICH_PRESENCE_ASSET_KEY") or "file_0000000049881f49ef3a3b0cb7cdf84"

if not TOKEN:
    raise RuntimeError(
        "Missing Discord bot token. Set the DISCORD_TOKEN environment variable."
    )

RICH_PRESENCE_ASSET_KEY = ASSET_KEY
