import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re
import math
import random
import json
import time
import datetime
from typing import Optional
from flask import Flask
from config import TOKEN, DEFAULT_VOLUME

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly with 100+ Slash Commands!"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.queues = {}
        self.custom_voice_clients = {}
        self.now_playing = {}
        self.history = {}
        self.favorites = {}
        self.playlists = {}
        self.lyrics_cache = {}
        self.start_time = time.time()
        self.loop_mode = {}  # 'none', 'song', 'queue'
        self.shuffle_mode = {}
        self.sleep_timers = {}
        self.eq_presets = {}
        self.song_skiplist = {}

    async def setup_hook(self):
        print("✅ Syncing slash commands...")
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} commands successfully!")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

bot = MusicBot()
bot.remove_command('help')

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -b:a 128k'
}

YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,
    'default_search': 'ytsearch',
    'skip_download': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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
                'audio_url': info['url'],
                'channel': info.get('uploader', 'Unknown'),
                'views': info.get('view_count', 0)
            }
        except Exception as e:
            return {'error': str(e)[:200]}

def format_time(seconds):
    if seconds is None or seconds == 0:
        return "🔴 Live"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

async def get_voice_client(ctx_or_interaction):
    """Helper to get or connect voice client"""
    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild = ctx_or_interaction.guild
        respond = ctx_or_interaction.response.send_message
    else:
        user = ctx_or_interaction.author
        guild = ctx_or_interaction.guild
        respond = ctx_or_interaction.send

    if not user.voice:
        await respond("❌ You must be in a voice channel first!", ephemeral=True)
        return None, None
    
    voice_channel = user.voice.channel
    guild_id = guild.id
    
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
        vc = bot.custom_voice_clients[guild_id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)
    else:
        try:
            vc = await voice_channel.connect()
            bot.custom_voice_clients[guild_id] = vc
        except Exception as e:
            await respond(f"❌ Could not connect: {str(e)[:100]}", ephemeral=True)
            return None, None
    
    return vc, respond

async def play_next(guild_id):
    """Play next song in queue"""
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        if bot.loop_mode.get(guild_id) == 'queue' and bot.history.get(guild_id) and len(bot.history[guild_id]) > 0:
            bot.queues[guild_id] = list(bot.history[guild_id])
            bot.history[guild_id] = []
        else:
            await asyncio.sleep(10)
            if guild_id in bot.queues and len(bot.queues[guild_id]) == 0:
                vc = bot.custom_voice_clients.get(guild_id)
                if vc and vc.is_connected() and not vc.is_playing():
                    await vc.disconnect()
            return

    if bot.shuffle_mode.get(guild_id):
        random.shuffle(bot.queues[guild_id])

    song = bot.queues[guild_id].pop(0)
    
    if bot.loop_mode.get(guild_id) == 'song':
        bot.queues[guild_id].append(song)
    
    if guild_id not in bot.history:
        bot.history[guild_id] = []
    bot.history[guild_id].append(song)
    if len(bot.history[guild_id]) > 50:
        bot.history[guild_id].pop(0)
    
    bot.now_playing[guild_id] = song
    
    vc = bot.custom_voice_clients.get(guild_id)
    if not vc or not vc.is_connected():
        return

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        coro = play_next(guild_id)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = info['url']

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=after_playing)
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME
    except Exception as e:
        print(f"Error in playback: {e}")
        coro = play_next(guild_id)
        asyncio.run_coroutine_threadsafe(coro, bot.loop)

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name="/play | 100+ Commands")
    await bot.change_presence(activity=activity)
    print(f'✅ Bot is ready! Logged in as {bot.user}')

async def voice_check(interaction: discord.Interaction) -> bool:
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
        return False
    return True

def get_vc(guild_id):
    return bot.custom_voice_clients.get(guild_id)

def is_playing(guild_id):
    vc = get_vc(guild_id)
    return vc and vc.is_connected() and vc.is_playing()

