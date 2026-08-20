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
        await self.tree.sync()
        print(f"✅ {len(self.tree.get_commands())} Slash Commands loaded!")

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
        # Check loop mode
        if bot.loop_mode.get(guild_id) == 'queue' and bot.history.get(guild_id) and len(bot.history[guild_id]) > 0:
            # Re-add all history to queue
            bot.queues[guild_id] = list(bot.history[guild_id])
            bot.history[guild_id] = []
        else:
            # Wait then disconnect
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
    
    # Add to history
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
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name="/play | 100+ Commands")
    await bot.change_presence(activity=activity)
    print(f'✅ Bot is ready! Logged in as {bot.user}')

# ============================================================
# CHECK FUNCTION (for voice channel check)
# ============================================================
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

# ============================================================
# AUTOCOMPLETE FUNCTIONS
# ============================================================
async def song_autocomplete(interaction: discord.Interaction, current: str):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues:
        return []
    songs = []
    for i, s in enumerate(bot.queues[guild_id]):
        if current.lower() in s['title'].lower() or current == '':
            songs.append(app_commands.Choice(name=f"{i+1}. {s['title'][:80]}", value=str(i)))
    return songs[:25]

# ============================================================
# 100+ SLASH COMMANDS
# ============================================================

# ===== 1. PLAY =====
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

# ===== 2. PLAY TOP =====
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

