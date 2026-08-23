HMB GLOBAL - YouTube Cookie Fix

Fixed:
- Removed the old undefined YOUTUBE_COOKIE reference.
- Uses YOUTUBE_COOKIE_FILE from config.py.
- yt-dlp receives cookiefile only when the configured cookie path exists.

Fly.io Secret required:
YOUTUBE_COOKIE_FILE mounts to /app/cookies.txt

Important:
The Fly.io logs shown previously were running an older commit that still contained:
    if not YOUTUBE_COOKIE:
After replacing main.py, commit/push the new file and deploy the latest commit.
