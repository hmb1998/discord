# ============================================================
# CONTROL PANEL - پانێڵی کۆنترۆڵ (View with Buttons)
# ============================================================
# ئەم بەشە بکەرە ناو هەمان فایلی bot.py (لە کۆتایدا، پێش bot.run)
# ============================================================

class ControlView(discord.ui.View):
    """پانێڵی کۆنترۆڵ بە دووگمەی Interactive"""

    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 خولەک دوای ئەوە دووگمەکان نامانەوە
        self.interaction = interaction
        self.guild_id = interaction.guild.id
        self.message = None  # دواتر پڕ دەکرێتەوە

    async def update_embed(self):
        """Embed یەکەم هەڵدەگرێتەوە بۆ دۆخی ئێستا"""
        guild_id = self.guild_id
        embed = discord.Embed(
            title="🎛 **Control Panel**",
            color=discord.Color.blurple()
        )

        # دۆخی بۆت
        if guild_id in bot.voice_clients and bot.voice_clients[guild_id].is_connected():
            vc = bot.voice_clients[guild_id]
            status = "🟢 Connected" if vc.is_playing() else "🟡 Paused" if not vc.is_paused() and vc.is_connected() else "⚫ Stopped"
            if vc.is_paused():
                status = "🟡 Paused"
            channel_name = vc.channel.name if vc.channel else "Unknown"

            # دەنگی ئێستا
            volume = int(vc.source.volume * 100) if vc.source and hasattr(vc.source, 'volume') else DEFAULT_VOLUME
            volume = int(volume * 100) if isinstance(vc.source.volume, float) else volume  # some fix

            embed.add_field(name="📡 Connection", value=f"`{channel_name}`", inline=True)
            embed.add_field(name="🔊 Volume", value=f"`{volume}%`", inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)

            # گۆرانی ئێستا
            if guild_id in bot.queues and len(bot.queues[guild_id]) > 0:
                # detach current song? Actually first in queue is current
                pass
        else:
            embed.add_field(name="📡 Status", value="❌ **Not Connected**", inline=False)

        # Queue length
        queue_len = len(bot.queues.get(guild_id, []))
        embed.set_footer(text=f"📋 Queue: {queue_len} songs • 🎵 Music Bot")

        return embed

    @discord.ui.button(label="⏸ Pause/Resume", style=discord.ButtonStyle.secondary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.voice_clients:
            await interaction.response.send_message("❌ Not connected!", ephemeral=True)
            return

        vc = bot.voice_clients[guild_id]
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Paused", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing to pause/resume", ephemeral=True)
            return

        # پانێڵ نوێ دەکەینەوە
        embed = await self.update_embed()
        await self.message.edit(embed=embed)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.primary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id in bot.voice_clients and bot.voice_clients[guild_id].is_playing():
            bot.voice_clients[guild_id].stop()
            await interaction.response.send_message("⏭ Skipped!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id in bot.voice_clients and bot.voice_clients[guild_id].is_connected():
            if bot.voice_clients[guild_id].is_playing():
                bot.voice_clients[guild_id].stop()
            await bot.voice_clients[guild_id].disconnect()
            bot.voice_clients.pop(guild_id, None)
            bot.queues.pop(guild_id, None)
            bot.current_channel.pop(guild_id, None)

            await interaction.response.send_message("👋 Disconnected!", ephemeral=True)
            # پانێڵ دابخە
            await self.message.delete()
            self.stop()
        else:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)

    @discord.ui.button(label="🔊 +10", style=discord.ButtonStyle.success, row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if guild_id not in bot.voice_clients:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)
            return

        vc = bot.voice_clients[guild_id]
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
        if guild_id not in bot.voice_clients:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)
            return

        vc = bot.voice_clients[guild_id]
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
        """نیشاندانی Queue وه‌ك پیامێك"""
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
    """پانێڵی کۆنترۆڵ بکەرەوە"""
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
        return

    guild_id = interaction.guild.id

    # دڵنیا بە لە بەستنەوەی بۆت
    if guild_id not in bot.voice_clients or not bot.voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ Bot is not connected! Use `/play` first.", ephemeral=True)
        return

    # دروستکردنی View
    view = ControlView(interaction)

    # Embed
    vc = bot.voice_clients[guild_id]
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

    # دوای 5 خولەک، دووگمەکان نامانەوە
    def disable_buttons():
        for child in view.children:
            child.disabled = True

    view.on_timeout = disable_buttons
