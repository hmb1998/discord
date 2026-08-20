# 🎵 Discord Music Bot

A Discord music bot that plays audio from YouTube and supports **both slash commands and `!` prefix commands**.

## ✨ Features

- ▶️ Play music from YouTube (URL or search)
- 📋 Queue, skip, pause, resume and stop
- 🔀 Shuffle and loop controls
- ⭐ Favorites and playlists
- 🎚️ Volume and audio presets
- 📝 Lyrics/search helpers
- 📥 Queue/history utilities
- 🌐 Fly.io health endpoint
- 🔒 Token is read from an environment variable — never put it in source code

## Commands

The project contains **100 slash commands** (Discord's top-level limit). All 100 also have `!` prefix aliases, plus the extra `!uptime_seconds` prefix-only command.

Examples:

```text
/play never gonna give you up
!play never gonna give you up

/pause
!pause

/queue
!queue

/skip
!skip
```

## 1. Create the Discord bot

1. Open the Discord Developer Portal.
2. Create a new application and add a Bot.
3. Copy the bot token.
4. Enable **Message Content Intent** and **Server Members Intent** if required by the commands you use.
5. Invite the bot with the `bot` and `applications.commands` scopes and the needed voice/message permissions.

## 2. Run locally

Python 3.12 is recommended. FFmpeg must be installed and available on `PATH`.

```bash
pip install -r requirements.txt
export DISCORD_TOKEN="YOUR_TOKEN"
python main.py
```

On Windows PowerShell:

```powershell
$env:DISCORD_TOKEN="YOUR_TOKEN"
python main.py
```

## 3. Deploy to Fly.io

Create the app using the Fly CLI, then set the token as a secret:

```bash
fly launch --no-deploy
fly secrets set DISCORD_TOKEN="YOUR_TOKEN"
fly deploy
```

The included `Dockerfile` installs FFmpeg. The included `fly.toml` exposes port `8080` for the health check.

## Security

**Never commit the Discord token to GitHub.** If a token was ever exposed publicly, regenerate it immediately in the Discord Developer Portal.


### Prefix command fix
The 100 slash commands are kept within Discord's top-level slash-command limit. `!` commands call the same slash callbacks directly, and `!uptime_seconds` remains prefix-only. This avoids duplicate registration and the `command function must be a coroutine function` / 100-command-limit startup errors.


## Rich Presence Assets

This build sets the bot activity to **Listening to HMB GLOBAL** and uses the Discord Rich Presence asset as the `large_image`.

### Rich Presence large image
The supplied HMB GLOBAL asset key is:

`file_0000000049881f49ef3a3b0cb7cdf84`

For Fly.io, add this as a Secret named `ASSET_KEY`. The code also accepts `RICH_PRESENCE_ASSET_KEY` for compatibility.

```bash
fly secrets set ASSET_KEY="file_0000000049881f49ef3a3b0cb7cdf84"
fly deploy
```

If Discord gives the image a new asset key after you re-upload it, replace the value of `ASSET_KEY` with the new key.


## 🚀 HMB GLOBAL Rich Presence (Fly.io)

This build is already wired to show the HMB GLOBAL Rich Presence when the bot connects.

### Fly.io setup

1. In **Discord Developer Portal → Rich Presence → Assets**, upload the HMB GLOBAL image.
2. Copy the asset key shown for that image. The supplied build currently uses:
   `file_0000000049881f49ef3a3b0cb7cdf84`
3. In Fly.io → **Secrets**, create/update:
   - **Name:** `ASSET_KEY`
   - **Secret:** `file_0000000049881f49ef3a3b0cb7cdf84`
4. Click **Set secret**.
5. Click **Deploy Secrets** (or run `fly deploy`).
6. Check Logs. A successful startup prints:
   `✅ Rich Presence enabled with asset: ...`

### Important

- `ASSET_KEY` is **not** the Discord bot token.
- Never put `DISCORD_TOKEN` in source code or GitHub.
- The Discord Developer Portal **Rich Presence Visualizer is only a preview**; the bot code sends the activity.
- If you delete/re-upload the image, Discord may give it a different asset key. Update `ASSET_KEY` and deploy again.
