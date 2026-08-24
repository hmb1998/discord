# 🎵 HMB GLOBAL

```{=html}
<p align="center">
```
`<img src="banner.png" alt="HMB GLOBAL" width="100%">`{=html}
```{=html}
</p>
```
```{=html}
<p align="center">
```
`<strong>`{=html}Smart • Fast • Secure • Powerful Discord Music
Bot`</strong>`{=html}
```{=html}
</p>
```
```{=html}
<p align="center">
```
`<a href="https://github.com/hmb1998/discord">`{=html}`<img src="https://img.shields.io/github/stars/hmb1998/discord?style=for-the-badge" alt="GitHub Stars">`{=html}`</a>`{=html}
`<a href="https://github.com/hmb1998/discord/commits/main">`{=html}`<img src="https://img.shields.io/github/last-commit/hmb1998/discord?style=for-the-badge" alt="Last Commit">`{=html}`</a>`{=html}
`<a href="https://www.python.org/">`{=html}`<img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">`{=html}`</a>`{=html}
`<a href="https://discordpy.readthedocs.io/">`{=html}`<img src="https://img.shields.io/badge/discord.py-2.4+-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="discord.py">`{=html}`</a>`{=html}
`<a href="https://fly.io/">`{=html}`<img src="https://img.shields.io/badge/Deploy-Fly.io-8B5CF6?style=for-the-badge" alt="Fly.io">`{=html}`</a>`{=html}
```{=html}
</p>
```
> **HMB GLOBAL** is an all-in-one Discord bot focused on music, voice
> playback, playlists, favorites, history, audio controls, moderation,
> security, persistence, and server utilities.

## 🚀 Highlights

-   🎧 Full Discord voice/music system
-   ⚡ **100 Slash Commands** loaded by the current bot deployment
-   ⌨️ `!` prefix aliases
-   📋 Queue, history, favorites, and playlists
-   🔁 Loop, shuffle, seek, rewind, forward, restart, move, swap and
    queue tools
-   🎛️ Audio effects and EQ-style presets
-   🛡️ Moderation and anti-spam/security controls
-   💾 SQLite persistence for bot data
-   🍪 YouTube cookie support for yt-dlp
-   🦕 Deno runtime support for current YouTube JavaScript challenges
-   🧹 Automatic audio-cache cleanup
-   🚀 Docker + Fly.io deployment support
-   ❤️ Rich Presence and `/healthz` monitoring endpoint

## 🎶 Music System

HMB GLOBAL provides a complete voice playback workflow: play/search,
pause/resume, skip, stop, volume, now playing, queue management,
join/leave voice, shuffle, repeat/loop, seek, rewind, forward, restart,
jump/move, swap, duplicate removal and queue utilities.

The bot maintains per-guild playback state including queues, current
track, history, favorites, playlists, loop mode, shuffle mode, sleep
timers, EQ presets, and playback generations/locks.

## ⭐ Favorites, Playlists & History

-   Add/remove/list/play favorites
-   Create/delete/list/play playlists and add tracks
-   View, replay, recent-track and clear-history tools

Persistent bot state is handled by the SQLite storage layer.

## 🎛️ Audio Controls

Includes volume, equalizer-style presets, Bass Boost, Nightcore,
Vaporwave, Slow, Speed and Karaoke-style controls.

## 🛡️ Moderation & Security

-   Anti-spam protection
-   Duplicate-message detection
-   Mention-spam detection
-   Discord invite/link controls
-   Progressive timeout protection
-   Member warnings
-   Lockdown controls
-   Message cleanup
-   Maintenance controls
-   Permission-aware command error handling

## 💾 Persistence & Audio Cache

Default database path:

``` text
/app/data/hmb_global.sqlite3
```

Audio cache:

``` text
/app/data/hmb_audio
```

The Fly.io configuration mounts `/app/data` for application data. HMB
GLOBAL also runs an automatic audio-cache cleanup task so expired/extra
cached files are removed according to the configured cache limits.

## 🧠 YouTube / yt-dlp Runtime

The project supports YouTube cookies, `yt-dlp[default]`, Deno for
JavaScript challenges, and FFmpeg audio processing. The Docker image
installs FFmpeg and Deno, while the application detects the Deno
executable and resolves the configured cookie file.

Fly.io mounts the `YOUTUBE_COOKIE_FILE` secret at `/app/cookies.txt`.

**Never commit real YouTube cookies or Discord tokens to GitHub.**

## 🩺 Health Check

``` text
GET /healthz
```

The endpoint reports bot readiness and connected guild count and is used
by the Fly.io HTTP health check.

