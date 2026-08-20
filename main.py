import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import re
from aiohttp import web
from config import TOKEN, DEFAULT_VOLUME

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.queues = {}
        self.custom_voice_clients = {}

    async def setup_hook(self):
        print("✅ Bot is ready with Prefix commands (!hmb)!")

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
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = info['url']

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=after_playing)
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = DEFAULT_VOLUME

        try:
            await ctx.send(f"🎵 **Now Playing:** {song['title']}")
        except:
            pass
    except Exception as e:
        print(f"Error in playback: {e}")
        coro = play_next_message(ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping), web.get('/healthz', handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web server successfully started and listening on port 8080")

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.listening, name="!hmb")
    await bot.change_presence(activity=activity)
    print(f'✅ Bot is ready! Logged in as {bot.user}')

class SongSearchModal(discord.ui.Modal, title="🔍 Search or Play Song"):
    song_query = discord.ui.TextInput(
        label="Song Name or YouTube Link",
        placeholder="Type song name or paste link here...",
        required=True,
        max_length=300
    )

    def __init__(self, ctx, view_instance):
        super().__init__()
        self.ctx = ctx
        self.view_instance = view_instance

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.song_query.value
        guild_id = self.ctx.guild.id
        voice_channel = self.ctx.author.voice.channel if self.ctx.author.voice else None

        if not voice_channel:
            await interaction.followup.send("❌ You must be in a voice channel!", ephemeral=True)
            return

        if guild_id not in bot.custom_voice_clients or not bot.custom_voice_clients[guild_id].is_connected():
            try:
                vc = await voice_channel.connect()
                bot.custom_voice_clients[guild_id] = vc
            except Exception as e:
                await interaction.followup.send(f"❌ Could not connect: {str(e)[:100]}", ephemeral=True)
                return
        else:
            vc = bot.custom_voice_clients[guild_id]

        song = search_youtube(query)
        if 'error' in song:
            await interaction.followup.send(f"❌ {song['error']}", ephemeral=True)
            return

        if guild_id not in bot.queues:
            bot.queues[guild_id] = []

        bot.queues[guild_id].append(song)

        if not vc.is_playing():
            await interaction.followup.send(f"✅ **Added & Playing:** {song['title']}", ephemeral=True)
            await play_next_message(self.ctx)
        else:
            position = len(bot.queues[guild_id])
            await interaction.followup.send(f"✅ **Added to queue:** {song['title']} (Position #{position})", ephemeral=True)

        embed = await self.view_instance.update_embed()
        await self.view_instance.message.edit(embed=embed)

class ControlView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.message = None

    async def update_embed(self):
        guild_id = self.guild_id
        embed = discord.Embed(title="🎛 **Music Control Panel**", color=discord.Color.blurple())
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

    @discord.ui.button(label="🔍 Search & Play", style=discord.ButtonStyle.primary, row=0)
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
            return
        await interaction.response.send_modal(SongSearchModal(self.ctx, self))

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

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.secondary, row=0)
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
            try:
                await self.message.delete()
            except:
                pass
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

@bot.command(name='hmb', description='Open the interactive music control panel')
async def hmb(ctx):
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

    view = ControlView(ctx)
    volume = int(vc.source.volume * 100) if vc.source and hasattr(vc.source, 'volume') else DEFAULT_VOLUME
    embed = discord.Embed(
        title="🎛 **Music Control Panel**",
        description=f"**Guild:** `{ctx.guild.name}`\n"
                    f"**Voice Channel:** `{vc.channel.name}`\n"
                    f"**Volume:** `{volume}%`",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"📋 Queue: {len(bot.queues.get(guild_id, []))} songs")
    message = await ctx.send(embed=embed, view=view)
    view.message = message

    def disable_buttons():
        for child in view.children:
            child.disabled = True
    view.on_timeout = disable_buttons

async def main():
    server_task = asyncio.create_task(start_web_server())
    bot_task = asyncio.create_task(bot.start(TOKEN))
    await asyncio.gather(server_task, bot_task)

if __name__ == "__main__":
    if not TOKEN:
        exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
