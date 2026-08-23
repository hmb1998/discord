# 🎵 HMB Music Bot

> **HMB Music Bot — Professional Discord Music, Moderation & Server Utility Bot**

A powerful Discord bot built with **Python + discord.py**, designed to combine high-quality music playback, queue management, playlists, favorites, history, audio effects, moderation, security tools, and server utilities in one professional package.

---

## ✨ Features

### 🎶 Music System
HMB Music Bot provides a complete music experience for your Discord server:

- ▶️ Play music from supported sources
- ⏸️ Pause / ▶️ Resume
- ⏭️ Skip tracks
- ⏹️ Stop playback
- 🔊 Volume control
- 📜 Queue management
- 🎵 Now Playing
- 🔎 Music search
- 🔁 Loop / Repeat
- 🔀 Shuffle
- ⏩ Seek / Forward
- ⏪ Rewind
- 🔄 Restart current track
- 🎚️ Queue reordering and cleanup
- 🎧 Voice channel join / leave

### ⭐ Favorites & Playlists
Save your favorite music and create personal playlists:

- Add/remove favorites
- View favorite tracks
- Play favorites
- Create playlists
- Delete playlists
- Add tracks to playlists
- List playlists
- Play playlists
- View playlist information

### 📜 History
Keep track of recently played music:

- View listening history
- Replay previous tracks
- View recent tracks
- Clear history

### 🎛️ Audio Effects
Customize the sound with built-in effects such as:

- Bass Boost
- Nightcore
- Vaporwave
- Slow
- Speed
- Equalizer
- Karaoke

### 🛡️ Moderation & Security
The bot also includes server protection and moderation features:

- Clear messages
- Warn members
- Mute / Unmute
- Lockdown / Unlockdown
- Clean-up tools
- Maintenance mode
- Security controls
- Anti-spam protection
- Duplicate-message detection
- Mention-spam detection
- Discord invite/link protection
- Timeout-based protection
- Security logging

### ⚙️ Server & Bot Utilities

- Ping
- Uptime
- Bot statistics
- Help system
- Bot information
- Server information
- User information
- Avatar display
- Server icon
- Voice status
- Invite information

---

## 📋 Commands

The project currently contains **100 Slash Commands** covering music, playlists, favorites, history, audio effects, queue controls, moderation/security, and utility features.

### 🎵 Music Commands
`/play` · `/playtop` · `/pause` · `/resume` · `/skip` · `/stop` · `/volume` · `/queue` · `/nowplaying` · `/remove` · `/shuffle` · `/loop` · `/seek` · `/move` · `/join` · `/leave` · `/search`

### ⭐ Favorites & Playlists
`/favorite_add` · `/favorite_remove` · `/favorite_list` · `/favorite_play`

`/playlist_create` · `/playlist_delete` · `/playlist_add` · `/playlist_list` · `/playlist_play` · `/playlist_info`

### 📜 History & Lyrics
`/history` · `/history_play` · `/history_clear` · `/recent` · `/lyrics`

### 🎛️ Audio Effects
`/bassboost` · `/nightcore` · `/vaporwave` · `/slow` · `/speed` · `/equalizer` · `/karaoke`

### 🔄 Advanced Queue Controls
`/goto` · `/rewind` · `/forward` · `/restart` · `/jump` · `/swap` · `/repeat` · `/remove_dupes` · `/queue_length` · `/queue_save` · `/queue_first` · `/queue_last` · `/queue_reverse` · `/queue_random` · `/queue_clear_after`

### 🛡️ Moderation & Security
`/security` · `/clear` · `/mute` · `/unmute` · `/warn` · `/lockdown` · `/unlockdown` · `/clean` · `/maintenance` · `/reset`

### ℹ️ Information & Utilities
`/ping` · `/uptime` · `/stats` · `/help` · `/invite` · `/about` · `/serverinfo` · `/userinfo` · `/avatar` · `/server_icon` · `/botinfo` · `/voice_status`

> **Note:** The command list above is organized by function for easier navigation. The source code remains the authoritative reference for the exact implementation and available options.

---

## 📁 Project Structure

```text
discord-main/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── fly.toml
├── README.md
├── PRIVACY.md
├── TERMS.md
├── banner.png
├── .dockerignore
├── .gitignore
└── assets/
    ├── hmb_global_asset.png
    └── README.md
```

### 🔥 `main.py`
The main application file containing the bot logic, commands, music system, queue handling, security/moderation features, and Discord event handling.

### ⚙️ `config.py`
Central configuration for important bot settings such as token-related configuration, default volume, and Rich Presence settings.

### 📦 `requirements.txt`
Contains the Python dependencies required to run the project.

### 🔐 `.env.example`
Example environment configuration intended for storing sensitive values outside the source code.

### 🐳 `Dockerfile`
Allows the bot to be packaged and deployed in a Docker-based environment.

### 🚀 `fly.toml`
Deployment configuration for Fly.io.

### 📜 `PRIVACY.md`
Privacy-related information for the project.

### 📄 `TERMS.md`
Terms and usage information for the bot/project.

### 🖼️ `assets/`
Project assets and shared bot branding resources.

---

## 🚀 Installation

### 1. Clone the project

```bash
git clone <YOUR_REPOSITORY_URL>
cd discord-main
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the bot

Copy the example environment file:

```bash
cp .env.example .env
```

Then add your Discord bot configuration.

**Never publish your real Discord bot token to GitHub.**

### 4. Start the bot

```bash
python main.py
```

When the bot starts successfully, it should connect to Discord and register its available commands.

---

## 🔒 Security

Keep all secrets outside your public repository.

Recommended:

- Store the Discord token in environment variables.
- Never upload `.env`.
- Never paste a real token into `main.py`.
- If a token is accidentally exposed, immediately regenerate it through the Discord Developer Portal.

---

## 🧩 Technology

The project is built around:

- 🐍 Python
- 🤖 discord.py
- 🎵 Discord Voice / Music components
- 🔊 Audio processing
- 🛡️ Moderation & security systems
- 🐳 Docker deployment support
- 🚀 Fly.io deployment configuration

---

## 💎 What HMB Can Do

HMB is designed as an **all-in-one Discord bot** rather than a simple music player.

It can:

**🎵 Play Music**  
Join a voice channel, play tracks, manage queues, control volume, search music, and handle playback.

**📚 Manage Your Music**  
Create playlists, save favorites, view history, and replay tracks.

**🎛️ Customize Audio**  
Apply effects such as Bass Boost, Nightcore, Vaporwave, Slow, Speed, Equalizer, and Karaoke.

**🛡️ Protect Your Server**  
Use moderation and security tools to help control spam, unwanted links/invites, excessive mentions, and problematic activity.

**⚙️ Manage Your Server**  
Use utility and moderation commands for everyday Discord server management.

---

## 🌟 HMB Philosophy

HMB is built with one goal:

> **One bot. One system. Complete Discord control.**

From music and playlists to moderation, security, and server utilities, HMB brings the most important features together inside a single Discord bot.

---

## 👑 HMB

**HMB Music Bot**  
Professional • Powerful • Fast • Secure

Made for Discord communities that want music, moderation, security, and utility features in one place.

---

### ⚠️ Disclaimer

This README describes the project based on the provided source package. Exact behavior can depend on Discord API changes, dependency versions, external music providers, deployment environment, and the bot's configuration.
