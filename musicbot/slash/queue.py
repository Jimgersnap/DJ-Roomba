"""
Slash commands — Phase 3: queue management.
/queue  /clearqueue  /shufflequeue  /removequeue  /promote  /move
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, List, Optional

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.constants import MUSICBOT_EMBED_COLOR_NORMAL
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import defer, invoke_response, respond, respond_with_embed
from musicbot.utils import format_song_duration

if TYPE_CHECKING:
    from musicbot.bot import MusicBot
    from musicbot.player import MusicPlayer

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Queue embed builder                                                 #
# ------------------------------------------------------------------ #

def _build_queue_embed(
    bot: "MusicBot",
    player: "MusicPlayer",
    page: int,
) -> tuple[discord.Embed, int]:
    """
    Build the queue embed for a given page number.
    Returns (embed, pages_total) where pages_total is the max page index.
    """
    total = len(player.playlist.entries)
    pages_total = math.ceil(total / bot.config.queue_length) - 1 if total else 0

    # Currently playing section.
    current_section = ""
    if player.current_entry:
        progress = format_song_duration(player.progress)
        duration = (
            format_song_duration(player.current_entry.duration_td)
            if player.current_entry.duration is not None
            else "unknown duration"
        )
        added_by = (
            player.current_entry.author.name
            if player.current_entry.author
            else "autoplaylist"
        )
        current_section = (
            f"Currently playing: **{player.current_entry.title}** "
            f"added by **{added_by}**. `({progress} / {duration})`\n\n"
        )

    # Queue entries for this page.
    start = bot.config.queue_length * page
    end = start + bot.config.queue_length
    tracks = ""
    for idx, entry in enumerate(list(player.playlist.entries)[start:end], start + 1):
        if entry == player.current_entry:
            continue
        added_by = entry.author.name if entry.channel and entry.author else "autoplaylist"
        title = entry.title[:40] + " ..." if len(entry.title) > 40 else entry.title
        line = f"`{idx}` — **{title}** added by **{added_by}**\n"
        if len(tracks) + len(line) < 3840:
            tracks += line

    if total:
        body = tracks
        if pages_total > 0:
            body += f"\nPage {page + 1}/{pages_total + 1}"
    else:
        body = "The queue is empty."

    embed = discord.Embed(
        description=f"{current_section}{body}",
        title="Queue",
        color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_NORMAL),
    )
    return embed, pages_total


# ------------------------------------------------------------------ #
#  Paginated queue view                                                #
# ------------------------------------------------------------------ #

class QueueView(discord.ui.View):
    """
    Adds ◀ ▶ navigation buttons to the queue embed.
    Buttons are disabled when there is only one page.
    """

    def __init__(
        self,
        bot: "MusicBot",
        player: "MusicPlayer",
        page: int,
        pages_total: int,
    ) -> None:
        super().__init__(timeout=120)
        self.bot = bot
        self.player = player
        self.page = page
        self.pages_total = pages_total
        self.message: Optional[discord.Message] = None

        if pages_total == 0:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True

    async def _update(self, interaction: discord.Interaction) -> None:
        embed, self.pages_total = _build_queue_embed(self.bot, self.player, self.page)
        if self.pages_total == 0:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
        else:
            self.prev_btn.disabled = False
            self.next_btn.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        log.exception("QueueView button error", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong updating the queue. Try `/queue` again.",
                ephemeral=True,
            )
        except discord.HTTPException:
            pass

    async def on_timeout(self) -> None:
        self.prev_btn.disabled = True
        self.next_btn.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = self.pages_total if self.page <= 0 else self.page - 1
        await self._update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = 0 if self.page >= self.pages_total else self.page + 1
        await self._update(interaction)


# ------------------------------------------------------------------ #
#  Autocomplete helpers                                                #
# ------------------------------------------------------------------ #

async def _queue_position_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[int]]:
    """Autocomplete returning current queue entries by position."""
    bot: "MusicBot" = interaction.client  # type: ignore[assignment]
    if not interaction.guild:
        return []
    player = bot.get_player_in(interaction.guild)
    if not player or not player.playlist.entries:
        return []

    choices = []
    for i, entry in enumerate(player.playlist.entries, 1):
        label = f"{i}. {entry.title}"[:100]
        if current and current not in str(i) and current.lower() not in label.lower():
            continue
        choices.append(app_commands.Choice(name=label, value=i))
        if len(choices) >= 25:
            break
    return choices


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register(bot: "MusicBot") -> None:
    """Register all queue slash commands with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  /queue                                                            #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="queue",
        description="Show the current song queue with page navigation.",
    )
    @app_commands.describe(page="Page number to jump to (default: 1).")
    async def slash_queue(
        interaction: discord.Interaction, page: int = 1
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("queue")
        player = await ctx.get_player()

        total = len(player.playlist.entries)
        if not total and not player.current_entry:
            raise exceptions.CommandError(
                "There are no songs queued! Queue something with `/play`."
            )

        page_index = max(0, page - 1)
        pages_total = math.ceil(total / bot.config.queue_length) - 1 if total else 0

        if page_index > pages_total:
            raise exceptions.CommandError(
                f"Page {page} is out of range. There are **{pages_total + 1}** page(s)."
            )

        embed, pages_total = _build_queue_embed(bot, player, page_index)
        view = QueueView(bot, player, page_index, pages_total)
        msg = await respond_with_embed(interaction, embed, view=view)
        view.message = msg

    # ---------------------------------------------------------------- #
    #  /clearqueue                                                       #
    # ---------------------------------------------------------------- #

    @bot.tree.command(name="clearqueue", description="Clear all songs from the queue.")
    async def slash_clearqueue(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("clear")
        guild = ctx.require_guild()
        _player = ctx.get_player_in()

        response = await bot.cmd_clear(ssd_=ctx.ssd, _player=_player, guild=guild)
        if response:
            await invoke_response(interaction, response)
        else:
            await respond(interaction, "Queue cleared.")

    # ---------------------------------------------------------------- #
    #  /shufflequeue                                                     #
    # ---------------------------------------------------------------- #

    @bot.tree.command(name="shufflequeue", description="Shuffle the song queue.")
    async def slash_shufflequeue(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("shuffle")
        player = await ctx.get_player()

        if not player.playlist.entries:
            raise exceptions.CommandError("There's nothing in the queue to shuffle.")

        player.playlist.shuffle()
        await respond(interaction, "The queue has been shuffled.")

    # ---------------------------------------------------------------- #
    #  /removequeue                                                      #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="removequeue",
        description="Remove a song from the queue by position.",
    )
    @app_commands.describe(position="Position of the song to remove.")
    @app_commands.autocomplete(position=_queue_position_autocomplete)
    async def slash_removequeue(
        interaction: discord.Interaction, position: int
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("remove")

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )

        player = await ctx.get_player()

        if not player.playlist.entries:
            raise exceptions.CommandError("There's nothing in the queue to remove.")

        if position < 1 or position > len(player.playlist.entries):
            raise exceptions.CommandError(
                f"Invalid position. The queue has **{len(player.playlist.entries)}** song(s)."
            )

        entry = player.playlist.get_entry_at_index(position - 1)

        if not ctx.permissions.remove and entry.author != ctx.author:
            raise exceptions.PermissionsError(
                "You can only remove songs you added yourself."
            )

        player.playlist.delete_entry_at_index(position - 1)
        added_by = f" added by **{entry.author.name}**" if entry.author else ""
        await respond(
            interaction, f"Removed **{entry.title}**{added_by} from the queue."
        )

    # ---------------------------------------------------------------- #
    #  /promote                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="promote",
        description="Move a queued song to the front so it plays next.",
    )
    @app_commands.describe(position="Position of the song to promote.")
    @app_commands.autocomplete(position=_queue_position_autocomplete)
    async def slash_promote(
        interaction: discord.Interaction, position: Optional[int] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("promote")
        player = await ctx.get_player()

        pos_str = str(position) if position is not None else ""
        response = await bot.cmd_promote(
            ssd_=ctx.ssd, player=player, position=pos_str
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /move                                                             #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="move",
        description="Move a song from one queue position to another.",
    )
    @app_commands.describe(
        from_position="Current position of the song.",
        to_position="Position to move it to.",
    )
    @app_commands.autocomplete(from_position=_queue_position_autocomplete)
    async def slash_move(
        interaction: discord.Interaction,
        from_position: int,
        to_position: int,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("move")
        player = await ctx.get_player()
        queue_len = len(player.playlist.entries)

        if not player.current_entry:
            raise exceptions.CommandError(
                "There are no songs queued. Queue something with `/play`."
            )

        for pos, label in [(from_position, "from"), (to_position, "to")]:
            if pos < 1 or pos > queue_len:
                raise exceptions.CommandError(
                    f"The {label} position ({pos}) is outside the queue range (1–{queue_len})."
                )

        song = player.playlist.delete_entry_at_index(from_position - 1)
        player.playlist.insert_entry_at_index(to_position - 1, song)

        await respond(
            interaction,
            f"Moved **{song.title}** from position {from_position} to {to_position}.",
        )
