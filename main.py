async def voice_check(interaction: discord.Interaction) -> bool:
    """Check whether the user is connected to a voice channel."""

    if interaction.user.voice is not None:
        return True

    message = "❌ You must be in a voice channel first!"

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )
    except (discord.HTTPException, discord.Forbidden):
        pass

    return False


async def get_voice_client(ctx_or_interaction):
    """Get an existing voice client or connect to the user's voice channel."""

    if isinstance(ctx_or_interaction, discord.Interaction):
        user = ctx_or_interaction.user
        guild = ctx_or_interaction.guild

        async def respond(message, **kwargs):
            kwargs.setdefault("ephemeral", True)

            try:
                if ctx_or_interaction.response.is_done():
                    return await ctx_or_interaction.followup.send(
                        message,
                        **kwargs
                    )

                return await ctx_or_interaction.response.send_message(
                    message,
                    **kwargs
                )
            except (discord.HTTPException, discord.Forbidden):
                return None

    else:
        user = (
            ctx_or_interaction.author
            if hasattr(ctx_or_interaction, "author")
            else ctx_or_interaction.user
        )

        guild = ctx_or_interaction.guild

        async def respond(message, **kwargs):
            kwargs.pop("ephemeral", None)

            if hasattr(ctx_or_interaction, "send"):
                return await ctx_or_interaction.send(
                    message,
                    **kwargs
                )

            if hasattr(ctx_or_interaction, "response"):
                return await ctx_or_interaction.response.send_message(
                    message,
                    **kwargs
                )

            return None

    if guild is None:
        await respond("❌ This command can only be used in a server.")
        return None, respond

    if user.voice is None:
        await respond(
            "❌ You must be in a voice channel first!"
        )
        return None, respond

    voice_channel = user.voice.channel
    guild_id = guild.id

    vc = bot.custom_voice_clients.get(guild_id)

    # Reuse existing connection
    if vc and vc.is_connected():

        # Move bot if user is in another voice channel
        if vc.channel != voice_channel:
            try:
                await vc.move_to(voice_channel)
            except (discord.Forbidden, discord.HTTPException) as exc:
                await respond(
                    f"❌ Could not move to `{voice_channel.name}`.\n"
                    f"`{type(exc).__name__}`"
                )
                return None, respond

        return vc, respond

    # Remove stale client
    bot.custom_voice_clients.pop(guild_id, None)

    # Connect
    try:
        vc = await voice_channel.connect(
            reconnect=True,
            timeout=20
        )

        bot.custom_voice_clients[guild_id] = vc

        return vc, respond

    except asyncio.TimeoutError:
        await respond(
            "❌ Voice connection timed out."
        )
        return None, respond

    except discord.ClientException as exc:
        await respond(
            f"❌ Discord voice connection failed:\n`{str(exc)[:150]}`"
        )
        return None, respond

    except discord.Forbidden:
        await respond(
            "❌ I don't have permission to connect to the voice channel."
        )
        return None, respond

    except Exception as exc:
        logging.getLogger("hmb.voice").exception(
            "Voice connection failed"
        )

        await respond(
            f"❌ Could not connect to voice channel:\n"
            f"`{type(exc).__name__}: {str(exc)[:150]}`"
        )

        return None, respond
