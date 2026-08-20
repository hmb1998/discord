import discord
from discord import app_commands
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

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=BOT_PREFIX, intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced successfully!")

bot = MusicBot()

queues = {}
voice_clients = {}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,
    'default_search': 'ytsearch',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 🎛️ Music Control Panel (Buttons View)
class MusicControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        vc = voice_clients.get(guild_id)
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused music.", ephemeral=True)
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed music.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        if guild_id in voice_clients and voice_clients[guild_id].is_playing():
            voice_clients[guild_id].stop()
            await interaction.response.send_message("⏭️ Skipped current song!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop & Leave", style=discord.ButtonStyle.danger)
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        if guild_id in voice_clients and voice_clients[guild_id].is_connected():
            if voice_clients[guild_id].is_playing():
                voice_clients[guild_id].stop()
            await voice_clients[guild_id].disconnect()
            voice_clients.pop(guild_id, None)
            queues.pop(guild_id, None)
            await interaction.response.send_message("👋 Disconnected and cleared queue!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

def download_from_github(url, dest_dir="downloads"):
    os.makedirs(dest_dir, exist_ok=True)
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
                return f"❌ HTTP {r.status_code}"
            except Exception as e:
                return f"❌ Error: {str(e)[:80]}"
    return "❌ Could not parse GitHub URL."

def search_youtube(query):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            if re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', query):
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
            else:
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

async def play_next_interaction(interaction: discord.Interaction):
    guild_id = interaction.guild.id
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
        coro = play_next_interaction(interaction)
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

        try:
            await interaction.channel.send(f"🎵 **Now Playing:** {song['title']}", view=MusicControlView())
        except:
            pass
    except Exception as e:
        coro = play_next_interaction(interaction)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

@bot.event
async def on_ready():
    print(f'✅ Bot is ready! Logged in as {bot.user}')

@bot.tree.command(name='play', description='Play a song from YouTube')
@app_commands.describe(query='The song name or YouTube URL')
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
        return

    await interaction.response.defer()
    voice_channel = interaction.user.voice.channel
    guild_id = interaction.guild.id

    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        try:
            vc = await voice_channel.connect()
            voice_clients[guild_id] = vc
        except Exception as e:
            await interaction.followup.send(f"❌ Could not connect: {str(e)[:100]}")
            return
    else:
        vc = voice_clients[guild_id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)

    song = search_youtube(query)
    if 'error' in song:
        await interaction.followup.send(f"❌ {song['error']}")
        return

    if guild_id not in queues:
        queues[guild_id] = []

    queues[guild_id].append(song)

    if not vc.is_playing():
        await interaction.followup.send(f"✅ **Added to queue:** {song['title']}")
        await play_next_interaction(interaction)
    else:
        position = len(queues[guild_id])
        await interaction.followup.send(f"✅ **Added to queue:** {song['title']} (Position #{position})")

@bot.tree.command(name='skip', description='Skip the current song')
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].stop()
        await interaction.response.send_message("⏭️ Skipped!")
    else:
        await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)

@bot.tree.command(name='queue', description='Show the current song queue')
async def show_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await interaction.response.send_message("📭 Queue is empty.", ephemeral=True)
        return

    msg = "**🎶 Song Queue:**\n"
    for i, song in enumerate(queues[guild_id], 1):
        duration = song.get('duration', 0)
        minutes, seconds = divmod(duration, 60)
        time_str = f"{minutes}:{seconds:02d}" if duration else "🔴 Live"
        msg += f"`{i}.` **{song['title']}** ({time_str})\n"

    if len(msg) > 2000:
        msg = msg[:1997] + "..."
    await interaction.response.send_message(msg)

@bot.tree.command(name='stop', description='Stop playing and disconnect the bot')
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_connected():
        if voice_clients[guild_id].is_playing():
            voice_clients[guild_id].stop()
        await voice_clients[guild_id].disconnect()
        voice_clients.pop(guild_id, None)
        queues.pop(guild_id, None)
        await interaction.response.send_message("👋 Disconnected!")
    else:
        await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

@bot.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")

if __name__ == "__main__":
    if not TOKEN:
        exit(1)
    bot.run(TOKEN)
