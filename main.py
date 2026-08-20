import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re
import random
import time
from typing import Optional
from flask import Flask
from config import TOKEN, DEFAULT_VOLUME

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

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
        self.loop_mode = {}
        self.shuffle_mode = {}
        self.start_time = time.time()

    async def setup_hook(self):
        # لێرەدا سینک لارەداوە بۆ ئەوەی تووشی Rate Limit (429) نەبیت
        print("✅ Bot is setting up...")

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
    'default_search': 'ytsearch',
    'skip_download': True,
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

async def get_voice_client(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
        return None, None
    
    voice_channel = interaction.user.voice.channel
    guild_id = interaction.guild.id
    
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
        vc = bot.custom_voice_clients[guild_id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)
    else:
        try:
            vc = await voice_channel.connect()
            bot.custom_voice_clients[guild_id] = vc
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not connect: {str(e)[:100]}", ephemeral=True)
            return None, None
    
    return vc, interaction.response.send_message

async def play_next(guild_id):
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await asyncio.sleep(10)
        if guild_id in bot.queues and len(bot.queues[guild_id]) == 0:
            vc = bot.custom_voice_clients.get(guild_id)
            if vc and vc.is_connected() and not vc.is_playing():
                await vc.disconnect()
        return

    song = bot.queues[guild_id].pop(0)
    bot.now_playing[guild_id] = song
    
    vc = bot.custom_voice_clients.get(guild_id)
    if not vc or not vc.is_connected():
        return

    def after_playing(error):
        coro = play_next(guild_id)
        asyncio.run_coroutine_threadsafe(coro, bot.loop)

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = info['url']

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=after_playing)
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME
    except Exception as e:
        print(f"Error: {e}")
        asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name="/play | Music Bot")
    await bot.change_presence(activity=activity)
    print(f'✅ Bot is ready! Logged in as {bot.user}')

@bot.tree.command(name='play', description='🎵 Play a song')
@app_commands.describe(query='Song name or URL')
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
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
        await interaction.followup.send(f"▶️ **Now Playing:** {song['title']}")
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"✅ **Added to Queue:** {song['title']}")

@bot.tree.command(name='stop', description='⏹ Stop and disconnect')
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = bot.custom_voice_clients.get(guild_id)
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
        bot.queues[guild_id] = []
        await vc.disconnect()
        bot.custom_voice_clients.pop(guild_id, None)
        await interaction.response.send_message("⏹ **Stopped & Disconnected**")
    else:
        await interaction.response.send_message("❌ Not connected", ephemeral=True)

@bot.tree.command(name='ping', description='🏓 Check latency')
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 **Pong!** `{latency}ms`")

if __name__ == '__main__':
    import threading
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
