"""
Slash commands — Phase 4: playback options.
/repeat  /seek  /speed  /playnow  /playnext  /shuffleplay  /search
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.constants import MUSICBOT_EMBED_COLOR_NORMAL
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import defer, invoke_response, respond, schedule_delete
from musicbot.utils import format_song_duration

if TYPE_CHECKING:
    from musicbot.bot import MusicBot
    from musicbot.player import MusicPlayer
    from musicbot.permissions import PermissionGroup

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Search results select menu                                          #
# ------------------------------------------------------------------ #

class SearchView(discord.ui.View):
    """
    Presents search results as a Select dropdown.
    The invoking user picks a result and it is added to the queue.
    """

    def __init__(
        self,
        bot: "MusicBot",
        player: "MusicPlayer",
        entries: list,
        channel: discord.abc.Messageable,
        guild: discord.Guild,
        author: discord.Member,
        permissions: "PermissionGroup",
    ) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.player = player
        self.entries = entries
        self.channel = channel
        self.guild = guild
        self.author = author
        self.permissions = permissions

        options = []
        for i, entry in enumerate(entries[:25], 1):
            title = entry.get("title", "Unknown")
            label = f"{i}. {title}"[:100]
            duration = format_song_duration(entry.duration_td)
            options.append(
                discord.SelectOption(label=label, description=duration, value=str(i - 1))
            )

        self.result_select.options = options

    async def on_timeout(self) -> None:
        self.result_select.disabled = True

    @discord.ui.select(placeholder="Pick a result to add it to the queue...")
    async def result_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ) -> None:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Only the person who searched can pick a result.", ephemeral=True
            )
            return

        await interaction.response.defer()

        entry = self.entries[int(select.values[0])]
        title = entry.get("title", "Unknown")
        url = entry.get("url") or entry.get("webpage_url", "")

        await self.bot._cmd_play(
            None,
            self.player,
            self.channel,
            self.guild,
            self.author,
            self.permissions,
            [],
            url,
            head=False,
        )

        result_embed = discord.Embed(
            description=f"Added **{title}** to the queue.",
            color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_NORMAL),
        )
        await interaction.message.edit(embed=result_embed, view=None)
        cfg = getattr(interaction.client, "config", None)
        if cfg is not None and getattr(cfg, "delete_messages", False):
            schedule_delete(interaction.message, cfg.delete_delay_short)


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register(bot: "MusicBot") -> None:
    """Register all playback-options slash commands with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  /repeat                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="repeat",
        description="Set the repeat mode: off, song, or playlist.",
    )
    @app_commands.describe(mode="What to repeat. Omit to cycle through modes.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off — stop repeating",         value="off"),
        app_commands.Choice(name="Song — loop the current song", value="song"),
        app_commands.Choice(name="Playlist — loop the queue",    value="all"),
    ])
    async def slash_repeat(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("repeat")
        player = await ctx.get_player()

        option = mode.value if mode else ""
        response = await bot.cmd_repeat(ssd_=ctx.ssd, player=player, option=option)
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /seek                                                             #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="seek",
        description="Jump to a position in the current song.",
    )
    @app_commands.describe(
        time='Position to seek to, e.g. "1:30" or "90". Prefix with + or - for relative seek.'
    )
    async def slash_seek(interaction: discord.Interaction, time: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("seek")
        guild = ctx.require_guild()
        player = await ctx.get_player()

        response = await bot.cmd_seek(
            ssd_=ctx.ssd,
            guild=guild,
            player=player,
            leftover_args=[],
            seek_time=time,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /speed                                                            #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="speed",
        description="Change the playback speed of the current track (0.5–2.0).",
    )
    @app_commands.describe(rate="Playback speed multiplier, e.g. 1.5 for 50% faster.")
    async def slash_speed(interaction: discord.Interaction, rate: float) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("speed")
        guild = ctx.require_guild()
        player = await ctx.get_player()

        response = await bot.cmd_speed(
            ssd_=ctx.ssd,
            guild=guild,
            player=player,
            new_speed=str(rate),
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /playnext                                                         #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="playnext",
        description="Add a song to the front of the queue so it plays next.",
    )
    @app_commands.describe(query="Song name, URL, or playlist link.")
    async def slash_playnext(interaction: discord.Interaction, query: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("playnext")

        await defer(interaction)
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player(create=True)

        response = await bot._cmd_play(
            None,
            player,
            interaction.channel,
            guild,
            ctx.author,
            ctx.permissions,
            [],
            query,
            head=True,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /playnow                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="playnow",
        description="Play a song immediately, skipping whatever is currently playing.",
    )
    @app_commands.describe(query="Song name, URL, or playlist link.")
    async def slash_playnow(interaction: discord.Interaction, query: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("playnow")

        await defer(interaction)
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player(create=True)

        response = await bot._cmd_play(
            None,
            player,
            interaction.channel,
            guild,
            ctx.author,
            ctx.permissions,
            [],
            query,
            head=True,
            skip_playing=True,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /shuffleplay                                                      #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="shuffleplay",
        description="Add a playlist to the queue and shuffle it immediately.",
    )
    @app_commands.describe(query="Playlist URL or search terms.")
    async def slash_shuffleplay(interaction: discord.Interaction, query: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("shuffleplay")

        await defer(interaction)
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player(create=True)

        response = await bot._cmd_play(
            None,
            player,
            interaction.channel,
            guild,
            ctx.author,
            ctx.permissions,
            [],
            query,
            head=False,
            shuffle_entries=True,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /search                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="search",
        description="Search YouTube and pick a result to add to the queue.",
    )
    @app_commands.describe(query="What to search for.")
    async def slash_search(interaction: discord.Interaction, query: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("search")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        await defer(interaction)

        guild = ctx.require_guild()
        player = await ctx.get_player(create=True)

        if (
            ctx.permissions.max_songs
            and player.playlist.count_for_user(ctx.author) > ctx.permissions.max_songs
        ):
            raise exceptions.PermissionsError(
                "You have reached your playlist item limit (%(max)s)",
                fmt_args={"max": ctx.permissions.max_songs},
            )

        if player.karaoke_mode and not ctx.permissions.bypass_karaoke_mode:
            raise exceptions.PermissionsError(
                "Karaoke mode is enabled, please try again when it's disabled."
            )

        bot._do_song_blocklist_check(query)

        num_results = min(
            bot.config.defaultsearchresults,
            ctx.permissions.max_search_items,
        )
        search_query = f"ytsearch{num_results}:{query}"

        try:
            info = await bot.downloader.extract_info(
                search_query, download=False, process=True
            )
        except Exception as e:
            log.warning("Search failed: %s", e)
            raise exceptions.CommandError(
                "Search failed. Please try again or use a direct URL with `/play`."
            ) from e

        if not info:
            raise exceptions.CommandError("No results found.")

        entries = info.get_entries_objects()
        if not entries:
            raise exceptions.CommandError("No results found.")

        embed = discord.Embed(
            title=f"Search results for: {query}",
            color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_NORMAL),
        )
        lines = []
        for i, entry in enumerate(entries[:25], 1):
            title = entry.get("title", "Unknown")
            duration = format_song_duration(entry.duration_td)
            lines.append(f"`{i}.` **{title}** `{duration}`")
        embed.description = "\n".join(lines)

        view = SearchView(
            bot=bot,
            player=player,
            entries=entries[:25],
            channel=interaction.channel,
            guild=guild,
            author=ctx.author,
            permissions=ctx.permissions,
        )

        await interaction.followup.send(embed=embed, view=view)