## 📋 Command Groups

The current deployment reports **100 Slash Commands loaded**.

  -----------------------------------------------------------------------
  Category                            Examples
  ----------------------------------- -----------------------------------
  🎵 Music                            `/play`, `/pause`, `/resume`,
                                      `/skip`, `/stop`, `/volume`

  📋 Queue                            `/queue`, `/shuffle`, `/loop`,
                                      `/seek`, `/move`, `/remove`

  ⭐ Favorites                        favorite management and playback
                                      commands

  📚 Playlists                        playlist creation, editing, listing
                                      and playback

  📜 History                          history, recent tracks and replay
                                      tools

  🎛️ Audio                            EQ/effects and playback-speed
                                      controls

  🛡️ Security                         security, warning, lockdown and
                                      anti-spam tools

  ℹ️ Utilities                        ping, uptime, statistics,
                                      server/user and bot tools
  -----------------------------------------------------------------------

The source code is the authority for exact command names, options,
permissions and behavior.

## 📁 Project Structure

``` text
hmb-global-bot/
├── main.py              # Discord bot, music system, commands and events
├── storage.py           # SQLite persistence layer
├── config.py            # Runtime configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Safe configuration template
├── Dockerfile           # Container image definition
├── fly.toml             # Fly.io deployment configuration
├── README.md            # Project documentation
├── PRIVACY.md           # Privacy information
├── TERMS.md              # Terms / usage information
├── FIXES.md              # Fixes and maintenance notes
├── banner.png           # HMB GLOBAL branding
├── assets/              # Project assets
└── data/                # Runtime/local data directory
```

## 🧰 Tech Stack

  Technology        Purpose
  ----------------- -------------------------------
  🐍 Python 3.12+   Application runtime
  🤖 discord.py     Discord API and bot framework
  🎵 yt-dlp         Media extraction / downloads
  🦕 Deno           YouTube JavaScript runtime
  🔊 FFmpeg         Audio processing
  🧂 PyNaCl         Discord voice support
  🗃️ SQLite         Persistent bot state
  🌐 Flask          Health/web endpoint
  🐳 Docker         Container deployment
  🚀 Fly.io         Production hosting

## 🚀 Local Installation

``` bash
git clone https://github.com/hmb1998/discord.git
cd discord
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

Set your Discord bot token and other required values in the environment.
Never commit `.env` or real secrets.

## 🚀 Fly.io Deployment

Current application:

``` text
hmb-global-bot
```

Typical deployment:

``` bash
fly auth login
fly deploy -a hmb-global-bot
fly logs -a hmb-global-bot
```

Set secrets through Fly.io:

``` bash
fly secrets set DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN" -a hmb-global-bot
```

Configure the `YOUTUBE_COOKIE_FILE` secret for YouTube cookie support.

## 🔐 Security Rules

Never commit:

-   ❌ Discord bot tokens
-   ❌ YouTube cookies
-   ❌ `.env` files containing secrets
-   ❌ Private credentials

Use Fly.io secrets or environment variables for sensitive configuration.
If a credential is exposed, revoke/rotate it immediately.

## 🧩 Runtime Architecture

``` text
Discord
   │
   ▼
HMB GLOBAL (Python)
   │
   ├── Discord Slash Commands
   ├── Voice / Music Engine
   ├── yt-dlp + Deno
   ├── FFmpeg
   ├── SQLite Persistence
   ├── Audio Cache + Automatic Cleanup
   ├── Moderation / Security
   └── Flask Health Endpoint
          │
          ▼
       Fly.io
```

## 📜 Documentation

-   [`PRIVACY.md`](PRIVACY.md) --- privacy information
-   [`TERMS.md`](TERMS.md) --- project usage terms
-   [`FIXES.md`](FIXES.md) --- fixes and maintenance notes
-   [`.env.example`](.env.example) --- safe configuration template
-   [`fly.toml`](fly.toml) --- Fly.io deployment configuration

## 👑 HMB GLOBAL

> **One bot. One system. Complete Discord control.**

Built for communities that want music, voice playback, playlists,
moderation, security, and useful server tools in one professional
Discord bot.

**HMB GLOBAL --- Smart • Secure • Powerful.**

## ⚠️ Disclaimer

HMB GLOBAL depends on Discord, YouTube/media providers, yt-dlp, FFmpeg,
and other external services/software. Availability and behavior can
change when external APIs, media providers, or dependency versions
change.

This README documents the repository's current architecture and
configuration; the source code is the final authority for exact
implementation details.
