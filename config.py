"""Environment-based configuration for the Discord music bot."""
import os

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.50"))

# Discord Rich Presence asset key.
# Set ASSET_KEY in Fly.io Secrets to the key of the uploaded Rich Presence image.
# The fallback keeps the supplied HMB GLOBAL asset working if ASSET_KEY is not set.
RICH_PRESENCE_ASSET_KEY = (
    os.getenv("ASSET_KEY")
    or os.getenv("RICH_PRESENCE_ASSET_KEY")
    or "file_0000000049881f49ef3a3b0cb7cdf84"
)

if not TOKEN:
    raise RuntimeError(
        "Missing Discord bot token. Set the DISCORD_TOKEN environment variable."
    )
