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

class MusicBot(commands.Bot):
    def __init__(self):
        # لێرەدا پێشگری (Prefix)ـی بۆتەکە دەکەین بە '$'
        super().__init__(command_prefix='$', intents=intents)
        self.queues = {}
        self.custom_voice_clients = {}

    async def setup_hook(self):
        print("✅ Bot is setting up...")

bot = MusicBot()

# لادانی فەرمانی default help بۆ ئەوەی خۆمان یەکێکی جوانتر دروست بکەین
bot.remove_command('help')

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

async def play_next_message(ctx):
    guild_id = ctx.guild.id
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
        coro = play_next_message(ctx)
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
        coro = play_next_message(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

@bot.event
async def on_ready():
    # دانانی دۆخێک لە پرۆفایلی بۆتەکەدا کە ئاماژە بە $help دەکات
    activity = discord.Activity(type=discord.ActivityType.listening, name="$help")
    await bot.change_presence(activity=activity)
    print(f'✅ Bot is ready! Logged in as {bot.user}')

@bot.command(name='play', description='Play a song from YouTube')
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel first!")
        return

    voice_channel = ctx.author.voice.channel
    guild_id = ctx.guild.id

    if guild_id not in bot.custom_voice_clients or not bot.custom_voice_clients[guild_id].is_connected():
        try:
            vc = await voice_channel.connect()
            bot.custom_voice_clients[guild_id] = vc
        except Exception as e:
            await ctx.send(f"❌ Could not connect: {str(e)[:100]}")
            return
    else:
        vc = bot.custom_voice_clients[guild_id]
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)

    song = search_youtube(query)
    if 'error' in song:
        await ctx.send(f"❌ {song['error']}")
        return

    if guild_id not in bot.queues:
        bot.queues[guild_id] = []

    bot.queues[guild_id].append(song)

    if not vc.is_playing():
        await ctx.send(f"✅ **Added to queue:** {song['title']}")
        await play_next_message(ctx)
    else:
        position = len(bot.queues[guild_id])
        await ctx.send(f"✅ **Added to queue:** {song['title']} (Position #{position})")

@bot.command(name='skip', description='Skip the current song')
async def skip(ctx):
    guild_id = ctx.guild.id
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_playing():
        bot.custom_voice_clients[guild_id].stop()
        await ctx.send("⏭️ Skipped!")
    else:
        await ctx.send("❌ Nothing is playing right now.")

@bot.command(name='queue', description='Show the current song queue')
async def show_queue(ctx):
    guild_id = ctx.guild.id
    if guild_id not in bot.queues or len(bot.queues[guild_id]) == 0:
        await ctx.send("📭 Queue is empty.")
        return

    msg = "**🎶 Song Queue:**\n"
    for i, song in enumerate(bot.queues[guild_id], 1):
        duration = song.get('duration', 0)
        minutes, seconds = divmod(duration, 60)
        time_str = f"{minutes}:{seconds:02d}" if duration else "🔴 Live"
        msg += f"`{i}.` **{song['title']}** ({time_str})\n"

    if len(msg) > 2000:
        msg = msg[:1997] + "..."
    await ctx.send(msg)

@bot.command(name='stop', description='Stop playing and disconnect the bot')
async def stop(ctx):
    guild_id = ctx.guild.id
    if guild_id in bot.custom_voice_clients and bot.custom_voice_clients[guild_id].is_connected():
        if bot.custom_voice_clients[guild_id].is_playing():
            bot.custom_voice_clients[guild_id].stop()
        await bot.custom_voice_clients[guild_id].disconnect()
        bot.custom_voice_clients.pop(guild_id, None)
        bot.queues.pop(guild_id, None)
        await ctx.send("👋 Disconnected!")
    else:
        await ctx.send("❌ I'm not connected to a voice channel.")

@bot.command(name='ping', description='Check bot latency')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

# ============================================================
# HELP COMMAND - فەرمانی یارمەتی
# ============================================================
@bot.command(name='help', description='Show available commands')
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 **Music Bot Commands**",
        description="Here is a list of all available commands using the `$` prefix:",
        color=discord.Color.blurple()
    )
    
    embed.add_field(name="`$play <song>`", value="Play a song or search on YouTube.", inline=False)
    embed.add_field(name="`$skip`", value="Skip the currently playing song.", inline=False)
    embed.add_field(name="`$queue`", value="Show the current song queue.", inline=False)
    embed.add_field(name="`$stop`", value="Stop music and disconnect the bot.", inline=False)
    embed.add_field(name="`$ping`", value="Check the bot's latency.", inline=False)
    embed.add_field(name="`$help`", value="Show this help message.", inline=False)
    
    embed.set_footer(text="🎵 Music Bot • Made with Python")
    await ctx.send(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        exit(1)
    bot.run(TOKEN)
