"""
Response utilities for slash command interactions.

Handles the interaction response lifecycle: immediate send, deferred
followup, ephemeral errors, and optional auto-delete.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord

from musicbot.constants import MUSICBOT_EMBED_COLOR_ERROR, MUSICBOT_EMBED_COLOR_NORMAL

log = logging.getLogger(__name__)


def _schedule_delete(msg: discord.Message, delay: float) -> None:
    """Delete a message after delay seconds in a background task."""
    async def _delete() -> None:
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
    asyncio.create_task(_delete())


async def respond(
    interaction: discord.Interaction,
    content: str,
    *,
    title: Optional[str] = None,
    ephemeral: bool = False,
    delete_after: Optional[float] = None,
    color_hex: str = MUSICBOT_EMBED_COLOR_NORMAL,
) -> None:
    """
    Send an embed response to a slash command interaction.
    Works whether the interaction has been deferred or not.
    Non-ephemeral responses auto-delete per bot config when delete_after is unset.
    """
    embed = discord.Embed(
        description=content,
        color=discord.Colour.from_str(color_hex),
        title=title,
    )

    if interaction.response.is_done():
        msg = await interaction.followup.send(
            embed=embed,
            ephemeral=ephemeral,
            wait=True,
        )
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        msg = await interaction.original_response()

    if not ephemeral:
        effective_delay = delete_after
        if effective_delay is None:
            cfg = getattr(interaction.client, "config", None)
            if cfg is not None and getattr(cfg, "delete_messages", False):
                effective_delay = cfg.delete_delay_short
        if effective_delay:
            _schedule_delete(msg, effective_delay)


async def respond_with_embed(
    interaction: discord.Interaction,
    embed: discord.Embed,
    *,
    ephemeral: bool = False,
    delete_after: Optional[float] = None,
    view: Optional[discord.ui.View] = None,
) -> discord.Message:
    """
    Send a pre-built embed as a slash command response.
    Returns the sent message for later editing or deletion.
    """
    kwargs: dict = {"embed": embed, "ephemeral": ephemeral}
    if view is not None:
        kwargs["view"] = view

    if interaction.response.is_done():
        msg = await interaction.followup.send(**kwargs, wait=True)
    else:
        await interaction.response.send_message(**kwargs)
        msg = await interaction.original_response()

    if delete_after and not ephemeral:
        _schedule_delete(msg, delete_after)

    return msg


async def respond_error(
    interaction: discord.Interaction,
    content: str,
) -> None:
    """Send an ephemeral error embed. Only the invoker sees it."""
    embed = discord.Embed(
        description=content,
        color=discord.Colour.from_str(MUSICBOT_EMBED_COLOR_ERROR),
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def invoke_response(
    interaction: discord.Interaction,
    response: "Optional[discord.Embed]",
    *,
    view: Optional[discord.ui.View] = None,
) -> None:
    """
    Send a MusicBotResponse (Response / ErrorResponse) as an interaction
    response. Mirrors the prefix command auto-delete fallback from bot.py.
    """
    if response is None:
        return
    delete_after = getattr(response, "delete_after", None)
    if delete_after is None:
        cfg = getattr(interaction.client, "config", None)
        if cfg is not None and getattr(cfg, "delete_messages", False):
            delete_after = cfg.delete_delay_short
    await respond_with_embed(
        interaction,
        response,
        delete_after=delete_after,
        view=view,
    )


async def defer(
    interaction: discord.Interaction,
    *,
    ephemeral: bool = False,
) -> None:
    """
    Defer an interaction response for long-running operations.
    Must be called within 3 seconds of the interaction, before any other response.
    """
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=ephemeral)
