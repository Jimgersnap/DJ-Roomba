"""
Slash commands — Phase 6: utility.
/np  /botinfo  /botversion  /uptime  /latency  /perms
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.constants import (
    VERSION as BOTVERSION,
    DEFAULT_BOT_NAME,
    MUSICBOT_EMBED_COLOR_NORMAL,
)
from musicbot.entry import StreamPlaylistEntry
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import invoke_response, respond, schedule_delete
from musicbot.utils import format_song_duration

if TYPE_CHECKING:
    from musicbot.bot import MusicBot
    from musicbot.player import MusicPlayer

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Now Playing view with control buttons                               #
# ------------------------------------------------------------------ #

class NowPlayingView(discord.ui.View):
    """
    Attaches ⏸/▶ · ⏭ · 🔁 buttons to the now-playing embed.
    Any server member may use them.
    """

    def __init__(
        self,
        bot: "MusicBot",
        player: "MusicPlayer",
        *,
        auto_delete: bool = True,
    ) -> None:
        super().__init__(timeout=60 if auto_delete else None)
        self.bot = bot
        self.player = player
        self.message: Optional[discord.Message] = None
        self._auto_delete = auto_delete
        self._refresh_pause_label()

    def _refresh_pause_label(self) -> None:
        if self.player.is_paused:
            self.pause_resume_btn.label = "▶ Resume"
            self.pause_resume_btn.style = discord.ButtonStyle.green
        else:
            self.pause_resume_btn.label = "⏸ Pause"
            self.pause_resume_btn.style = discord.ButtonStyle.secondary

    def _refresh_repeat_label(self) -> None:
        if self.player.repeatsong:
            self.repeat_btn.label = "🔁 Song (on)"
            self.repeat_btn.style = discord.ButtonStyle.blurple
        else:
            self.repeat_btn.label = "🔁 Repeat"
            self.repeat_btn.style = discord.ButtonStyle.secondary

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
            if self._auto_delete:
                cfg = getattr(self.bot, "config", None)
                if cfg is not None and getattr(cfg, "delete_messages", False):
                    schedule_delete(self.message, cfg.delete_delay_short)

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause_resume_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.player.is_paused:
            self.player.resume()
        elif self.player.is_playing:
            self.player.pause()
        else:
            await interaction.response.send_message(
                "Nothing is playing right now.", ephemeral=True
            )
            return
        self._refresh_pause_label()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.secondary)
    async def skip_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not self.player.is_playing and not self.player.is_paused:
            await interaction.response.send_message(
                "Nothing is playing right now.", ephemeral=True
            )
            return
        self.player.skip()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="🔁 Repeat", style=discord.ButtonStyle.secondary)
    async def repeat_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.player.repeatsong = not self.player.repeatsong
        self._refresh_repeat_label()
        await interaction.response.edit_message(view=self)


# ------------------------------------------------------------------ #
#  Now Playing embed builder                                           #
# ------------------------------------------------------------------ #

def _build_np_embed(player: "MusicPlayer") -> discord.Embed:
    entry = player.current_entry
    streaming = isinstance(entry, StreamPlaylistEntry)

    song_progress = format_song_duration(player.progress)
    song_total = (
        format_song_duration(entry.duration_td)
        if entry.duration is not None
        else "~"
    )
    prog_str = (
        f"`({song_progress})`"
        if streaming
        else f"`({song_progress} / {song_total})`"
    )

    percentage = 0.0
    if entry.duration and entry.duration_td.total_seconds() > 0:
        percentage = player.progress / entry.duration_td.total_seconds()

    bar_length = 30
    bar = "".join(
        "■" if percentage >= (i / bar_length) else "□"
        for i in range(bar_length)
    )

    added_by = entry.author.name if entry.author else "autoplaylist"

    embed = discord.Embed(
        title=entry.title,
        color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_NORMAL),
    )
    embed.add_field(name="Added By:", value=f"`{added_by}`", inline=False)
    embed.add_field(name="Progress:", value=f"{prog_str}\n{bar}", inline=False)

    display_url = entry.info.input_subject if streaming else entry.url
    if display_url and len(display_url) <= 1024:
        embed.add_field(name="URL:", value=display_url, inline=False)

    if entry.thumbnail_url:
        embed.set_image(url=entry.thumbnail_url)

    return embed


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register(bot: "MusicBot") -> None:
    """Register all utility slash commands with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  /np                                                               #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="nowplaying",
        description="Refresh the now-playing message to the bottom of chat.",
    )
    async def slash_np(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("np")
        guild = ctx.require_guild()

        player = ctx.get_player_in()
        if player is None or not player.current_entry:
            raise exceptions.CommandError("Nothing is playing right now.")

        # Delete the existing auto-NP message to avoid redundancy.
        old_np_msg = bot.server_data[guild.id].last_np_msg
        if old_np_msg:
            try:
                await old_np_msg.delete()
            except discord.HTTPException:
                pass
            bot.server_data[guild.id].last_np_msg = None

        embed = _build_np_embed(player)
        view = NowPlayingView(bot, player, auto_delete=False)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg
        bot.server_data[guild.id].last_np_msg = msg

    # ---------------------------------------------------------------- #
    #  /botinfo                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="botinfo",
        description="Show DJ Roomba version, links, and credits.",
    )
    async def slash_botinfo(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        response = await bot.cmd_botinfo(message=None)
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /botversion                                                       #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="botversion",
        description="Show the current DJ Roomba version.",
    )
    async def slash_botversion(interaction: discord.Interaction) -> None:
        await respond(
            interaction,
            f"DJ-Roomba GitHub: <https://github.com/Jimgersnap/DJ-Roomba>\n"
            f"Current version: `{BOTVERSION}`",
        )

    # ---------------------------------------------------------------- #
    #  /uptime                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="uptime",
        description="Show how long DJ Roomba has been running.",
    )
    async def slash_uptime(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        response = await bot.cmd_uptime(ssd_=ctx.ssd)
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /latency                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="latency",
        description="Show API and voice latency.",
    )
    async def slash_latency(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        guild = ctx.require_guild()
        response = await bot.cmd_latency(ssd_=ctx.ssd, guild=guild)
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /perms                                                            #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="perms",
        description="Show your permissions, or another member's.",
    )
    @app_commands.describe(user="Member to check permissions for. Defaults to you.")
    async def slash_perms(
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("perms")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a server."
            )

        target = user or ctx.author
        perms = bot.permissions.for_user(target)

        if target == ctx.author:
            content = (
                f"Your command permissions in **{guild.name}** are:\n"
                f"```\n{perms.format(for_user=True)}\n```"
            )
        else:
            content = (
                f"Command permissions for **{target.name}** in **{guild.name}**:\n"
                f"```\n{perms.format()}\n```"
            )

        # Send ephemeral — permissions info is personal, keeps channels clean.
        embed = discord.Embed(
            description=content,
            color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_NORMAL),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