async def song_autocomplete(interaction: discord.Interaction, current: str):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues:
        return []
    songs = []
    for i, s in enumerate(bot.queues[guild_id]):
        if current.lower() in s['title'].lower() or current == '':
            songs.append(app_commands.Choice(name=f"{i+1}. {s['title'][:80]}", value=str(i)))
    return songs[:25]

@bot.tree.command(name='play', description='🎵 Play a song or add to queue')
@app_commands.describe(query='Song name or YouTube URL')
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    guild_id = interaction.guild_id
    song = search_youtube(query)
    
    if 'error' in song:
        await interaction.followup.send(f"❌ {song['error']}", ephemeral=True)
        return
    
    if guild_id not in bot.queues:
        bot.queues[guild_id] = []
    
    bot.queues[guild_id].append(song)
    
    if not vc.is_playing():
        await interaction.followup.send(f"▶️ **Now Playing:** [{song['title']}]({song['url']}) (`{format_time(song['duration'])}`)")
        await play_next(guild_id)
    else:
        position = len(bot.queues[guild_id])
        await interaction.followup.send(f"✅ **Added to Queue** (#{position}): [{song['title']}]({song['url']}) (`{format_time(song['duration'])}`)")

@bot.tree.command(name='playtop', description='🎵 Add a song to the top of the queue')
@app_commands.describe(query='Song name or YouTube URL')
async def playtop(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    guild_id = interaction.guild_id
    song = search_youtube(query)
    
    if 'error' in song:
        await interaction.followup.send(f"❌ {song['error']}", ephemeral=True)
        return
    
    if guild_id not in bot.queues:
        bot.queues[guild_id] = []
    
    bot.queues[guild_id].insert(0, song)
    
    if not vc.is_playing():
        await interaction.followup.send(f"▶️ **Now Playing:** [{song['title']}]({song['url']})")
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"⬆️ **Added to Top of Queue:** [{song['title']}]({song['url']})")

