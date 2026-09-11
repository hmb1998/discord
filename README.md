# HMB GLOBAL 🎵

> A professional Discord music bot built with Python, `discord.py`, `yt-dlp`, FFmpeg, SQLite, and Docker.

HMB GLOBAL is a feature-rich Discord music bot focused on reliable voice playback, YouTube search/download, queue management, audio effects, persistent bot data, Rich Presence, and production deployment.

## ✨ Features

### 🎵 Music & Voice
- YouTube search and YouTube URL playback
- Discord voice-channel connection
- Audio download and local playback through FFmpeg
- Queue management
- Play-next / automatic queue progression
- Play-top support
- Loop and shuffle functionality
- Playback generation protection to avoid stale playback
- Cached local audio to reduce repeated downloads

### 🎚️ Audio Controls
- Volume control
- Bass boost
- Nightcore
- Vaporwave
- Karaoke
- Speed control
- Equalizer presets
- FFmpeg audio filters

### 📚 User & Server Data
- Playback history
- Favorites
- Playlists
- Warnings
- Skip lists
- Guild/server settings
- SQLite-based storage

### 🤖 Discord
- Discord slash commands
- 100+ registered slash commands
- Rich Presence
- Safe interaction handling
- Voice connection error handling
- Automatic slash-command synchronization

### 🛡️ YouTube / yt-dlp
- `yt-dlp` integration
- Deno JavaScript runtime for current YouTube challenge handling
- YouTube cookie-file support
- Configurable HTTP headers and user agent
- Download retry handling
- Local cookie preparation for read-only container secret files

### 🚀 Deployment
- Docker-based deployment
- Render Web Service compatible
- Health endpoint: `/healthz`
- Production HTTP server with Waitress
- Environment-variable configuration
- FFmpeg included in the Docker image
- Deno installed automatically in the Docker image

## 🧰 Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Main runtime |
| discord.py | Discord bot and slash commands |
| yt-dlp | YouTube extraction/download |
| FFmpeg | Audio processing/playback |
| PyNaCl | Discord voice support |
| Flask | Health/web endpoint |
| Waitress | Production WSGI server |
| SQLite | Bot data storage |
| Docker | Deployment/runtime environment |
| Deno | YouTube JavaScript challenge support |

## 📁 Project Structure

```text
.
├── main.py
├── config.py
├── storage.py
├── requirements.txt
├── Dockerfile
├── .env.example
├── tests/
├── data/
└── discord-main/
```

> The repository may contain additional command/data modules and project files. The structure above highlights the main runtime and deployment files.

## ⚙️ Environment Variables

The bot reads configuration from environment variables.

### Required

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
```

### Optional

```env
DEFAULT_VOLUME=0.50
DB_PATH=/app/data/hmb_global.sqlite3
PORT=8080
ASSET_KEY=YOUR_DISCORD_RICH_PRESENCE_ASSET_KEY
```

### YouTube Cookies

For Render, the YouTube cookie file should be mounted as a Secret File:

```text
/etc/secrets/cookies.txt
```

The application prepares a writable runtime copy under `/tmp` before passing the cookie file to `yt-dlp`. This is important because Render Secret Files are read-only.

**Never commit Discord tokens, YouTube cookies, or other secrets to GitHub.**

## 🐳 Docker

Build:

```bash
docker build -t hmb-global .
```

Run:

```bash
docker run --rm \
  -e DISCORD_TOKEN="YOUR_TOKEN" \
  -p 8080:8080 \
  hmb-global
```

The container includes:

- Python
- FFmpeg
- Deno
- yt-dlp
- Discord voice dependencies
- Flask/Waitress health server

## ☁️ Render Deployment

HMB GLOBAL can run as a Render Web Service using the repository Dockerfile.

Recommended configuration:

1. Create a **Web Service**.
2. Connect the repository.
3. Select the `main` branch.
4. Use **Docker**.
5. Add the `DISCORD_TOKEN` environment variable.
6. Add the YouTube cookie file as a Render Secret File:
   ```text
   /etc/secrets/cookies.txt
   ```
7. Set the Render health check path to:
   ```text
   /healthz
   ```

The application listens on the `PORT` environment variable and binds the health server to `0.0.0.0`.

## ❤️ Health Check

The bot exposes:

```text
GET /healthz
```

This endpoint is intended for service monitoring systems such as UptimeRobot and Render health checks.

Example:

```text
https://YOUR-RENDER-DOMAIN/healthz
```

## ⚠️ YouTube Rate Limits

YouTube can return:

```text
HTTP Error 429: Too Many Requests
```

This is a YouTube rate-limit response and is separate from the Discord bot or Render health service.

Fresh cookies can help with expired authentication/session problems, but cookies do not guarantee that a hosting-provider IP will avoid YouTube rate limits.

Avoid aggressive repeated retries when YouTube is returning 429 responses.

## 💾 Storage

The project uses SQLite for bot data.

The default database path is:

```text
/app/data/hmb_global.sqlite3
```

On ephemeral hosting environments, local SQLite data may be lost after a restart, redeploy, or instance replacement. For long-term persistent production data, use a persistent storage/database solution.

## 🔐 Security

- Keep `DISCORD_TOKEN` private.
- Never upload `cookies.txt` to GitHub.
- Never paste tokens or cookie contents into public issues.
- Use environment variables or platform Secret Files for sensitive configuration.
- Rotate credentials if they are accidentally exposed.

## 🧪 Testing

Project tests can be run with:

```bash
pytest -q
```

## 🛠️ Local Development

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Make sure FFmpeg is installed and available in `PATH`.

Then configure your environment:

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Start the bot:

```bash
python main.py
```

The health endpoint will be available on the configured `PORT`.

## 📌 Current Production Setup

HMB GLOBAL is designed to run as:

```text
Discord
   │
   ▼
HMB GLOBAL
   │
   ├── discord.py
   ├── yt-dlp
   ├── Deno
   ├── FFmpeg
   ├── SQLite
   └── Flask + Waitress
          │
          ▼
       /healthz
          │
          ▼
      UptimeRobot
```

## 📄 License

Add the project's preferred license here before publishing the repository publicly.

---

### HMB GLOBAL

**Professional Discord Music Bot**

Built for stable Discord voice playback, music management, and production deployment.