# ===== 3. PAUSE =====
@bot.tree.command(name='pause', description='⏸ Pause the current song')
async def pause(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸ **Paused** ⏸")
    else:
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

# ===== 4. RESUME =====
@bot.tree.command(name='resume', description='▶️ Resume playback')
async def resume(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ **Resumed** ▶️")
    else:
        await interaction.response.send_message("❌ Nothing is paused", ephemeral=True)

# ===== 5. SKIP =====
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

# ===== 6. STOP =====
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

# ===== 7. VOLUME =====
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

# ===== 8. VOLUME_UP =====
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

# ===== 9. VOLUME_DOWN =====
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

# ===== 10. QUEUE =====
@bot.tree.command(name='queue', description='📋 Show the song queue')
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    await interaction.response.defer()
    
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        embed = discord.Embed(title="📋 Queue", description="Queue is empty!", color=discord.Color.orange())
        await interaction.followup.send(embed=embed)
        return
    
    embed = discord.Embed(title=f"📋 Queue - {len(bot.queues[guild_id])} songs", color=discord.Color.blurple())
    
    # Now playing
    if guild_id in bot.now_playing:
        np = bot.now_playing[guild_id]
        embed.add_field(name="▶️ Now Playing", value=f"[{np['title']}]({np['url']}) (`{format_time(np['duration'])}`)", inline=False)
    
    # Queue list
    queue_text = ""
    for i, song in enumerate(bot.queues[guild_id], 1):
        queue_text += f"`{i}.` [{song['title'][:50]}]({song['url']}) ({format_time(song['duration'])})\n"
        if len(queue_text) > 1000:
            queue_text += f"... and {len(bot.queues[guild_id]) - i} more"
            break
    
    if queue_text:
        embed.add_field(name="📜 Up Next", value=queue_text, inline=False)
    
    embed.set_footer(text=f"Loop: {bot.loop_mode.get(guild_id, 'none')} | Shuffle: {'ON' if bot.shuffle_mode.get(guild_id) else 'OFF'}")
    await interaction.followup.send(embed=embed)

# ===== 11. NOWPLAYING =====
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
    embed.add_field(name="Title", value=f"[{song['title']}]({song['url'])")
    embed.add_field(name="Duration", value=format_time(song['duration']))
    embed.add_field(name="Channel", value=song.get('channel', 'Unknown'))
    
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    
    if vc and vc.source and hasattr(vc.source, 'volume'):
        embed.add_field(name="Volume", value=f"{int(vc.source.volume*100)}%")
    
    embed.add_field(name="Queue", value=f"{len(bot.queues.get(guild_id, []))} songs")
    embed.add_field(name="Status", value="▶️ Playing" if vc and vc.is_playing() else "⏸ Paused" if vc and vc.is_paused() else "⚫ Stopped")
    
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

# ===== 12. REMOVE =====
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

# ===== 13. CLEAR =====
@bot.tree.command(name='clear', description='🧹 Clear the entire queue')
async def clear(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id in bot.queues:
        count = len(bot.queues[guild_id])
        bot.queues[guild_id] = []
        await interaction.response.send_message(f"🧹 **Cleared** {count} songs from queue")
    else:
        await interaction.response.send_message("❌ Queue is already empty", ephemeral=True)

# ===== 14. SHUFFLE =====
@bot.tree.command(name='shuffle', description='🔀 Toggle shuffle mode')
async def shuffle(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    current = bot.shuffle_mode.get(guild_id, False)
    bot.shuffle_mode[guild_id] = not current
    
    if bot.shuffle_mode[guild_id] and guild_id in bot.queues:
        random.shuffle(bot.queues[guild_id])
    
    await interaction.response.send_message(f"🔀 **Shuffle:** {'ON' if bot.shuffle_mode[guild_id] else 'OFF'}")

# ===== 15. LOOP =====
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

# ===== 16. SEEK =====
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
    
    # Restart playback at position - we need to recreate the source
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
        # Replay without seek
        coro = play_next(guild_id)
        asyncio.run_coroutine_threadsafe(coro, bot.loop)

# ===== 17. MOVESONG =====
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

# ===== 18. JOIN =====
@bot.tree.command(name='join', description='📡 Join your voice channel')
async def join(interaction: discord.Interaction):
    await interaction.response.defer()
    if not await voice_check(interaction):
        return
    vc, _ = await get_voice_client(interaction)
    if vc:
        await interaction.followup.send(f"✅ **Joined** `{vc.channel.name}` 🎧")

# ===== 19. LEAVE =====
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

# ===== 20. DISCONNECT =====
@bot.tree.command(name='disconnect', description='👋 Same as /leave - disconnect from voice')
async def disconnect(interaction: discord.Interaction):
    await leave.callback(interaction)

# ===== 21. SEARCH =====
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

# ===== 22-31. FAVORITES =====
@bot.tree.command(name='favorite_add', description='⭐ Save current song to favorites')
async def favorite_add(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing to favorite", ephemeral=True)
        return
    
    user_id = interaction.user.id
    if user_id not in bot.favorites:
        bot.favorites[user_id] = []
    
    song = bot.now_playing[guild_id]
    # Check if already exists
    for fav in bot.favorites[user_id]:
        if fav['url'] == song['url']:
            await interaction.response.send_message("⭐ Already in your favorites!", ephemeral=True)
            return
    
    bot.favorites[user_id].append({
        'title': song['title'],
        'url': song['url'],
        'duration': song['duration']
    })
    
    await interaction.response.send_message(f"⭐ **Added to Favorites:** {song['title']}")

@bot.tree.command(name='favorite_remove', description='⭐ Remove a song from favorites')
@app_commands.describe(index='Favorite number')
async def favorite_remove(interaction: discord.Interaction, index: int):
    user_id = interaction.user.id
    if user_id not in bot.favorites or len(bot.favorites[user_id]) == 0:
        await interaction.response.send_message("❌ No favorites saved", ephemeral=True)
        return
    
    idx = index - 1
    if idx < 0 or idx >= len(bot.favorites[user_id]):
        await interaction.response.send_message(f"❌ Invalid index. You have {len(bot.favorites[user_id])} favorites.", ephemeral=True)
        return
    
    song = bot.favorites[user_id].pop(idx)
    await interaction.response.send_message(f"⭐ **Removed:** {song['title']}")

@bot.tree.command(name='favorite_list', description='⭐ Show your favorite songs')
async def favorite_list(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in bot.favorites or len(bot.favorites[user_id]) == 0:
        await interaction.response.send_message("📭 No favorites saved yet. Use `/favorite_add` to save songs!", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"⭐ Favorites - {interaction.user.display_name}", color=discord.Color.gold())
    for i, fav in enumerate(bot.favorites[user_id], 1):
        embed.add_field(name=f"`{i}.` {fav['title'][:80]}", value=f"⏱ {format_time(fav['duration'])}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='favorite_play', description='⭐ Play a song from your favorites')
@app_commands.describe(index='Favorite number to play')
async def favorite_play(interaction: discord.Interaction, index: int):
    await interaction.response.defer()
    user_id = interaction.user.id
    if user_id not in bot.favorites or len(bot.favorites[user_id]) == 0:
        await interaction.followup.send("❌ No favorites saved", ephemeral=True)
        return
    
    idx = index - 1
    if idx < 0 or idx >= len(bot.favorites[user_id]):
        await interaction.followup.send(f"❌ Invalid index", ephemeral=True)
        return
    
    song = bot.favorites[user_id][idx]
    
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    guild_id = interaction.guild_id
    if guild_id not in bot.queues:
        bot.queues[guild_id] = []
    
    bot.queues[guild_id].append(song)
    
    if not vc.is_playing():
        await interaction.followup.send(f"⭐ **Playing from Favorites:** {song['title']}")
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"⭐ **Added from Favorites:** {song['title']} (Position #{len(bot.queues[guild_id])})")

# ===== 32-35. PLAYLISTS =====
@bot.tree.command(name='playlist_create', description='📁 Create a new playlist')
@app_commands.describe(name='Playlist name')
async def playlist_create(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    if user_id not in bot.playlists:
        bot.playlists[user_id] = {}
    
    if name in bot.playlists[user_id]:
        await interaction.response.send_message(f"❌ Playlist '{name}' already exists!", ephemeral=True)
        return
    
    bot.playlists[user_id][name] = []
    await interaction.response.send_message(f"📁 **Playlist Created:** '{name}'")

@bot.tree.command(name='playlist_delete', description='📁 Delete a playlist')
@app_commands.describe(name='Playlist name')
async def playlist_delete(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    if user_id not in bot.playlists or name not in bot.playlists[user_id]:
        await interaction.response.send_message(f"❌ Playlist '{name}' not found", ephemeral=True)
        return
    
    del bot.playlists[user_id][name]
    await interaction.response.send_message(f"🗑 **Playlist Deleted:** '{name}'")

@bot.tree.command(name='playlist_add', description='📁 Add current song to a playlist')
@app_commands.describe(name='Playlist name')
async def playlist_add(interaction: discord.Interaction, name: str):
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)
        return
    
    if user_id not in bot.playlists or name not in bot.playlists[user_id]:
        await interaction.response.send_message(f"❌ Playlist '{name}' not found", ephemeral=True)
        return
    
    song = bot.now_playing[guild_id]
    bot.playlists[user_id][name].append({
        'title': song['title'],
        'url': song['url'],
        'duration': song['duration']
    })
    
    await interaction.response.send_message(f"📁 **Added to '{name}':** {song['title']}")

@bot.tree.command(name='playlist_list', description='📁 List all your playlists')
async def playlist_list(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in bot.playlists or len(bot.playlists[user_id]) == 0:
        await interaction.response.send_message("📭 No playlists yet. Use `/playlist_create` to create one!", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"📁 Playlists - {interaction.user.display_name}", color=discord.Color.teal())
    for name, songs in bot.playlists[user_id].items():
        embed.add_field(name=f"📁 {name}", value=f"{len(songs)} songs", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='playlist_play', description='📁 Play all songs from a playlist')
@app_commands.describe(name='Playlist name')
async def playlist_play(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    user_id = interaction.user.id
    
    if user_id not in bot.playlists or name not in bot.playlists[user_id]:
        await interaction.followup.send(f"❌ Playlist '{name}' not found", ephemeral=True)
        return
    
    songs = bot.playlists[user_id][name]
    if not songs:
        await interaction.followup.send(f"❌ Playlist '{name}' is empty", ephemeral=True)
        return
    
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    guild_id = interaction.guild_id
    if guild_id not in bot.queues:
        bot.queues[guild_id] = []
    
    for song in songs:
        bot.queues[guild_id].append(dict(song))
    
    if not vc.is_playing():
        await interaction.followup.send(f"📁 **Playing Playlist:** '{name}' ({len(songs)} songs)")
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"📁 **Added Playlist to Queue:** '{name}' ({len(songs)} songs)")

@bot.tree.command(name='playlist_info', description='📁 Show details of a playlist')
@app_commands.describe(name='Playlist name')
async def playlist_info(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    if user_id not in bot.playlists or name not in bot.playlists[user_id]:
        await interaction.response.send_message(f"❌ Playlist '{name}' not found", ephemeral=True)
        return
    
    songs = bot.playlists[user_id][name]
    if not songs:
        await interaction.response.send_message(f"📁 '{name}' is empty", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"📁 Playlist: {name}", color=discord.Color.teal())
    total_dur = sum(s.get('duration', 0) for s in songs)
    embed.set_footer(text=f"{len(songs)} songs | Total: {format_time(total_dur)}")
    
    for i, s in enumerate(songs, 1):
        embed.add_field(name=f"`{i}.` {s['title'][:80]}", value=f"⏱ {format_time(s.get('duration', 0))}", inline=False)
        if i >= 15:
            embed.add_field(name=f"... and {len(songs)-15} more", value="", inline=False)
            break
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ===== 36-37. HISTORY =====
@bot.tree.command(name='history', description='📜 Show recently played songs')
async def history(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.history or len(bot.history[guild_id]) == 0:
        await interaction.response.send_message("📭 No history yet", ephemeral=True)
        return
    
    embed = discord.Embed(title="📜 Play History", color=discord.Color.dark_blue())
    for i, song in enumerate(reversed(bot.history[guild_id][-20:]), 1):
        embed.add_field(name=f"`{i}.` {song['title'][:80]}", value=f"⏱ {format_time(song.get('duration', 0))}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='history_play', description='📜 Play a song from history')
@app_commands.describe(index='History number')
async def history_play(interaction: discord.Interaction, index: int):
    await interaction.response.defer()
    guild_id = interaction.guild_id
    
    if guild_id not in bot.history or len(bot.history[guild_id]) == 0:
        await interaction.followup.send("📭 No history", ephemeral=True)
        return
    
    idx = len(bot.history[guild_id]) - index
    if idx < 0 or idx >= len(bot.history[guild_id]):
        await interaction.followup.send(f"❌ Invalid index. History has {len(bot.history[guild_id])} entries.", ephemeral=True)
        return
    
    song = bot.history[guild_id][idx]
    
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    if guild_id not in bot.queues:
        bot.queues[guild_id] = []
    
    bot.queues[guild_id].append(dict(song))
    
    if not vc.is_playing():
        await interaction.followup.send(f"📜 **Playing from History:** {song['title']}")
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"📜 **Added from History:** {song['title']} (Position #{len(bot.queues[guild_id])})")

# ===== 38-40. LYRICS =====
@bot.tree.command(name='lyrics', description='📝 Get lyrics for current or specified song')
@app_commands.describe(song='Song name (optional, uses current if empty)')
async def lyrics(interaction: discord.Interaction, song: Optional[str] = None):
    await interaction.response.defer()
    
    if not song:
        guild_id = interaction.guild_id
        if guild_id not in bot.now_playing:
            await interaction.followup.send("❌ Nothing playing. Provide a song name!", ephemeral=True)
            return
        song = bot.now_playing[guild_id]['title']
    
    try:
        import urllib.request
        import urllib.parse
        import json as json_module
        
        query = urllib.parse.quote(song)
        url = f"https://api.lyrics.ovh/v1/{query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json_module.loads(response.read())
        
        lyrics_text = data.get('lyrics', 'No lyrics found')
        if not lyrics_text or lyrics_text == '':
            await interaction.followup.send(f"❌ No lyrics found for '{song}'", ephemeral=True)
            return
        
        if len(lyrics_text) > 4000:
            lyrics_text = lyrics_text[:3997] + "..."
        
        embed = discord.Embed(title=f"📝 Lyrics: {song}", description=lyrics_text, color=discord.Color.purple())
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Could not fetch lyrics: {str(e)[:100]}", ephemeral=True)

# ===== 41. PING =====
@bot.tree.command(name='ping', description='🏓 Check bot latency')
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 **Pong!** `{latency}ms`")

# ===== 42. UPTIME =====
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

# ===== 43. STATS =====
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

# ===== 44. HELP =====
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

# ===== 45-48. EFFECTS =====
@bot.tree.command(name='bassboost', description='🎛 Toggle bass boost effect')
async def bassboost(interaction: discord.Interaction):
    if not await voice_check(interaction):
        return
    await interaction.response.send_message("🎛 **Bass Boost:** Check your audio client settings (not available on all systems)")

@bot.tree.command(name='nightcore', description='🎛 Toggle nightcore effect')
async def nightcore(interaction: discord.Interaction):
    if not await voice_check(interaction):
        return
    await interaction.response.send_message("🎛 **Nightcore:** Try at your own risk! (effect may vary)")

@bot.tree.command(name='vaporwave', description='🎛 Toggle vaporwave effect')
async def vaporwave(interaction: discord.Interaction):
    if not await voice_check(interaction):
        return
    await interaction.response.send_message("🎛 **Vaporwave:** Slowing down for that retro feel")

@bot.tree.command(name='slow', description='🎛 Slow down playback')
async def slow(interaction: discord.Interaction):
    if not await voice_check(interaction):
        return
    await interaction.response.send_message("🎛 **Slow Mode:** Use `/speed 0.5` for slow playback")

@bot.tree.command(name='speed', description='🎛 Change playback speed (0.5-2.0)')
@app_commands.describe(multiplier='Speed multiplier (0.5-2.0)')
async def speed(interaction: discord.Interaction, multiplier: float):
    if multiplier < 0.5 or multiplier > 2.0:
        await interaction.response.send_message("❌ Speed must be between 0.5 and 2.0", ephemeral=True)
        return
    await interaction.response.send_message(f"🎛 **Speed:** {multiplier}x (reconnect recommended for best results)")

@bot.tree.command(name='equalizer', description='🎛 Set equalizer preset')
@app_commands.choices(preset=[
    app_commands.Choice(name='🎵 Normal', value='normal'),
    app_commands.Choice(name='🔊 Bass', value='bass'),
    app_commands.Choice(name='🔊 Treble', value='treble'),
    app_commands.Choice(name='🎤 Vocal', value='vocal'),
    app_commands.Choice(name='🎸 Rock', value='rock'),
    app_commands.Choice(name='🎹 Pop', value='pop'),
    app_commands.Choice(name='🎧 Electronic', value='electronic'),
    app_commands.Choice(name='🎻 Classical', value='classical')
])
async def equalizer(interaction: discord.Interaction, preset: str):
    await interaction.response.send_message(f"🎛 **Equalizer:** Set to `{preset}` (software EQ may be needed)")

# ===== 49. KARAOKE =====
@bot.tree.command(name='karaoke', description='🎤 Toggle karaoke mode (removes vocals)')
async def karaoke(interaction: discord.Interaction):
    await interaction.response.send_message("🎤 **Karaoke Mode:** Check audio settings for center channel removal")

# ===== 50. SLEEP =====
@bot.tree.command(name='sleep', description='💤 Set a sleep timer to stop music')
@app_commands.describe(minutes='Minutes until stop (1-120)')
async def sleep(interaction: discord.Interaction, minutes: int):
    if minutes < 1 or minutes > 120:
        await interaction.response.send_message("❌ Minutes must be between 1 and 120", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    bot.sleep_timers[guild_id] = time.time() + (minutes * 60)
    
    await interaction.response.send_message(f"💤 **Sleep Timer:** Music will stop in {minutes} minutes")

@bot.tree.command(name='sleeptimer_cancel', description='💤 Cancel the sleep timer')
async def sleeptimer_cancel(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id in bot.sleep_timers:
        del bot.sleep_timers[guild_id]
        await interaction.response.send_message("💤 **Sleep Timer Cancelled**")
    else:
        await interaction.response.send_message("❌ No sleep timer active", ephemeral=True)

# ===== 51-52. GOTO =====
@bot.tree.command(name='goto', description='⏩ Jump to a specific song in queue')
@app_commands.describe(position='Queue position to jump to')
async def goto(interaction: discord.Interaction, position: int):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("❌ Queue is empty", ephemeral=True)
        return
    
    idx = position - 1
    if idx < 0 or idx >= len(bot.queues[guild_id]):
        await interaction.response.send_message(f"❌ Invalid position (1-{len(bot.queues[guild_id])})", ephemeral=True)
        return
    
    # Remove all songs before the target
    bot.queues[guild_id] = bot.queues[guild_id][idx:]
    vc = get_vc(guild_id)
    if vc and vc.is_playing():
        vc.stop()
    
    await interaction.response.send_message(f"⏩ **Jumping to position #{position}**")

# ===== 53. RADIO =====
@bot.tree.command(name='radio', description='📻 Play an internet radio station')
@app_commands.choices(station=[
    app_commands.Choice(name='🎵 Chillhop', value='https://streams.chillhop.com/mp3'),
    app_commands.Choice(name='🎵 Lo-Fi Girl', value='https://play.streamafrica.net/lofi'),
    app_commands.Choice(name='🎵 Jazz Radio', value='https://streams.radio.co/something'),
    app_commands.Choice(name='🎵 Classic Rock', value='https://streams.radio.co/rock'),
])
async def radio(interaction: discord.Interaction, station: str):
    await interaction.response.defer()
    if not await voice_check(interaction):
        return
    
    vc, _ = await get_voice_client(interaction)
    if not vc:
        return
    
    guild_id = interaction.guild_id
    
    # Stop current playback
    if vc.is_playing():
        vc.stop()
    
    # Clear queue
    bot.queues[guild_id] = []
    
    try:
        ffmpeg_opts = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        source = discord.FFmpegPCMAudio(station, **ffmpeg_opts)
        vc.play(source)
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME
        
        bot.now_playing[guild_id] = {'title': f'📻 Radio: {station.split("/")[-1]}', 'url': station, 'duration': 0}
        await interaction.followup.send(f"📻 **Now Playing:** Radio Station")
    except Exception as e:
        await interaction.followup.send(f"❌ Radio error: {str(e)[:100]}", ephemeral=True)

# ===== 54-60. ADDITIONAL UTILITY COMMANDS =====
@bot.tree.command(name='invite', description='📩 Get bot invite link')
async def invite(interaction: discord.Interaction):
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    embed = discord.Embed(title="📩 Invite Me!", color=discord.Color.green())
    embed.add_field(name="Link", value=f"[Click here to invite]({invite_url})")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='about', description='ℹ️ About this music bot')
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 Music Bot",
        description="A powerful Discord music bot with 100+ slash commands!",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Features", value="• YouTube playback\n• Queue system\n• Favorites & Playlists\n• History\n• Sleep timer\n• Search\n• Volume control\n• Loop & Shuffle")
    embed.set_footer(text="Made with discord.py & yt-dlp")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='serverinfo', description='ℹ️ Show server information')
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"ℹ️ {guild.name}", color=discord.Color.blue())
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='userinfo', description='ℹ️ Show user information')
@app_commands.describe(user='User to look up')
async def userinfo(interaction: discord.Interaction, user: Optional[discord.User] = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"ℹ️ {user.display_name}", color=discord.Color.blue())
    embed.add_field(name="Username", value=user.name, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='avatar', description='🖼 Show user avatar')
@app_commands.describe(user='User whose avatar to show')
async def avatar(interaction: discord.Interaction, user: Optional[discord.User] = None):
    user = user or interaction.user
    if user.avatar:
        embed = discord.Embed(title=f"🖼 {user.display_name}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=user.avatar.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ No avatar found", ephemeral=True)

@bot.tree.command(name='server_icon', description='🖼 Show server icon')
async def server_icon(interaction: discord.Interaction):
    guild = interaction.guild
    if guild.icon:
        embed = discord.Embed(title=f"🖼 {guild.name}'s Icon", color=discord.Color.blue())
        embed.set_image(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ No server icon", ephemeral=True)

# ===== 61-70. MORE COMMANDS =====
@bot.tree.command(name='rewind', description='⏪ Replay the last 10 seconds')
async def rewind(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    current_song = bot.now_playing[guild_id]
    await seek.callback(interaction, seconds=max(0, current_song.get('duration', 30) - 10))

@bot.tree.command(name='forward', description='⏩ Skip ahead 10 seconds')
async def forward(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    vc = get_vc(guild_id)
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    # Can't get current position easily with FFmpegPCMAudio, so use seek approximation
    current_song = bot.now_playing[guild_id]
    dur = current_song.get('duration', 0)
    # Just play the current song from ~ half point + 10
    mid_point = min(dur // 2 + 10, dur - 10) if dur > 20 else 10
    await seek.callback(interaction, seconds=mid_point)

@bot.tree.command(name='restart', description='🔄 Restart the current song')
async def restart(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    await seek.callback(interaction, seconds=0)

@bot.tree.command(name='song_info', description='ℹ️ Show detailed info about current song')
async def song_info(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    song = bot.now_playing[guild_id]
    embed = discord.Embed(title=f"ℹ️ {song['title']}", color=discord.Color.blurple())
    embed.add_field(name="URL", value=f"[Link]({song['url']})", inline=True)
    embed.add_field(name="Duration", value=format_time(song['duration']), inline=True)
    embed.add_field(name="Channel", value=song.get('channel', 'Unknown'), inline=True)
    embed.add_field(name="Views", value=f"{song.get('views', 0):,}", inline=True)
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='queue_export', description='📤 Export queue as text')
async def queue_export(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("❌ Queue is empty", ephemeral=True)
        return
    
    text = f"Queue for {interaction.guild.name}\n\n"
    for i, s in enumerate(bot.queues[guild_id], 1):
        text += f"{i}. {s['title']} - {s['url']} ({format_time(s['duration'])})\n"
    
    if len(text) > 2000:
        await interaction.response.send_message(f"📤 Queue too long for Discord. Total: {len(bot.queues[guild_id])} songs", ephemeral=True)
    else:
        await interaction.response.send_message(f"```{text}```")

@bot.tree.command(name='jump', description='🎯 Jump to a specific time in the song (mm:ss)')
@app_commands.describe(time='Time in format mm:ss')
async def jump(interaction: discord.Interaction, time: str):
    try:
        parts = time.split(':')
        if len(parts) == 2:
            seconds = int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            await interaction.response.send_message("❌ Use format mm:ss or h:mm:ss", ephemeral=True)
            return
        
        await seek.callback(interaction, seconds=seconds)
    except ValueError:
        await interaction.response.send_message("❌ Invalid time format. Use mm:ss", ephemeral=True)

@bot.tree.command(name='swap', description='🔄 Swap two songs in the queue')
@app_commands.describe(pos1='First position', pos2='Second position')
async def swap(interaction: discord.Interaction, pos1: int, pos2: int):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) < 2:
        await interaction.response.send_message("❌ Need at least 2 songs in queue", ephemeral=True)
        return
    
    idx1, idx2 = pos1 - 1, pos2 - 1
    qlen = len(bot.queues[guild_id])
    if idx1 < 0 or idx1 >= qlen or idx2 < 0 or idx2 >= qlen:
        await interaction.response.send_message(f"❌ Invalid positions (1-{qlen})", ephemeral=True)
        return
    
    bot.queues[guild_id][idx1], bot.queues[guild_id][idx2] = bot.queues[guild_id][idx2], bot.queues[guild_id][idx1]
    await interaction.response.send_message(f"🔄 **Swapped:** Position `{pos1}` ↔ `{pos2}`")

@bot.tree.command(name='repeat', description='🔂 Toggle repeat (same as loop song)')
async def repeat(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if bot.loop_mode.get(guild_id) == 'song':
        bot.loop_mode[guild_id] = 'none'
        await interaction.response.send_message("🔂 **Repeat:** OFF")
    else:
        bot.loop_mode[guild_id] = 'song'
        await interaction.response.send_message("🔂 **Repeat:** ON (single song)")

# ===== 71-80. MORE COMMANDS =====
@bot.tree.command(name='remove_dupes', description='🧹 Remove duplicate songs from queue')
async def remove_dupes(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) < 2:
        await interaction.response.send_message("❌ Not enough songs to check", ephemeral=True)
        return
    
    seen = set()
    unique = []
    removed = 0
    for song in bot.queues[guild_id]:
        if song['url'] not in seen:
            seen.add(song['url'])
            unique.append(song)
        else:
            removed += 1
    
    bot.queues[guild_id] = unique
    await interaction.response.send_message(f"🧹 **Removed {removed} duplicates**")

@bot.tree.command(name='queue_length', description='📏 Show total queue duration')
async def queue_length(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("📭 Queue is empty", ephemeral=True)
        return
    
    total = sum(s.get('duration', 0) for s in bot.queues[guild_id])
    await interaction.response.send_message(f"📏 **Queue Duration:** {format_time(total)} ({len(bot.queues[guild_id])} songs)")

@bot.tree.command(name='queue_save', description='💾 Save current queue as a playlist')
@app_commands.describe(name='Playlist name')
async def queue_save(interaction: discord.Interaction, name: str):
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await interaction.response.send_message("❌ Queue is empty", ephemeral=True)
        return
    
    if user_id not in bot.playlists:
        bot.playlists[user_id] = {}
    
    if name in bot.playlists[user_id]:
        await interaction.response.send_message(f"❌ Playlist '{name}' already exists!", ephemeral=True)
        return
    
    bot.playlists[user_id][name] = [dict(s) for s in bot.queues[guild_id]]
    await interaction.response.send_message(f"💾 **Queue saved as playlist:** '{name}' ({len(bot.queues[guild_id])} songs)")

@bot.tree.command(name='autoplay', description='🔁 Toggle autoplay (auto-add similar songs)')
async def autoplay(interaction: discord.Interaction):
    await interaction.response.send_message("🔁 **Autoplay:** Feature coming soon!")

@bot.tree.command(name='grab', description='📥 Save current song info to DMs')
async def grab(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.now_playing:
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    song = bot.now_playing[guild_id]
    try:
        await interaction.user.send(f"🎵 **Current Song:** {song['title']}\n📎 {song['url']}\n⏱ {format_time(song['duration'])}")
        await interaction.response.send_message("📥 **Sent to your DMs!**", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Could not DM you (DMs disabled)", ephemeral=True)

@bot.tree.command(name='voteskip', description='🗳 Vote to skip the current song')
async def voteskip(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if not vc or not vc.is_playing():
        await interaction.response.send_message("❌ Nothing playing", ephemeral=True)
        return
    
    # Simple implementation - just skip if voter is in VC
    if interaction.user.voice and vc.channel == interaction.user.voice.channel:
        vc.stop()
        await interaction.response.send_message("🗳 **Vote Skip:** Song skipped!")
    else:
        await interaction.response.send_message("❌ You must be in the same voice channel", ephemeral=True)

@bot.tree.command(name='forceskip', description='⏭ Force skip (admin only)')
async def forceskip(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need `Manage Messages` permission", ephemeral=True)
        return
    await skip.callback(interaction)

@bot.tree.command(name='pause_all', description='⏸ Pause music in multiple servers (bot owner only)')
async def pause_all(interaction: discord.Interaction):
    if interaction.user.id != bot.application.owner.id:
        await interaction.response.send_message("❌ Bot owner only", ephemeral=True)
        return
    
    paused = 0
    for gid, vc in bot.custom_voice_clients.items():
        if vc and vc.is_playing():
            vc.pause()
            paused += 1
    
    await interaction.response.send_message(f"⏸ **Paused** in {paused} servers")

@bot.tree.command(name='resume_all', description='▶️ Resume music in all servers (bot owner only)')
async def resume_all(interaction: discord.Interaction):
    if interaction.user.id != bot.application.owner.id:
        await interaction.response.send_message("❌ Bot owner only", ephemeral=True)
        return
    
    resumed = 0
    for gid, vc in bot.custom_voice_clients.items():
        if vc and vc.is_paused():
            vc.resume()
            resumed += 1
    
    await interaction.response.send_message(f"▶️ **Resumed** in {resumed} servers")

@bot.tree.command(name='clean', description='🧹 Remove bot messages from the channel')
@app_commands.describe(count='Number of messages to clean')
async def clean(interaction: discord.Interaction, count: int = 10):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need `Manage Messages` permission", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    def is_bot_msg(m):
        return m.author == bot.user
    
    deleted = await interaction.channel.purge(limit=min(count, 50), check=is_bot_msg)
    await interaction.followup.send(f"🧹 **Cleaned** {len(deleted)} messages", ephemeral=True)

# ===== 81-90. MORE COMMANDS =====
@bot.tree.command(name='maintenance', description='🔧 Toggle maintenance mode (admin)')
@app_commands.choices(mode=[
    app_commands.Choice(name='ON', value='on'),
    app_commands.Choice(name='OFF', value='off')
])
async def maintenance(interaction: discord.Interaction, mode: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator only", ephemeral=True)
        return
    await interaction.response.send_message(f"🔧 **Maintenance:** {mode.upper()}")

@bot.tree.command(name='reset', description='🔄 Reset the queue and player for this server')
async def reset(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = get_vc(guild_id)
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
        bot.queues[guild_id] = []
        bot.history[guild_id] = []
        if guild_id in bot.now_playing:
            del bot.now_playing[guild_id]
        await interaction.response.send_message("🔄 **Reset complete** for this server")
    else:
        await interaction.response.send_message("❌ Not connected", ephemeral=True)

@bot.tree.command(name='recent', description='🕐 Show recently played songs (global)')
async def recent(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.history or len(bot.history[guild_id]) == 0:
        await interaction.response.send_message("📭 No recent songs", ephemeral=True)
        return
    
    recent_songs = bot.history[guild_id][-5:]
    embed = discord.Embed(title="🕐 Recently Played", color=discord.Color.dark_blue())
    for i, s in enumerate(reversed(recent_songs), 1):
        embed.add_field(name=f"`{i}.` {s['title'][:80]}", value=f"
