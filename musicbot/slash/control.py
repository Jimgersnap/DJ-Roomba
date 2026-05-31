"""
Slash commands — Phase 5: bot control.
/summon  /disconnect  /reconnect  /follow  /karaoke
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import invoke_response, respond

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


def register(bot: "MusicBot") -> None:
    """Register all bot-control slash commands with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  /summon                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="summon",
        description="Bring DJ Roomba to the voice channel you're in.",
    )
    async def slash_summon(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("summon")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            raise exceptions.CommandError(
                "You are not connected to a voice channel."
            )

        # Call cmd_summon with message=None — last_np_msg will be cleared,
        # which is fine since slash commands don't produce a message object.
        response = await bot.cmd_summon(
            ssd_=ctx.ssd,
            guild=guild,
            author=ctx.author,
            message=None,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /disconnect                                                       #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="disconnect",
        description="Disconnect DJ Roomba from the voice channel.",
    )
    async def slash_disconnect(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("disconnect")
        guild = ctx.require_guild()
        response = await bot.cmd_disconnect(guild=guild)
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /reconnect                                                        #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="reconnect",
        description="Disconnect and reconnect to voice, preserving the queue.",
    )
    async def slash_reconnect(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("reconnect")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a server."
            )

        response = await bot.cmd_reconnect(
            ssd_=ctx.ssd,
            guild=guild,
            author=ctx.author,
            channel=interaction.channel,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /follow                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="follow",
        description="Have DJ Roomba follow you (or another user) between voice channels.",
    )
    @app_commands.describe(
        user="User to follow. Owner only. Leave blank to follow yourself."
    )
    async def slash_follow(
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("follow")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a server."
            )

        followed_user = bot.server_data[guild.id].follow_user

        # If already following, toggle off or switch.
        if followed_user is not None:
            if followed_user.id == ctx.author.id:
                bot.server_data[guild.id].follow_user = None
                await respond(
                    interaction,
                    f"No longer following `{ctx.author.name}`.",
                )
                return

            bot.server_data[guild.id].follow_user = ctx.author
            await respond(
                interaction,
                f"Now following `{ctx.author.name}` between voice channels.",
            )
            return

        # Owner can target another member; everyone else follows themselves.
        target = ctx.author
        if ctx.author.id == bot.config.owner_id and user is not None:
            target = user

        bot.server_data[guild.id].follow_user = target
        await respond(
            interaction,
            f"Will follow `{target.name}` between voice channels.",
        )

    # ---------------------------------------------------------------- #
    #  /karaoke                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="karaoke",
        description="Toggle karaoke mode — only members with bypass permission can queue songs.",
    )
    async def slash_karaoke(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("karaoke")
        player = await ctx.get_player()
        response = await bot.cmd_karaoke(ssd_=ctx.ssd, player=player)
        await invoke_response(interaction, response)
