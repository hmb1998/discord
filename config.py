"""Environment-based configuration for the Discord music bot."""
import os

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.50"))

if not TOKEN:
    raise RuntimeError(
        "Missing Discord bot token. Set the DISCORD_TOKEN environment variable."
    )
