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
        self.queues = {}
        self.custom_voice_clients = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced successfully!")

bot = MusicBot()

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
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await asyncio.sleep(5)
        if guild_id in bot.queues and len(bot.queues[guild_id]) == 0:
            vc = bot.custom_voice_clients.get(guild_id)
            if vc and vc.is_connected():
                await vc.disconnect()
        return

    song = bot.queues[guild_id].pop(0)
    vc = bot.custom_voice_clients.get(guild_id)
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
            await interaction.channel.send(f"🎵 **Now Playing:** {song['title']}")
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

    if guild_id not in bot.custom_voice_clients or not bot.custom_voice_clients[guild_id].is_connected():
        try:
            vc = await voice_channel.connect()
            bot.custom_voice_clients[guild_id] = vc
        except Exception as e:
            await interaction.followup.send(f"❌ Could not connect: {str(e)[:100]}")
            return
    else:
        vc = bot.custom_voice_clients[guild_id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)

    song = search_youtube(query)
    if 'error' in song:
        await interaction.followup.send(f"❌ {song['error']}")
        return

    if guild_id not in bot.queues:
        bot.queues[guild_id] = []

    bot.queues[guild_id].append(song)

    if not vc.is_playing():
        await interaction.followup.send(f"✅ **Added to queue:** {song['title']}")
        await play_next_interaction(interaction)
    else:
        position = len(bot.queues[guild_id])
        await interaction.followup.send(f"✅ **Added to queue:** {song['title']} (Position #{position})")

@bot.tree.command(name='skip', description='Skip the current song')
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_playing():
        bot.custom_voice_clients[guild_id].stop()
        await interaction.response.send_message("⏭️ Skipped!")
    else:
        await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)

@bot.tree.command(name='queue', description='Show the current song queue')
async def show_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("📭 Queue is empty.", ephemeral=True)
        return

    msg = "**🎶 Song Queue:**\n"
    for i, song in enumerate(bot.queues[guild_id], 1):
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
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
        if bot.custom_voice_clients[guild_id].is_playing():
            bot.custom_voice_clients[guild_id].stop()
        await bot.custom_voice_clients[guild_id].disconnect()
        bot.custom_voice_clients.pop(guild_id, None)
        bot.queues.pop(guild_id, None)
        await interaction.response.send_message("👋 Disconnected!")
    else:
        await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

@bot.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")


# ============================================================
# CONTROL PANEL - پانێڵی کۆنترۆڵ (View with Buttons)
# ============================================================

class ControlView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.guild_id = interaction.guild.id
        self.message = None

    async def update_embed(self):
        guild_id = self.guild_id
        embed = discord.Embed(
            title="🎛 **Control Panel**",
            color=discord.Color.blurple()
        )

        if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
            vc = bot.custom_voice_clients[guild_id]
            status = "🟢 Playing" if vc.is_playing() else "🟡 Paused" if vc.is_paused() else "⚫ Stopped"
            channel_name = vc.channel.name if vc.channel else "Unknown"

            volume = int(vc.source.volume * 100) if vc.source and hasattr(vc.source, 'volume') else DEFAULT_VOLUME

            embed.add_field(name="📡 Connection", value=f"`{channel_name}`", inline=True)
            embed.add_field(name="🔊 Volume", value=f"`{volume}%`", inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)
        else:
            embed.add_field(name="📡 Status", value="❌ **Not Connected**", inline=False)

        queue_len = len(bot.queues.get(guild_id, []))
        embed.set_footer(text=f"📋 Queue: {queue_len} songs • 🎵 Music Bot")
        return embed

    @discord.ui.button(label="⏸ Pause/Resume", style=discord.ButtonStyle.secondary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.custom_voice_clients:
            await interaction.response.send_message("❌ Not connected!", ephemeral=True)
            return

        vc = bot.custom_voice_clients[guild_id]
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Paused", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing to pause/resume", ephemeral=True)
            return

        embed = await self.update_embed()
        await self.message.edit(embed=embed)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.primary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_playing():
            bot.custom_voice_clients[guild_id].stop()
            await interaction.response.send_message("⏭ Skipped!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
            if bot.custom_voice_clients[guild_id].is_playing():
                bot.custom_voice_clients[guild_id].stop()
            await bot.custom_voice_clients[guild_id].disconnect()
            bot.custom_voice_clients.pop(guild_id, None)
            bot.queues.pop(guild_id, None)

            await interaction.response.send_message("👋 Disconnected!", ephemeral=True)
            await self.message.delete()
            self.stop()
        else:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)

    @discord.ui.button(label="🔊 +10", style=discord.ButtonStyle.success, row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.custom_voice_clients:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)
            return

        vc = bot.custom_voice_clients[guild_id]
        if not vc.source or not hasattr(vc.source, 'volume'):
            await interaction.response.send_message("❌ No audio source", ephemeral=True)
            return

        new_vol = min(vc.source.volume + 0.10, 1.0)
        vc.source.volume = new_vol
        embed = await self.update_embed()
        await self.message.edit(embed=embed)
        await interaction.response.send_message(f"🔊 Volume: **{int(new_vol*100)}%**", ephemeral=True)

    @discord.ui.button(label="🔉 -10", style=discord.ButtonStyle.success, row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.custom_voice_clients:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)
            return

        vc = bot.custom_voice_clients[guild_id]
        if not vc.source or not hasattr(vc.source, 'volume'):
            await interaction.response.send_message("❌ No audio source", ephemeral=True)
            return

        new_vol = max(vc.source.volume - 0.10, 0.0)
        vc.source.volume = new_vol
        embed = await self.update_embed()
        await self.message.edit(embed=embed)
        await interaction.response.send_message(f"🔉 Volume: **{int(new_vol*100)}%**", ephemeral=True)

    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary, row=1)
    async def show_queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
            await interaction.response.send_message("📭 Queue is empty.", ephemeral=True)
            return

        msg = "**🎶 Song Queue:**\n"
        for i, song in enumerate(bot.queues[guild_id], 1):
            duration = song.get('duration', 0)
            minutes, seconds = divmod(duration, 60)
            time_str = f"{minutes}:{seconds:02d}" if duration else "🔴 Live"
            msg += f"`{i}.` **{song['title']}** ({time_str})\n"

        if len(msg) > 2000:
            msg = msg[:1997] + "..."
        await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name='control', description='🎛 Open the music control panel')
async def control(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
        return

    guild_id = interaction.guild.id
    if guild_id not in bot.custom_voice_clients or not bot.custom_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Bot is not connected! Use `/play` first.", ephemeral=True)
        return

    view = ControlView(interaction)
    vc = bot.custom_voice_clients[guild_id]
    volume = int(vc.source.volume * 100) if vc.source and hasattr(vc.source, 'volume') else DEFAULT_VOLUME

    embed = discord.Embed(
        title="🎛 **Control Panel**",
        description=f"**Guild:** `{interaction.guild.name}`\n"
                    f"**Voice Channel:** `{vc.channel.name}`\n"
                    f"**Volume:** `{volume}%`",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"📋 Queue: {len(bot.queues.get(guild_id, []))} songs")

    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

    def disable_buttons():
        for child in view.children:
            child.disabled = True

    view.on_timeout = disable_buttons


if __name__ == "__main__":
    if not TOKEN:
        exit(1)
    bot.run(TOKEN)
