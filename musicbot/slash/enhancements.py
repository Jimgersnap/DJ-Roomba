"""
Slash commands — Phase 8: enhancements and remaining commands.
"Add to Queue" message context menu, /stream, /autoplaylist group.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import defer, invoke_response, respond

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+")


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register(bot: "MusicBot") -> None:
    """Register Phase 8 enhancements with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  "Add to Queue" message context menu                              #
    # ---------------------------------------------------------------- #

    @bot.tree.context_menu(name="Add to Queue")
    async def add_to_queue_ctx(
        interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """Right-click any message → Apps → Add to Queue."""
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("play")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a server."
            )

        # Extract the first URL from the message.
        match = _URL_RE.search(message.content)
        if not match:
            await interaction.response.send_message(
                "No URL found in that message.", ephemeral=True
            )
            return

        url = match.group(0).rstrip(".,;!?)")  # strip common trailing punctuation
        guild = ctx.require_guild()

        await defer(interaction)
        player = await ctx.get_player(create=True)

        response = await bot._cmd_play(
            None,
            player,
            interaction.channel,
            guild,
            ctx.author,
            ctx.permissions,
            [],
            url,
            head=False,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /stream                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="stream",
        description="Stream a live URL directly without downloading (Twitch, radio, etc.).",
    )
    @app_commands.describe(url="Stream URL to add to the queue.")
    async def slash_stream(interaction: discord.Interaction, url: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("stream")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        await defer(interaction)

        player = await ctx.get_player(create=True)

        if (
            ctx.permissions.max_songs
            and player.playlist.count_for_user(ctx.author) >= ctx.permissions.max_songs
        ):
            raise exceptions.PermissionsError(
                "You have reached your enqueued song limit (%(max)s)",
                fmt_args={"max": ctx.permissions.max_songs},
            )

        if player.karaoke_mode and not ctx.permissions.bypass_karaoke_mode:
            raise exceptions.PermissionsError(
                "Karaoke mode is enabled, please try again when it's disabled."
            )

        try:
            info = await bot.downloader.extract_info(
                url, download=False, process=True, as_stream=True
            )
        except Exception as e:
            log.exception("Failed to get info from stream: %s", url)
            raise exceptions.CommandError(
                "Failed to extract stream info: %(error)s",
                fmt_args={"error": str(e)},
            ) from e

        if info.has_entries:
            raise exceptions.CommandError("Streaming playlists is not supported.")

        bot._do_song_blocklist_check(info.url)
        if info.url != info.title:
            bot._do_song_blocklist_check(info.title)

        await player.playlist.add_stream_from_info(
            info,
            channel=interaction.channel,
            author=ctx.author,
            head=False,
        )

        if player.is_stopped:
            player.play()

        await respond(
            interaction,
            f"Connected to the stream. **{info.title}**\n\nEnd the stream with `/skip`.",
        )

    # ---------------------------------------------------------------- #
    #  /autoplaylist                                                     #
    # ---------------------------------------------------------------- #

    apl_group = app_commands.Group(
        name="autoplaylist",
        description="Manage the auto playlist that plays when the queue is empty.",
    )

    @apl_group.command(
        name="add",
        description="Add a URL to the auto playlist. Omit to add the current song.",
    )
    @app_commands.describe(url="URL to add. Leave blank to add the currently playing song.")
    async def apl_add(
        interaction: discord.Interaction, url: Optional[str] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("autoplaylist")
        guild = ctx.require_guild()

        track_url = url
        if not track_url:
            _player = ctx.get_player_in()
            if not _player or not _player.current_entry:
                raise exceptions.CommandError(
                    "No song is currently playing. Provide a URL to add."
                )
            track_url = _player.current_entry.url

        valid = bot.downloader.get_url_or_none(track_url)
        if not valid:
            raise exceptions.CommandError("That doesn't look like a valid URL.")

        bot._do_song_blocklist_check(valid)

        apl = bot.server_data[guild.id].autoplaylist
        if valid in apl:
            raise exceptions.CommandError("That song is already in the auto playlist.")

        await apl.add_track(valid)
        await respond(interaction, f"Added `{valid}` to the auto playlist.")

    @apl_group.command(
        name="remove",
        description="Remove a URL from the auto playlist. Omit to remove the current song.",
    )
    @app_commands.describe(url="URL to remove. Leave blank to remove the currently playing song.")
    async def apl_remove(
        interaction: discord.Interaction, url: Optional[str] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("autoplaylist")
        guild = ctx.require_guild()

        track_url = url
        if not track_url:
            _player = ctx.get_player_in()
            if not _player or not _player.current_entry:
                raise exceptions.CommandError(
                    "No song is currently playing. Provide a URL to remove."
                )
            track_url = _player.current_entry.url

        apl = bot.server_data[guild.id].autoplaylist
        if track_url not in apl:
            raise exceptions.CommandError("That song is not in the auto playlist.")

        await apl.remove_track(
            track_url,
            ex=UserWarning(f"Removed via slash command by {ctx.author.id}/{ctx.author.name}"),
            delete_from_ap=True,
        )
        await respond(interaction, f"Removed `{track_url}` from the auto playlist.")

    @apl_group.command(
        name="show",
        description="Show the current auto playlist and all available playlists.",
    )
    async def apl_show(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("autoplaylist")

        response = await bot.cmd_autoplaylist(
            ssd_=ctx.ssd,
            guild=ctx.require_guild(),
            author=ctx.author,
            channel=interaction.channel,
            voice_channel=None,
            message=None,
            _player=ctx.get_player_in(),
            player=ctx.get_player_in(),
            option="show",
            opt_url="",
        )
        await invoke_response(interaction, response)

    @apl_group.command(
        name="restart",
        description="Reload the auto playlist from disk and refresh the player queue.",
    )
    async def apl_restart(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("autoplaylist")
        guild = ctx.require_guild()

        apl = bot.server_data[guild.id].autoplaylist
        await apl.load(force=True)

        _player = ctx.get_player_in()
        if _player:
            _player.autoplaylist = list(apl)

        await respond(
            interaction,
            f"Reloaded auto playlist from `{apl.filename}`.",
        )

    bot.tree.add_command(apl_group)
