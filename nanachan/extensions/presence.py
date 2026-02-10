from random import choice
from uuid import UUID

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import Embed, is_admin
from nanachan.nanapi.client import get_nanapi
from nanachan.nanapi.model import NewPresenceBody, PresencePresenceType


@app_commands.guild_only()
class Presence(NanaGroupCog, name='Presence', group_name='presence'):
    """Make people believe that {bot_name} is watching your favorite show"""

    emoji = '👀'

    def __init__(self, bot: Bot):
        self.bot = bot
        self.current_presence_id: UUID | None = None

    @Cog.listener()
    async def on_ready(self):
        if not self.loop_presence.is_running():
            self.loop_presence.start()

    async def cog_unload(self):
        self.loop_presence.cancel()

    @tasks.loop(seconds=300)
    async def loop_presence(self):
        resp = await get_nanapi().presence.presence_get_presences()
        resp = resp.raise_exc()

        presences_data = resp.result
        presences_data = [p for p in presences_data if p.id != self.current_presence_id]
        if len(presences_data) == 0:
            return

        presence = choice(presences_data)
        type = getattr(discord.ActivityType, presence.type.lower())
        activity = discord.Activity(type=type, name=presence.name)

        await self.bot.change_presence(activity=activity)
        self.current_presence_id = presence.id

    @app_commands.command()
    async def list(self, interaction: Interaction):
        """Get rotating presences list"""
        await interaction.response.defer()
        resp = await get_nanapi().presence.presence_get_presences()
        resp = resp.raise_exc()

        presences_data = resp.result
        if len(presences_data) == 0:
            await interaction.followup.send('No presences found')
            return

        presences = [
            f'`{presence.id}` {presence.type} {presence.name}' for presence in presences_data
        ]
        embed = Embed(description='\n'.join(presences))
        await interaction.followup.send(embed=embed)

    @app_commands.command()
    async def add(self, interaction: Interaction, type: PresencePresenceType, *, name: str):
        """Add presence to rotating list"""
        await interaction.response.defer()
        resp = await get_nanapi().presence.presence_new_presence(
            NewPresenceBody(type=type.value, name=name)
        )
        resp = resp.raise_exc()

        await interaction.followup.send('👌')

    @app_commands.command(description='(Admin only) Remove presence from rotating list')
    @app_commands.check(is_admin)
    async def remove(self, interaction: Interaction, id: str):
        uuid = UUID(id)
        await interaction.response.defer()
        resp = await get_nanapi().presence.presence_delete_presence(uuid)
        resp = resp.raise_exc()

        await interaction.followup.send('👌')

    @app_commands.command(description='(Admin only) Force set bot presence')
    @app_commands.check(is_admin)
    async def set(self, interaction: Interaction[Bot], type: PresencePresenceType, *, name: str):
        if type.lower() not in ('playing', 'listening', 'watching'):
            raise commands.BadArgument('Type not in (`playing`, `listening`, `watching`)')

        self.loop_presence.cancel()
        activity = discord.Activity(type=getattr(discord.ActivityType, type.lower()), name=name)
        await interaction.response.send_message(
            f'*Remember to restart rotating presences with `/{self.auto.qualified_name}`*'
        )
        await interaction.client.change_presence(activity=activity)

    @app_commands.command(description='(Admin only) Start rotating presences')
    @app_commands.check(is_admin)
    async def auto(self, interaction: Interaction):
        if self.loop_presence.is_running():
            raise app_commands.AppCommandError('Already using rotating presences.')

        self.loop_presence.start()
        await interaction.response.send_message('👌')


async def setup(bot: Bot):
    await bot.add_cog(Presence(bot))
