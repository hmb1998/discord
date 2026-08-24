# Rich Presence Asset

This folder contains `hmb_global_asset.png`, a 1024x1024 PNG prepared for Discord Developer Portal -> Rich Presence -> Assets.

The bot code reads `ASSET_KEY` (or the legacy `RICH_PRESENCE_ASSET_KEY`) from the environment. The current default key in `config.py` matches the asset key shown in the supplied Developer Portal screenshot.

If you upload this new image as a new Discord asset, Discord may assign a different asset key. In that case, set:
RICH_PRESENCE_ASSET_KEY=<the exact key shown by Discord>

Do not put the Discord bot token in the repository.
