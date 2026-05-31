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
    Non-ephemeral responses can be auto-deleted after delete_after seconds.
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

    if delete_after and not ephemeral:
        await asyncio.sleep(delete_after)
        try:
            await msg.delete()
        except discord.HTTPException:
            pass


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
    if interaction.response.is_done():
        msg = await interaction.followup.send(
            embed=embed,
            ephemeral=ephemeral,
            view=view,
            wait=True,
        )
    else:
        await interaction.response.send_message(
            embed=embed,
            ephemeral=ephemeral,
            view=view,
        )
        msg = await interaction.original_response()

    if delete_after and not ephemeral:
        await asyncio.sleep(delete_after)
        try:
            await msg.delete()
        except discord.HTTPException:
            pass

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
    response. Preserves the response's delete_after value if set.
    """
    if response is None:
        return
    delete_after = getattr(response, "delete_after", None)
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
