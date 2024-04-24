from functools import partial
from operator import attrgetter
from typing import Sequence

import discord
import discord.errors
from discord import Message, Role, TextChannel
from discord.ext import commands
from toolz.curried import compose, compose_left, get

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Emoji, EmojiConverter, WebhookMessage
from nanachan.discord.reactions import ReactionHandler, ReactionListener
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import NewRoleBody, RoleSelectAllResult
from nanachan.settings import PREFIX, ROLE_ASSIGNMENT_CHANNEL, RequiresRoleAssignment
from nanachan.utils.misc import list_display


class RoleMessage(ReactionListener):

    DESCRIPTION = "Manage your roles by adding/removing reactions to this message."

    def __init__(self, bot: Bot, message: int | WebhookMessage | discord.WebhookMessage | Message,
                 roles: Sequence[RoleSelectAllResult]):
        self.roles = {r.role_id: r for r in roles}
        handlers = self.get_role_reactions()

        super().__init__(bot, message, first_handlers=handlers)
        self.bot.loop.create_task(self.update_message())

    async def update_message(self):
        content = self.get_message_content()
        assert self.message is not None
        if self.message.content != content:
            await self.message.edit(content=content)

    def get_role_reactions(self, roles=None):
        if roles is None:
            roles = self.get_roles()

        for db_role, discord_role in roles:
            emoji = Emoji.from_string(self.bot, db_role.emoji)
            assert emoji is not None
            yield ReactionHandler(
                partial(self.handler_add_role, discord_role=discord_role),
                emoji.name,
                on_add=True,
                remove_reaction=False,
            )
            yield ReactionHandler(
                partial(self.handler_remove_role, discord_role=discord_role),
                emoji.name,
                on_remove=True,
                remove_reaction=False,
            )

    @staticmethod
    async def handler_add_role(listener, user, *, discord_role):
        if discord_role.id in listener.roles:
            await user.add_roles(discord_role)

    @staticmethod
    async def handler_remove_role(listener, user, *, discord_role):
        if discord_role.id in listener.roles:
            await user.remove_roles(discord_role)

    async def add_role(self, discord_role, db_role):
        self.roles[db_role.role_id] = db_role
        await self.update_message()
        for handler in self.get_role_reactions([(db_role, discord_role)]):
            self.add_handler(handler)

        assert self.message is not None
        await self.message.add_reaction(self.get_reaction(db_role.emoji))

    async def remove_role(self, role_id: int):
        db_role = self.roles.pop(role_id)
        await self.update_message()
        assert self.message is not None
        await self.message.clear_reaction(self.get_reaction(db_role.emoji))

    def get_role(self, role_id: int):
        for guild in self.bot.guilds:
            if role := guild.get_role(role_id):
                return role

    def discord_roles(self, roles):
        return (self.get_role(role.role_id) for role in roles)

    def _get_roles(self, roles):
        return ((r, d) for r, d in zip(roles, self.discord_roles(roles))
                if d is not None)

    def get_roles(self):
        return self._get_roles(list(self.roles.values()))

    def get_message_content(self):
        content = RoleMessage.DESCRIPTION

        if self.roles:
            roles = list(self.get_roles())

            content += "\n\n" + '\n'.join(f"{Emoji.from_string(self.bot, role.emoji)} "
                                          f"**{discord_role.name}**"
                                          for role, discord_role in roles)

        return content

    def get_emojis(self):
        return map(compose(attrgetter('name'), get(1)), self.get_roles())


class Roles(Cog):

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.is_ready = bot.loop.create_future()

    @property
    def role_channel(self):
        role_channel = self.bot.get_channel(ROLE_ASSIGNMENT_CHANNEL)
        assert isinstance(role_channel, TextChannel)
        return role_channel

    async def get_role_message(self):
        webhooks = {w.id: w for w in await self.role_channel.webhooks()
                    if w.token is not None}
        async for message in self.role_channel.history(limit=None):
            if message.webhook_id in webhooks:
                return WebhookMessage(message, webhooks[message.webhook_id])

    @RequiresRoleAssignment
    @Cog.listener()
    async def on_ready(self):
        if not self.is_ready.done():
            role_message = await self.get_role_message()
            if role_message is None:
                webhook = await self.bot.get_webhook(self.role_channel)
                assert self.bot.user is not None
                role_message = await webhook.send(RoleMessage.DESCRIPTION,
                                                  username=self.bot.user.display_name,
                                                  avatar_url=self.bot.user.display_avatar.url,
                                                  wait=True)

            resp = await get_nanapi().role.role_get_roles()
            if not success(resp):
                raise RuntimeError(resp.result)
            roles = resp.result

            self.role_message = RoleMessage(self.bot, role_message, roles)
            self.is_ready.set_result(True)

    @commands.guild_only()
    @commands.group(aliases=['roles'], invoke_without_command=True,
                    help='Display information about roles')
    async def role(self, ctx, *, role: Role):
        members = sorted([str(member)
                          for member in ctx.guild.members
                          if role in member.roles],
                         key=str.lower)
        if members:
            for page in list_display(role.name, members):
                await ctx.send(page)
        else:
            await ctx.send(f'Nobody on server has role {role.name}')

    @staticmethod
    async def _do_list(ctx):
        roles = [
            role.name
            for role in sorted(ctx.guild.roles,
                               key=compose_left(attrgetter('name'), str.casefold))
            if role.name != '@everyone'
        ]
        for page in list_display('Server roles', roles):
            await ctx.send(page)

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)
            await self._do_list(ctx)
        else:
            await self.bot.on_command_error(ctx, error, force=True)

    @commands.guild_only()
    @role.command(help='List all existing roles')
    async def list(self, ctx):
        await self._do_list(ctx)

    if RequiresRoleAssignment:

        @commands.has_permissions(administrator=True)
        @role.command(help='Enable auto assignable role')
        async def auto(self, ctx, role: Role, emoji: EmojiConverter):
            await self.is_ready

            resp = await get_nanapi().role.role_new_role(
                NewRoleBody(role_id=role.id, emoji=str(emoji)))
            if not success(resp):
                match resp.code:
                    case 409:
                        raise commands.CommandError(f"Role {role.name} is already auto assignable")
                    case _:
                        raise RuntimeError(resp.result)
            db_role = resp.result

            try:
                await self.role_message.add_role(role, db_role)
            except discord.errors.HTTPException:
                raise commands.CommandError(
                    f"Can't add this reaction (because it is not from this server). "
                    f"Either add it yourself to the message or {PREFIX}import it or "
                    f"choose another emoji.")
            await ctx.send(f"{role.name} is now auto assignable.")

        @commands.has_permissions(administrator=True)
        @role.command(help='Disable auto assignable role')
        async def deauto(self, ctx, role: Role):
            if role.id in self.role_message.roles:
                resp = await get_nanapi().role.role_delete_role(role.id)
                if not success(resp):
                    raise RuntimeError(resp.result)
                await self.role_message.remove_role(role.id)
                await ctx.send(f"{role.name} is not auto assignable anymore.")
            else:
                raise commands.CommandError(f"{role.name} is not auto assignable.")


async def setup(bot: Bot):
    await bot.add_cog(Roles(bot))
