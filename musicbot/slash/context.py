"""
SlashContext: wraps discord.Interaction to provide the same context
objects (guild, author, player, permissions) that cmd_ methods use.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

import discord

from musicbot import exceptions
from musicbot.permissions import PermissionGroup

if TYPE_CHECKING:
    from musicbot.bot import MusicBot
    from musicbot.constructs import GuildSpecificData
    from musicbot.player import MusicPlayer


class SlashContext:
    """
    Provides guild, author, channel, permissions, and player access
    for a slash command interaction — mirroring the injected parameters
    that cmd_ methods receive from the prefix command dispatcher.
    """

    def __init__(self, interaction: discord.Interaction, bot: "MusicBot") -> None:
        self.interaction = interaction
        self.bot = bot
        self.guild: Optional[discord.Guild] = interaction.guild
        self.author: Union[discord.Member, discord.User] = interaction.user
        self.channel = interaction.channel
        self.ssd: Optional[GuildSpecificData] = (
            bot.server_data[interaction.guild.id] if interaction.guild else None
        )
        self.permissions: PermissionGroup = bot.permissions.for_user(interaction.user)

    def check_permission(self, command: str, sub: str = "") -> None:
        """Raise PermissionsError if the user cannot use this command."""
        if self.author.id == self.bot.config.owner_id:
            return
        if not self.permissions.can_use_command(command, sub):
            raise exceptions.PermissionsError(
                "This command is not allowed for your permissions group:  %(group)s",
                fmt_args={"group": self.permissions.name},
            )

    def require_guild(self) -> discord.Guild:
        """Return the guild or raise CommandError if not in a server."""
        if not self.guild:
            raise exceptions.CommandError(
                "This command can only be used in a server."
            )
        return self.guild

    def get_player_in(self) -> Optional["MusicPlayer"]:
        """Return the active player for this guild without creating one."""
        if self.guild:
            return self.bot.get_player_in(self.guild)
        return None

    async def get_player(self, create: bool = False) -> "MusicPlayer":
        """
        Return the guild's music player, creating one if needed.
        Raises CommandError if the user is not in a voice channel.
        """
        if not self.guild or not isinstance(self.author, discord.Member):
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )
        if not self.author.voice or not self.author.voice.channel:
            raise exceptions.CommandError(
                "This command requires you to be in a voice channel."
            )
        return await self.bot.get_player(
            self.author.voice.channel,
            create=create or self.permissions.summonplay,
        )
