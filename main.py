import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re
import requests
import zipfile
import io
from config import TOKEN, GITHUB_FILES_URL, BOT_PREFIX, DEFAULT_VOLUME

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# Queue structure: {guild_id: [{'url': ..., 'title': ..., 'duration': ..., 'thumbnail': ...}]}
queues = {}
# Voice client references
voice_clients = {}

# FFmpeg options
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# YT-DLP options
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,
    'default_search': 'ytsearch',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def download_from_github(url, dest_dir="downloads"):
    """Download files from a GitHub repository (raw file or full repo)"""
    import requests
    import zipfile
    import io
    import os

    os.makedirs(dest_dir, exist_ok=True)

    # Case 1: Raw file URL (github.com -> raw.githubusercontent.com)
    if "github.com" in url and "/blob/" in url:
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        filename = url.split("/")[-1]
        filepath = os.path.join(dest_dir, filename)

        try:
            r = requests.get(raw_url, timeout=30)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(r.content)
                return f"✅ Downloaded `{filename}` → `{dest_dir}/`"
            return f"❌ HTTP {r.status_code}"
        except Exception as e:
            return f"❌ Error: {str(e)[:80]}"

    # Case 2: Full repo download (as zipball)
    elif "github.com/" in url and ("tree" not in url):
        repo_path = url.replace(".git", "")
        parts = repo_path.split("github.com/")[1].split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/main"

            try:
                r = requests.get(zip_url, timeout=60)
                if r.status_code == 200:
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    z.extractall(dest_dir)
                    extracted = [n for n in z.namelist() if n.endswith('/')][:3]
                    folder_name = extracted[0].split('/')[0] if extracted else repo
                    return f"✅ Repo `{owner}/{repo}` extracted to `{dest_dir}/{folder_name}/`"
                return f"❌ HTTP {r.status_code} (maybe wrong URL or private repo)"
            except Exception as e:
                return f"❌ Error: {str(e)[:80]}"

    return "❌ Could not parse GitHub URL. Use a raw file URL or repo URL."

def search_youtube(query):
    """Search YouTube and return first result info"""
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            if re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', query):
                # Direct URL
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
            else:
                # Search query
                results = ydl.extract_info(f"ytsearch:{query}", download=False)
                if not results or 'entries' not in results or len(results['entries']) == 0:
                    return {'error': 'No results found'}
                info = results['entries'][0]

            return {
                'url': info['webpage_url'],
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'audio_url': info['url']
            }
        except Exception as e:
            return {'error': str(e)[:200]}

async def play_next(ctx):
    """Play the next song in the queue"""
    guild_id = ctx.guild.id

    if guild_id not in queues or len(queues[guild_id]) == 0:
        await asyncio.sleep(5)
        if guild_id in queues and len(queues[guild_id]) == 0:
            vc = voice_clients.get(guild_id)
            if vc and vc.is_connected():
                await vc.disconnect()
        return

    song = queues[guild_id].pop(0)

    vc = voice_clients.get(guild_id)
    if not vc or not vc.is_connected():
        return

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        coro = play_next(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

    try:
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = info['url']

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=after_playing)
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME

        await ctx.send(f"🎵 **Now Playing:** {song['title']}")

    except Exception as e:
        await ctx.send(f"❌ Error playing: {str(e)[:100]}")
        coro = play_next(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

@bot.event
async def on_ready():
    print(f'✅ Bot is ready! Logged in as {bot.user}')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{BOT_PREFIX}play commands"
        )
    )

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query: str):
    """Play a song from YouTube by URL or search query"""
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel first!")
        return

    voice_channel = ctx.author.voice.channel

    # Connect / move to voice channel
    if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
        try:
            vc = await voice_channel.connect()
            voice_clients[ctx.guild.id] = vc
        except Exception as e:
            await ctx.send(f"❌ Could not connect: {str(e)[:100]}")
            return
    else:
        vc = voice_clients[ctx.guild.id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)

    # Search for the song
    await ctx.send(f"🔍 Searching for `{query[:50]}`...")
    song = search_youtube(query)

    if 'error' in song:
        await ctx.send(f"❌ {song['error']}")
        return

    # Initialize queue
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    queues[ctx.guild.id].append(song)

    if not vc.is_playing():
        await play_next(ctx)
        await ctx.send(f"✅ **Added to queue:** {song['title']}")
    else:
        position = len(queues[ctx.guild.id])
        await ctx.send(f"✅ **Added to queue:** {song['title']} (Position #{position})")

@bot.command(name='skip', aliases=['next', 's'])
async def skip(ctx):
    """Skip the current song"""
    guild_id = ctx.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("❌ Nothing is playing right now.")

@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """Show the current song queue"""
    guild_id = ctx.guild.id

    if guild_id not in queues or len(queues[guild_id]) == 0:
        await ctx.send("📭 Queue is empty.")
        return

    msg = "**🎶 Song Queue:**\n"
    for i, song in enumerate(queues[guild_id], 1):
        duration = song.get('duration', 0)
        minutes, seconds = divmod(duration, 60)
        time_str = f"{minutes}:{seconds:02d}" if duration else "🔴 Live"
        msg += f"`{i}.` **{song['title']}** ({time_str})\n"

    if len(msg) > 2000:
        msg = msg[:1997] + "..."

    await ctx.send(msg)

@bot.command(name='stop', aliases=['dc', 'disconnect', 'leave'])
async def stop(ctx):
    """Stop playing and disconnect the bot"""
    guild_id = ctx.guild.id

    if guild_id in voice_clients and voice_clients[guild_id].is_connected():
        if voice_clients[guild_id].is_playing():
            voice_clients[guild_id].stop()
        await voice_clients[guild_id].disconnect()
        voice_clients.pop(guild_id, None)
        queues.pop(guild_id, None)
        await ctx.send("👋 Disconnected!")
    else:
        await ctx.send("❌ I'm not connected to a voice channel.")

@bot.command(name='github_dl', aliases=['gdl', 'gh'])
async def github_download(ctx, url: str):
    """Download files from a GitHub repository"""
    msg = await ctx.send(f"📥 Downloading from GitHub...")
    result = download_from_github(url)
    await msg.edit(content=result)

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

@bot.command(name='helpme', aliases=['h'])
async def help_command(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="🎵 Discord Music Bot Commands",
        description="Prefix: `!`",
        color=discord.Color.blue()
    )
    embed.add_field(name="!play `<URL or search>`", value="Play a song from YouTube", inline=False)
    embed.add_field(name="!skip", value="Skip current song", inline=True)
    embed.add_field(name="!queue", value="Show the song queue", inline=True)
    embed.add_field(name="!stop", value="Disconnect from voice", inline=True)
    embed.add_field(name="!ping", value="Check bot latency", inline=True)
    embed.add_field(name="!github_dl `<URL>`", value="Download from GitHub", inline=False)
    embed.set_footer(text="HackerAI Music Bot | No token in code")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("=" * 50)
        print("❌ ERROR: DISCORD_BOT_TOKEN is not set!")
        print()
        print("👉 Set it on fly.io with:")
        print("   fly secrets set DISCORD_BOT_TOKEN=your_discord_token_here")
        print()
        print("👉 Or locally with:")
        print("   export DISCORD_BOT_TOKEN=your_discord_token_here")
        print("=" * 50)
        exit(1)
    bot.run(TOKEN)
