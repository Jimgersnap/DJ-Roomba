"""
Slash commands — Phase 2: core playback.
/play  /pause  /resume  /stop  /skip  /volume
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import defer, invoke_response, respond, respond_error

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


def register(bot: "MusicBot") -> None:
    """Register all playback slash commands with the bot's CommandTree."""

    # ------------------------------------------------------------------ #
    #  /play                                                               #
    # ------------------------------------------------------------------ #

    @bot.tree.command(
        name="play",
        description="Add a song or playlist to the queue. Accepts URLs or search terms.",
    )
    @app_commands.describe(query="Song name, URL, or playlist link")
    async def slash_play(interaction: discord.Interaction, query: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("play")

        # Defer immediately — extraction and download can take several seconds.
        await defer(interaction)

        guild = ctx.require_guild()
        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player(create=True)
        channel = interaction.channel

        # Replicate auto-unpause behaviour from _do_cmd_unpause_check.
        if bot.config.auto_unpause_on_play and player.is_paused:
            player.resume()
            await respond(interaction, "Bot was previously paused, resuming playback now.")
            return

        response = await bot._cmd_play(
            None,           # message — not needed for slash commands
            player,
            channel,
            guild,
            ctx.author,
            ctx.permissions,
            [],             # leftover_args
            query,
            head=False,
        )
        await invoke_response(interaction, response)

    # ------------------------------------------------------------------ #
    #  /pause                                                              #
    # ------------------------------------------------------------------ #

    @bot.tree.command(name="pause", description="Pause the currently playing song.")
    async def slash_pause(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("pause")
        player = await ctx.get_player()
        response = await bot.cmd_pause(ssd_=ctx.ssd, player=player)
        await invoke_response(interaction, response)

    # ------------------------------------------------------------------ #
    #  /resume                                                             #
    # ------------------------------------------------------------------ #

    @bot.tree.command(name="resume", description="Resume paused playback.")
    async def slash_resume(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("resume")
        player = await ctx.get_player()
        response = await bot.cmd_resume(ssd_=ctx.ssd, player=player)
        await invoke_response(interaction, response)

    # ------------------------------------------------------------------ #
    #  /stop                                                               #
    # ------------------------------------------------------------------ #

    @bot.tree.command(
        name="stop",
        description="Stop playback and clear the entire queue.",
    )
    async def slash_stop(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("stop")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player()

        if not player.is_playing:
            raise exceptions.CommandError("I'm not playing anything right now.")

        player.skip()
        player.playlist.clear()

        await respond(
            interaction,
            f"Stopped playback and cleared the queue in `{player.voice_client.channel.name}`.\n"
            "Start a new session with `/play`.",
        )

    # ------------------------------------------------------------------ #
    #  /skip                                                               #
    # ------------------------------------------------------------------ #

    @bot.tree.command(
        name="skip",
        description="Skip or vote to skip the current song.",
    )
    @app_commands.describe(force="Force skip without a vote (requires InstaSkip permission).")
    async def slash_skip(
        interaction: discord.Interaction, force: bool = False
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("skip")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player()
        ssd = ctx.ssd

        if player.is_stopped:
            raise exceptions.CommandError("I'm not playing anything to skip.")

        if not player.current_entry:
            next_entry = player.playlist.peek()
            if next_entry:
                if next_entry.is_downloading:
                    raise exceptions.CommandError(
                        f"**{next_entry.title}** is still downloading, please wait."
                    )
                if next_entry.is_downloaded:
                    raise exceptions.CommandError(
                        "The next song will be played shortly. Please wait."
                    )
            raise exceptions.CommandError(
                "Something odd is happening. Try restarting the bot if this persists."
            )

        current_entry = player.current_entry
        entry_author_id = current_entry.author.id if current_entry.author else 0

        permission_force_skip = ctx.permissions.instaskip or (
            bot.config.allow_author_skip and ctx.author.id == entry_author_id
        )

        if permission_force_skip and (force or bot.config.legacy_skip):
            if not ctx.permissions.skip_looped and player.repeatsong:
                raise exceptions.PermissionsError(
                    "You do not have permission to force skip a looped song."
                )

            guild = ctx.require_guild()
            if (
                bot.config.enable_queue_history_global
                or bot.config.enable_queue_history_guilds
            ):
                bot.server_data[guild.id].current_playing_url = ""

            if player.repeatsong:
                player.repeatsong = False
            player.skip()
            await respond(
                interaction, f"Force skipped **{current_entry.title}**."
            )
            return

        if not permission_force_skip and force:
            raise exceptions.PermissionsError(
                "You do not have permission to force skip."
            )

        # Vote skip — track by user ID only (no message reference for slash commands).
        voice_channel = player.voice_client.channel
        num_voice = sum(
            1
            for m in voice_channel.members
            if not m.bot and not m.voice.deaf and not m.voice.self_deaf
        ) or 1

        player.skip_state.skippers.add(ctx.author.id)
        num_skips = sum(
            1
            for m in voice_channel.members
            if m.id in player.skip_state.skippers
        )

        skips_required = min(
            bot.config.skips_required,
            round(num_voice * bot.config.skip_ratio_required),
        )

        if num_skips >= skips_required:
            if player.repeatsong:
                player.repeatsong = False
            player.skip()
            await respond(
                interaction,
                f"Skipped **{current_entry.title}** — enough votes to skip "
                f"({num_skips}/{skips_required}).",
            )
        else:
            skips_remaining = skips_required - num_skips
            await respond(
                interaction,
                f"Your vote to skip **{current_entry.title}** has been added.\n"
                f"{skips_remaining} more vote(s) needed.",
            )

    # ------------------------------------------------------------------ #
    #  /volume                                                             #
    # ------------------------------------------------------------------ #

    @bot.tree.command(
        name="volume",
        description="Set the playback volume (1–100), or check the current level.",
    )
    @app_commands.describe(level="Volume level from 1 to 100. Leave blank to check.")
    async def slash_volume(
        interaction: discord.Interaction, level: Optional[int] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("volume")
        player = await ctx.get_player()

        new_volume = "" if level is None else str(level)
        response = await bot.cmd_volume(
            ssd_=ctx.ssd, player=player, new_volume=new_volume
        )
        await invoke_response(interaction, response)
