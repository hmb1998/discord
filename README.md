# 🎵 Discord Music Bot

A Discord music bot that plays audio from YouTube.  
Deployed on **fly.io** — **NO tokens in the code!**

## 🚀 Features

- ✅ Play music from YouTube (URL or search)
- ✅ Song queue system
- ✅ Skip, stop, queue commands
- ✅ Download files from GitHub
- ✅ Low latency ping check
- ✅ Secure token management via fly.io secrets

## 🔧 Setup

### 1. Create a Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a **New Application**
3. Go to **Bot** tab → **Add Bot**
4. Copy the **Token** (you'll need it for fly.io)
5. Enable **Message Content Intent** and **Server Members Intent** under Privileged Gateway Intents

### 2. Invite Bot to Server
- Go to **OAuth2** → **URL Generator**
- Scopes: `bot`, `applications.commands`
- Permissions: `Connect`, `Speak`, `Read Messages`, `Send Messages`, `Use Voice Activity`
- Open the generated URL and invite the bot

### 3. Deploy to fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app
fly launch --from Dockerfile

# Set the Discord token as a SECRET (NOT in any file!)
fly secrets set DISCORD_BOT_TOKEN=MTE5NzA...your_token_here

# Deploy
fly deploy
