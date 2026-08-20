import os

# Bot token - read ONLY from environment variable
# NEVER hardcode this in any file!
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# GitHub files URL (optional - can be set via fly secrets too)
GITHUB_FILES_URL = os.environ.get('GITHUB_FILES_URL', '')

# Bot settings
BOT_PREFIX = '!'
DEFAULT_VOLUME = 0.5  # 0.0 to 1.0
MAX_QUEUE_SIZE = 50
