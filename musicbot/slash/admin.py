"""
Slash commands — Phase 7: admin.
/blockuser  /blocksong  /restart  /shutdown  /clean
/checkupdates  /resetplaylist  /setname  /setnick  /setavatar
/language  /id  /pldump
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands

from musicbot import exceptions
from musicbot.slash.context import SlashContext
from musicbot.slash.responses import defer, invoke_response, respond

if TYPE_CHECKING:
    from musicbot.bot import MusicBot

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Shutdown confirmation view                                          #
# ------------------------------------------------------------------ #

class ShutdownConfirmView(discord.ui.View):
    """Requires the owner to confirm before shutting the bot down."""

    def __init__(self, bot: "MusicBot", guild: discord.Guild) -> None:
        super().__init__(timeout=30)
        self.bot = bot
        self.guild = guild

    @discord.ui.button(label="Confirm Shutdown", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(
            content="Shutting down. Goodbye! \N{WAVING HAND SIGN}", view=None
        )
        player = self.bot.get_player_in(self.guild)
        if player and player.is_paused:
            player.resume()
        await self.bot.disconnect_all_voice_clients()
        raise exceptions.TerminateSignal()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(content="Shutdown cancelled.", view=None)


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register(bot: "MusicBot") -> None:
    """Register all admin slash commands with the bot's CommandTree."""

    # ---------------------------------------------------------------- #
    #  /blockuser                                                        #
    # ---------------------------------------------------------------- #

    blockuser_group = app_commands.Group(
        name="blockuser",
        description="Manage the user block list.",
    )

    @blockuser_group.command(
        name="add", description="Block a user from using DJ Roomba."
    )
    @app_commands.describe(user="The member to block.")
    async def blockuser_add(
        interaction: discord.Interaction, user: discord.Member
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("blockuser")
        if user.id == bot.config.owner_id:
            raise exceptions.CommandError("The owner cannot be added to the block list.")
        if bot.config.user_blocklist.is_blocked(user):
            raise exceptions.CommandError(f"**{user.name}** is already blocked.")
        bot.config.user_blocklist.add_item(str(user.id))
        await respond(interaction, f"Blocked **{user.name}** from using DJ Roomba.", ephemeral=True)

    @blockuser_group.command(
        name="remove", description="Unblock a user."
    )
    @app_commands.describe(user="The member to unblock.")
    async def blockuser_remove(
        interaction: discord.Interaction, user: discord.Member
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("blockuser")
        if not bot.config.user_blocklist.is_blocked(user):
            raise exceptions.CommandError(f"**{user.name}** is not in the block list.")
        bot.config.user_blocklist.remove_item(str(user.id))
        await respond(interaction, f"Unblocked **{user.name}**.", ephemeral=True)

    @blockuser_group.command(
        name="status", description="Check whether a user is blocked."
    )
    @app_commands.describe(user="The member to check.")
    async def blockuser_status(
        interaction: discord.Interaction, user: discord.Member
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("blockuser")
        blocked = bot.config.user_blocklist.is_blocked(user)
        status = "**is** blocked" if blocked else "is **not** blocked"
        await respond(interaction, f"**{user.name}** {status}.", ephemeral=True)

    bot.tree.add_command(blockuser_group)

    # ---------------------------------------------------------------- #
    #  /blocksong                                                        #
    # ---------------------------------------------------------------- #

    blocksong_group = app_commands.Group(
        name="blocksong",
        description="Manage the song block list.",
    )

    @blocksong_group.command(
        name="add",
        description="Block a song URL or title keyword. Omit to block the current song.",
    )
    @app_commands.describe(subject="URL or title keyword to block.")
    async def blocksong_add(
        interaction: discord.Interaction, subject: Optional[str] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("blocksong")
        guild = ctx.require_guild()
        _player = ctx.get_player_in()

        song_subject = subject or ""
        response = await bot.cmd_blocksong(
            ssd_=ctx.ssd,
            guild=guild,
            _player=_player,
            option="add",
            leftover_args=[],
            song_subject=song_subject,
        )
        await invoke_response(interaction, response)

    @blocksong_group.command(
        name="remove",
        description="Remove a song URL or keyword from the block list.",
    )
    @app_commands.describe(subject="URL or title keyword to unblock.")
    async def blocksong_remove(
        interaction: discord.Interaction, subject: Optional[str] = None
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("blocksong")
        guild = ctx.require_guild()
        _player = ctx.get_player_in()

        song_subject = subject or ""
        response = await bot.cmd_blocksong(
            ssd_=ctx.ssd,
            guild=guild,
            _player=_player,
            option="remove",
            leftover_args=[],
            song_subject=song_subject,
        )
        await invoke_response(interaction, response)

    bot.tree.add_command(blocksong_group)

    # ---------------------------------------------------------------- #
    #  /restart                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="restart",
        description="Restart DJ Roomba.",
    )
    @app_commands.describe(mode="How to restart. Default: soft (reload without process restart).")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Soft — reload without process restart (default)", value="soft"),
        app_commands.Choice(name="Full — restart the entire process",               value="full"),
        app_commands.Choice(name="Upgrade — update everything then restart",        value="upgrade"),
        app_commands.Choice(name="Upgit — update source code then restart",         value="upgit"),
        app_commands.Choice(name="Uppip — update pip packages then restart",        value="uppip"),
    ])
    async def slash_restart(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("restart")
        guild = ctx.require_guild()

        opt = mode.value if mode else "soft"
        _player = ctx.get_player_in()

        await respond(interaction, f"Restarting (`{opt}`)...")

        if _player and _player.is_paused:
            _player.resume()
        await bot.disconnect_all_voice_clients()

        restart_codes = {
            "soft":    exceptions.RestartCode.RESTART_SOFT,
            "full":    exceptions.RestartCode.RESTART_FULL,
            "upgrade": exceptions.RestartCode.RESTART_UPGRADE_ALL,
            "uppip":   exceptions.RestartCode.RESTART_UPGRADE_PIP,
            "upgit":   exceptions.RestartCode.RESTART_UPGRADE_GIT,
        }
        raise exceptions.RestartSignal(code=restart_codes[opt])

    # ---------------------------------------------------------------- #
    #  /shutdown                                                         #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="shutdown",
        description="Shut down DJ Roomba completely.",
    )
    async def slash_shutdown(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("shutdown")
        guild = ctx.require_guild()

        view = ShutdownConfirmView(bot, guild)
        await interaction.response.send_message(
            "Are you sure you want to shut down DJ Roomba?",
            view=view,
            ephemeral=True,
        )

    # ---------------------------------------------------------------- #
    #  /clean                                                            #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="clean",
        description="Remove DJ Roomba messages and command invocations from this channel.",
    )
    @app_commands.describe(count="Number of messages to search through (default 50, max 500).")
    async def slash_clean(
        interaction: discord.Interaction, count: int = 50
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("clean")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError("This command requires you to be in a server.")

        # Acknowledge before purging since purge can take a moment.
        await interaction.response.defer(ephemeral=True)

        search_range = min(abs(count), 500)
        prefix_list = bot.server_data[guild.id].command_prefix_list

        def is_command_invoke(msg: discord.Message) -> bool:
            for prefix in prefix_list:
                if msg.content.startswith(prefix) and msg.content[len(prefix):].strip():
                    return True
            return False

        delete_all = (
            interaction.channel.permissions_for(ctx.author).manage_messages
            or bot.config.owner_id == ctx.author.id
        )

        def check(msg: discord.Message) -> bool:
            if is_command_invoke(msg):
                return delete_all or msg.author == ctx.author
            return msg.author == bot.user

        if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            deleted = await interaction.channel.purge(limit=search_range, check=check)
            await interaction.followup.send(
                f"Deleted {len(deleted)} message(s).", ephemeral=True
            )
        else:
            raise exceptions.CommandError("Cannot clean messages in this channel type.")

    # ---------------------------------------------------------------- #
    #  /checkupdates                                                     #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="checkupdates",
        description="Check for DJ Roomba and dependency updates.",
    )
    async def slash_checkupdates(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("checkupdates")

        await defer(interaction)
        response = await bot.cmd_checkupdates(
            ssd_=ctx.ssd, channel=interaction.channel
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /resetplaylist                                                    #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="resetplaylist",
        description="Reset the auto playlist back to its default tracks.",
    )
    async def slash_resetplaylist(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("resetplaylist")
        guild = ctx.require_guild()
        player = await ctx.get_player()
        response = await bot.cmd_resetplaylist(
            ssd_=ctx.ssd, guild=guild, player=player
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /setname                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="setname",
        description="Change DJ Roomba's Discord username.",
    )
    @app_commands.describe(name="New username.")
    async def slash_setname(interaction: discord.Interaction, name: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("setname")
        response = await bot.cmd_setname(
            ssd_=ctx.ssd, leftover_args=[], name=name
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /setnick                                                          #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="setnick",
        description="Change DJ Roomba's nickname in this server.",
    )
    @app_commands.describe(nick="New server nickname.")
    async def slash_setnick(interaction: discord.Interaction, nick: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("setnick")
        guild = ctx.require_guild()
        response = await bot.cmd_setnick(
            ssd_=ctx.ssd,
            guild=guild,
            channel=interaction.channel,
            leftover_args=[],
            nick=nick,
        )
        await invoke_response(interaction, response)

    # ---------------------------------------------------------------- #
    #  /setavatar                                                        #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="setavatar",
        description="Change DJ Roomba's avatar to an image URL.",
    )
    @app_commands.describe(url="Direct URL to the new avatar image.")
    async def slash_setavatar(interaction: discord.Interaction, url: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("setavatar")

        await defer(interaction)

        import aiohttp
        try:
            async with bot.session.get(url) as resp:
                if resp.status != 200:
                    raise exceptions.CommandError("Could not fetch image from that URL.")
                data = await resp.read()
            if bot.user:
                await bot.user.edit(avatar=data)
        except exceptions.CommandError:
            raise
        except Exception as e:
            raise exceptions.CommandError(
                "Failed to change avatar: %(error)s",
                fmt_args={"error": str(e)},
            ) from e

        await respond(interaction, "Changed the bot's avatar.")

    # ---------------------------------------------------------------- #
    #  /language                                                         #
    # ---------------------------------------------------------------- #

    language_group = app_commands.Group(
        name="language",
        description="Manage the language used for bot messages in this server.",
    )

    @language_group.command(
        name="show", description="Show the current language and available options."
    )
    async def language_show(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("language")
        response = await bot.cmd_language(ssd_=ctx.ssd, subcmd="show")
        await invoke_response(interaction, response)

    @language_group.command(name="set", description="Set the server language.")
    @app_commands.describe(code="Language locale code, e.g. en_US.")
    async def language_set(interaction: discord.Interaction, code: str) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("language")
        response = await bot.cmd_language(ssd_=ctx.ssd, subcmd="set", lang_code=code)
        await invoke_response(interaction, response)

    @language_group.command(
        name="reset", description="Reset the server language to the bot default."
    )
    async def language_reset(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("language")
        response = await bot.cmd_language(ssd_=ctx.ssd, subcmd="reset")
        await invoke_response(interaction, response)

    bot.tree.add_command(language_group)

    # ---------------------------------------------------------------- #
    #  /id                                                               #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="id",
        description="Show the Discord ID of a user or channel.",
    )
    @app_commands.describe(
        user="User to look up.",
        channel="Channel to look up.",
    )
    async def slash_id(
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
    ) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("id")

        if user:
            await respond(
                interaction,
                f"ID for **{user.name}**: `{user.id}`",
                ephemeral=True,
            )
        elif channel:
            await respond(
                interaction,
                f"ID for **#{channel.name}**: `{channel.id}`",
                ephemeral=True,
            )
        else:
            await respond(
                interaction,
                f"Your ID: `{interaction.user.id}`",
                ephemeral=True,
            )

    # ---------------------------------------------------------------- #
    #  /pldump                                                           #
    # ---------------------------------------------------------------- #

    @bot.tree.command(
        name="pldump",
        description="Save the current queue to a playlist file.",
    )
    async def slash_pldump(interaction: discord.Interaction) -> None:
        ctx = SlashContext(interaction, bot)
        ctx.check_permission("pldump")
        guild = ctx.require_guild()

        if not isinstance(ctx.author, discord.Member):
            raise exceptions.CommandError("This command requires you to be in a server.")

        player = await ctx.get_player()
        response = await bot.cmd_pldump(
            ssd_=ctx.ssd,
            channel=interaction.channel,
            guild=guild,
            author=ctx.author,
            player=player,
        )
        await invoke_response(interaction, response)
