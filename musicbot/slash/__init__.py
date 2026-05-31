"""
DJ Roomba slash commands package.
Call setup() once from MusicBot.__init__ to register all commands
and the global error handler with the bot's CommandTree.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.slash.responses import respond_error

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


def _format_error(error: exceptions.MusicbotException) -> str:
    """Format a MusicbotException message with its fmt_args."""
    msg = error.message
    if error.fmt_args:
        try:
            msg = msg % error.fmt_args
        except (KeyError, TypeError):
            pass
    return msg


def setup(bot: "MusicBot") -> None:
    """Register all slash commands and the global error handler."""
    from musicbot.slash import playback, queue
    playback.register(bot)
    queue.register(bot)

    @bot.tree.error
    async def on_tree_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)
        if isinstance(original, exceptions.MusicbotException):
            await respond_error(interaction, _format_error(original))
        else:
            log.exception("Unhandled slash command error", exc_info=error)
            await respond_error(interaction, "An unexpected error occurred.")
