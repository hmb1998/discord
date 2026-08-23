import os


TOKEN = os.getenv(
    "DISCORD_TOKEN",
    ""
)


DEFAULT_VOLUME = float(
    os.getenv(
        "DEFAULT_VOLUME",
        "0.5"
    )
)


RICH_PRESENCE_ASSET_KEY = os.getenv(
    "ASSET_KEY",
    ""
)


DB_PATH = os.getenv(
    "DB_PATH",
    "/app/data/hmb_global.sqlite3"
)


YOUTUBE_COOKIE_FILE = os.getenv(
    "YOUTUBE_COOKIE_FILE",
    "/app/data/cookies.txt"
)
