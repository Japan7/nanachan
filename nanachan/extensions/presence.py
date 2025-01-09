from random import choice
from uuid import UUID

import discord
from discord.ext import commands, tasks

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Embed
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import NewPresenceBody, PresencePresenceType
from nanachan.settings import PREFIX


class Presence(Cog, name='Presence'):
    """Make people believe that {bot_name} is watching your favorite show"""

    emoji = '👀'

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.current_presence_id = None

    @Cog.listener()
    async def on_ready(self):
        if not self.loop_presence.is_running():
            self.loop_presence.start()

    async def cog_unload(self):
        self.loop_presence.cancel()

    @tasks.loop(seconds=300)
    async def loop_presence(self):
        resp = await get_nanapi().presence.presence_get_presences()
        if not success(resp):
            raise RuntimeError(resp.result)
        presences_data = resp.result
        presences_data = [p for p in presences_data if p.id != self.current_presence_id]
        if len(presences_data) == 0:
            return
        presence = choice(presences_data)
        if presence is not None:
            type = getattr(discord.ActivityType, presence.type.lower())
            activity = discord.Activity(type=type, name=presence.name)
            await self.bot.change_presence(activity=activity)
            self.current_presence_id = presence.id

    @commands.guild_only()
    @commands.group()
    async def presence(self, ctx: commands.Context):
        """Bot presence subcommands"""
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument(
                'Missing subcommand: `list`, `add`, `remove`, `set`, `auto`'
            )

    @presence.command()
    async def list(self, ctx: commands.Context):
        """Get rotating presences list"""
        resp = await get_nanapi().presence.presence_get_presences()
        if not success(resp):
            raise RuntimeError(resp.result)
        presences_data = resp.result
        if len(presences_data) == 0:
            raise commands.CommandError('No presences found')
        presences = [
            f'`{presence.id}` {presence.type} {presence.name}' for presence in presences_data
        ]
        await ctx.send(embed=Embed(description='\n'.join(presences)))

    @presence.command(usage='<playing|listening|watching> <name>')
    async def add(self, ctx: commands.Context, type: str, *, name: str):
        """Add presence to rotating list"""
        try:
            type = PresencePresenceType(type.upper())
        except ValueError:
            raise commands.CommandError('Type not in (`playing`, `listening`, `watching`)')
        resp = await get_nanapi().presence.presence_new_presence(
            NewPresenceBody(type=type.value, name=name)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        await ctx.message.add_reaction('👌')

    @commands.has_permissions(administrator=True)
    @presence.command(aliases=['rm'])
    async def remove(self, ctx: commands.Context, id: str):
        """(Admin only) Remove presence from rotating list"""
        uuid = UUID(id)
        resp = await get_nanapi().presence.presence_delete_presence(uuid)
        if not success(resp):
            raise RuntimeError(resp.result)
        await ctx.message.add_reaction('👌')

    @commands.has_permissions(administrator=True)
    @presence.command(usage='<playing|listening|watching> <name>')
    async def set(self, ctx: commands.Context, type: str, *, name: str):
        """(Admin only) Force set bot presence"""
        if type.lower() not in ('playing', 'listening', 'watching'):
            raise commands.BadArgument('Type not in (`playing`, `listening`, `watching`)')
        self.loop_presence.cancel()
        activity = discord.Activity(type=getattr(discord.ActivityType, type.lower()), name=name)
        await self.bot.change_presence(activity=activity)
        await ctx.message.add_reaction('👌')
        await ctx.send(f'*Remember to restart rotating presences with `{PREFIX}presence auto`*')

    @commands.has_permissions(administrator=True)
    @presence.command()
    async def auto(self, ctx: commands.Context):
        """(Admin only) Start rotating presences"""
        if self.loop_presence.is_running():
            raise commands.CommandError('Already using rotating presences.')
        self.loop_presence.start()
        await ctx.message.add_reaction('👌')


async def setup(bot: Bot):
    await bot.add_cog(Presence(bot))