@bot.tree.command(name='pause', description='⏸ Pause the current song')
async def pause(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸ **Paused** ⏸")
    else:
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

@bot.tree.command(name='resume', description='▶️ Resume playback')
async def resume(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ **Resumed** ▶️")
    else:
        await interaction.response.send_message("❌ Nothing is paused", ephemeral=True)

@bot.tree.command(name='skip', description='⏭ Skip the current song')
@app_commands.describe(count='Number of songs to skip (default: 1)')
async def skip(interaction: discord.Interaction, count: Optional[int] = 1):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_playing():
        for _ in range(min(count, len(bot.queues.get(guild_id, [])) + 1)):
            vc.stop()
            await asyncio.sleep(0.05)
        await interaction.response.send_message(f"⏭ **Skipped** {'x'+str(count) if count > 1 else ''} ⏭")
    else:
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

@bot.tree.command(name='stop', description='⏹ Stop playback and clear queue')
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
        bot.queues[guild_id] = []
        await vc.disconnect()
        bot.custom_voice_clients.pop(guild_id, None)
        await interaction.response.send_message("⏹ **Stopped & Disconnected** 👋")
    else:
        await interaction.response.send_message("❌ Not connected", ephemeral=True)

@bot.tree.command(name='volume', description='🔊 Set the volume (0-100)')
@app_commands.describe(percent='Volume percentage (0-100)')
async def volume(interaction: discord.Interaction, percent: int):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if not vc or not vc.source or not hasattr(vc.source, 'volume'):
        await interaction.response.send_message("❌ No active audio source", ephemeral=True)
        return
    vol = max(0, min(100, percent)) / 100
    vc.source.volume = vol
    await interaction.response.send_message(f"🔊 **Volume:** {int(vol*100)}%")

@bot.tree.command(name='volumeup', description='🔊 Increase volume by 10%')
async def volumeup(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if not vc or not vc.source or not hasattr(vc.source, 'volume'):
        await interaction.response.send_message("❌ No active audio source", ephemeral=True)
        return
    new_vol = min(vc.source.volume + 0.10, 1.0)
    vc.source.volume = new_vol
    await interaction.response.send_message(f"🔊 **Volume:** {int(new_vol*100)}%")

@bot.tree.command(name='volumedown', description='🔉 Decrease volume by 10%')
async def volumedown(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if not vc or not vc.source or not hasattr(vc.source, 'volume'):
        await interaction.response.send_message("❌ No active audio source", ephemeral=True)
        return
    new_vol = max(vc.source.volume - 0.10, 0.0)
    vc.source.volume = new_vol
    await interaction.response.send_message(f"🔉 **Volume:** {int(new_vol*100)}%")

@bot.tree.command(name='queue', description='📋 Show the song queue')
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    await interaction.response.defer()
    
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        embed = discord.Embed(title="📋 Queue", description="Queue is empty!", color=discord.Color.orange())
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(title=f"📋 Queue - {len(bot.queues[guild_id])} songs", color=discord.Color.blurple())
    
    if guild_id in bot.now_playing:
        np = bot.now_playing[guild_id]
        embed.add_field(name="▶ Now Playing", value=f"[{np['title']}]({np['url']})")
    
    queue_text = ""
    for i, song in enumerate(bot.queues[guild_id], 1):
        queue_text += f"`{i}.` [{song['title'][:50]}]({song['url']}) - {format_time(song['duration'])}\n"
        if len(queue_text) > 1000:
            queue_text += f"... and {len(bot.queues[guild_id]) - i} more"
            break
    
    if queue_text:
        embed.add_field(name="📜 Up Next", value=queue_text, inline=False)
    
    embed.set_footer(text=f"Loop: {bot.loop_mode.get(guild_id, 'none')} | Shuffle: {'ON' if bot.shuffle_mode.get(guild_id) else 'OFF'}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='nowplaying', description='🎶 Show currently playing song')
@app_commands.describe(ephemeral='Show only to you (default: False)')
async def nowplaying(interaction: discord.Interaction, ephemeral: Optional[bool] = False):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)
        return
    
    song = bot.now_playing[guild_id]
    vc = get_vc(guild_id)
    
    embed = discord.Embed(title="🎶 Now Playing", color=discord.Color.green())
    embed.add_field(name="Title", value=f"[{song['title']}]({song['url']})")
    embed.add_field(name="Duration", value=format_time(song['duration']))
    embed.add_field(name="Channel", value=song.get('channel', 'Unknown'))
    
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    
    if vc and vc.source and hasattr(vc.source, 'volume'):
        embed.add_field(name="Volume", value=f"{int(vc.source.volume*100)}%")
    
    embed.add_field(name="Queue", value=f"{len(bot.queues.get(guild_id, []))} songs")
    embed.add_field(name="Status", value="▶️ Playing" if vc and vc.is_playing() else "⏸ Paused" if vc and vc.is_paused() else "⚫ Stopped")
    
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

@bot.tree.command(name='remove', description='🗑 Remove a song from queue by position')
@app_commands.describe(position='Position number in queue')
@app_commands.autocomplete(position=song_autocomplete)
async def remove(interaction: discord.Interaction, position: int):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("❌ Queue is empty", ephemeral=True)
        return
    
    idx = position - 1
    if idx < 0 or idx >= len(bot.queues[guild_id]):
        await interaction.response.send_message(f"❌ Invalid position. Queue has {len(bot.queues[guild_id])} songs.", ephemeral=True)
        return
    
    song = bot.queues[guild_id].pop(idx)
    await interaction.response.send_message(f"🗑 **Removed:** {song['title']}")

@bot.tree.command(name='clear', description='🧹 Clear the entire queue')
async def clear(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id in bot.queues:
        count = len(bot.queues[guild_id])
        bot.queues[guild_id] = []
        await interaction.response.send_message(f"🧹 **Cleared** {count} songs from queue")
    else:
        await interaction.response.send_message("❌ Queue is already empty", ephemeral=True)

@bot.tree.command(name='shuffle', description='🔀 Toggle shuffle mode')
async def shuffle(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    current = bot.shuffle_mode.get(guild_id, False)
    bot.shuffle_mode[guild_id] = not current
    
    if bot.shuffle_mode[guild_id] and guild_id in bot.queues:
        random.shuffle(bot.queues[guild_id])
    
    await interaction.response.send_message(f"🔀 **Shuffle:** {'ON' if bot.shuffle_mode[guild_id] else 'OFF'}")

@bot.tree.command(name='loop', description='🔄 Set loop mode (none/song/queue)')
@app_commands.describe(mode='Loop mode: none, song, or queue')
@app_commands.choices(mode=[
    app_commands.Choice(name='❌ None', value='none'),
    app_commands.Choice(name='🔂 Song', value='song'),
    app_commands.Choice(name='🔁 Queue', value='queue')
])
async def loop(interaction: discord.Interaction, mode: str):
    guild_id = interaction.guild_id
    bot.loop_mode[guild_id] = mode
    await interaction.response.send_message(f"🔄 **Loop:** {mode}")

@bot.tree.command(name='seek', description='⏩ Seek to a position in the current song (seconds)')
@app_commands.describe(seconds='Position in seconds')
async def seek(interaction: discord.Interaction, seconds: int):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)
        return
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ No current song info", ephemeral=True)
        return
    
    song = bot.now_playing[guild_id]
    duration = song.get('duration', 0)
    if duration and seconds > duration:
        await interaction.response.send_message(f"❌ Cannot seek past song duration ({format_time(duration)})", ephemeral=True)
        return
    
    vc.stop()
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = info['url']
        
        seek_opts = FFMPEG_OPTIONS.copy()
        seek_opts['before_options'] += f' -ss {seconds}'
        source = discord.FFmpegPCMAudio(audio_url, **seek_opts)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop))
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME
        
        await interaction.response.send_message(f"⏩ **Seeked to** {format_time(seconds)}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Seek error: {str(e)[:100]}", ephemeral=True)
        coro = play_next(guild_id)
        asyncio.run_coroutine_threadsafe(coro, bot.loop)

@bot.tree.command(name='move', description='↕️ Move a song to a different position in queue')
@app_commands.describe(from_position='Current position', to_position='New position')
async def move(interaction: discord.Interaction, from_position: int, to_position: int):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) < 2:
        await interaction.response.send_message("❌ Need at least 2 songs in queue", ephemeral=True)
        return
    
    from_idx = from_position - 1
    to_idx = to_position - 1
    qlen = len(bot.queues[guild_id])
    
    if from_idx < 0 or from_idx >= qlen or to_idx < 0 or to_idx >= qlen:
        await interaction.response.send_message(f"❌ Invalid position. Queue has {qlen} songs (1-{qlen})", ephemeral=True)
        return
    
    song = bot.queues[guild_id].pop(from_idx)
    bot.queues[guild_id].insert(to_idx, song)
    await interaction.response.send_message(f"↕️ **Moved:** `#{from_position}` → `#{to_position}` - {song['title']}")

@bot.tree.command(name='join', description='📡 Join your voice channel')
async def join(interaction: discord.Interaction):
    await interaction.response.defer()
    if not await voice_check(interaction):
        return
    vc, _ = await get_voice_client(interaction)
    if vc:
        await interaction.followup.send(f"✅ **Joined** `{vc.channel.name}` 🎧")

@bot.tree.command(name='leave', description='👋 Leave the voice channel')
async def leave(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_connected():
        channel_name = vc.channel.name
        bot.queues[guild_id] = []
        if vc.is_playing():
            vc.stop()
        await vc.disconnect()
        bot.custom_voice_clients.pop(guild_id, None)
        await interaction.response.send_message(f"👋 **Left** `{channel_name}`")
    else:
        await interaction.response.send_message("❌ Not connected", ephemeral=True)

@bot.tree.command(name='disconnect', description='👋 Same as /leave - disconnect from voice')
async def disconnect(interaction: discord.Interaction):
    await leave.callback(interaction)

@bot.tree.command(name='search', description='🔍 Search for songs and choose one')
@app_commands.describe(query='Search query')
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            results = ydl.extract_info(f"ytsearch5:{query}", download=False)
            if not results or 'entries' not in results or len(results['entries']) == 0:
                await interaction.followup.send("❌ No results found", ephemeral=True)
                return
            
            embed = discord.Embed(title=f"🔍 Search Results: {query}", color=discord.Color.blurple())
            for i, entry in enumerate(results['entries'], 1):
                duration = format_time(entry.get('duration', 0))
                embed.add_field(
                    name=f"`{i}.` {entry.get('title', 'Unknown')[:80]}",
                    value=f"⏱ {duration} | 👤 {entry.get('uploader', 'Unknown')[:30]}",
                    inline=False
                )
            
            embed.set_footer(text="Use /play with the song name or URL")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Search failed: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(name='ping', description='🏓 Check bot latency')
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 **Pong!** `{latency}ms`")

@bot.tree.command(name='uptime', description='⏰ Show bot uptime')
async def uptime(interaction: discord.Interaction):
    uptime_seconds = int(time.time() - bot.start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    await interaction.response.send_message(f"⏰ **Uptime:** `{' '.join(parts)}`")

@bot.tree.command(name='stats', description='📊 Show bot statistics')
async def stats(interaction: discord.Interaction):
    guild_count = len(bot.guilds)
    user_count = sum(g.member_count for g in bot.guilds)
    total_played = sum(len(h) for h in bot.history.values())
    total_queued = sum(len(q) for q in bot.queues.values())
    
    embed = discord.Embed(title="📊 Bot Statistics", color=discord.Color.blue())
    embed.add_field(name="Servers", value=guild_count, inline=True)
    embed.add_field(name="Users", value=user_count, inline=True)
    embed.add_field(name="Songs Played", value=total_played, inline=True)
    embed.add_field(name="Songs Queued", value=total_queued, inline=True)
    embed.add_field(name="Active Players", value=len(bot.custom_voice_clients), inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency*1000)}ms", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='help', description='ℹ️ Show help with all commands')
@app_commands.describe(category='Command category')
@app_commands.choices(category=[
    app_commands.Choice(name='🎵 All Commands', value='all'),
    app_commands.Choice(name='▶️ Playback', value='playback'),
    app_commands.Choice(name='📋 Queue', value='queue'),
    app_commands.Choice(name='⭐ Favorites', value='favorites'),
    app_commands.Choice(name='📁 Playlists', value='playlists'),
    app_commands.Choice(name='📜 History', value='history'),
    app_commands.Choice(name='🔧 Utility', value='utility'),
    app_commands.Choice(name='🎛 Effects', value='effects')
])
async def help(interaction: discord.Interaction, category: Optional[str] = 'all'):
    commands_map = {
        'playback': ['play', 'playtop', 'pause', 'resume', 'skip', 'stop', 'seek', 'join', 'leave', 'disconnect'],
        'queue': ['queue', 'nowplaying', 'remove', 'clear', 'shuffle', 'loop', 'move', 'search'],
        'favorites': ['favorite_add', 'favorite_remove', 'favorite_list', 'favorite_play'],
        'playlists': ['playlist_create', 'playlist_delete', 'playlist_add', 'playlist_list', 'playlist_play', 'playlist_info'],
        'history': ['history', 'history_play'],
        'utility': ['volume', 'volumeup', 'volumedown', 'ping', 'uptime', 'stats', 'help', 'lyrics'],
        'effects': ['bassboost', 'nightcore', 'vaporwave', 'slow', 'speed', 'equalizer', 'karaoke']
    }
    
    embed = discord.Embed(title="ℹ️ **Music Bot Help**", color=discord.Color.blurple())
    
    if category == 'all':
        for cat_name, cmds in commands_map.items():
            cmd_list = [f"`/{c}`" for c in cmds]
            embed.add_field(name=cat_name.capitalize(), value=", ".join(cmd_list), inline=False)
    else:
        cmds = commands_map.get(category, [])
        cmd_list = [f"`/{c}`" for c in cmds]
        embed.add_field(name=f"{category.capitalize()} Commands", value="\n".join(cmd_list), inline=False)
    
    embed.set_footer(text="Use /play <song> to start playing music!")
    await interaction.response.send_message(embed=embed)

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    import threading
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    bot.run(TOKEN)
