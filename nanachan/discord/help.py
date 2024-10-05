import logging
from itertools import batched, chain
from operator import attrgetter
from typing import TYPE_CHECKING, List, Mapping, Optional, cast

from discord.ext.commands import Cog, Command, Group, HelpCommand

from nanachan.discord.helpers import Embed
from nanachan.discord.views import NavigatorView
from nanachan.settings import PREFIX

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot

logger = logging.getLogger(__name__)


class HelpReactionListener(NavigatorView):

    @classmethod
    async def create(cls, bot, send_function, *, pages, **kwargs):
        prev_pages = chain([pages[-1]], pages)
        next_pages = chain(pages[1:], [pages[0]])
        for previous_page, page, next_page in zip(prev_pages, pages, next_pages):
            page['embed'].set_footer(text=f"{cls.PREV_EMOJI} {previous_page['embed'].title} | "
                                          f"{next_page['embed'].title} {cls.NEXT_EMOJI}")
        return await super().create(bot, send_function, pages=pages, **kwargs)


class CustomHelpCommand(HelpCommand):

    def get_recursive_help_for_command(self, command: Command):
        if command.hidden:
            return ''

        if isinstance(command, Group):
            for subcommand in sorted(command.commands, key=attrgetter("qualified_name")):
                yield from self.get_recursive_help_for_command(subcommand)
        else:
            result = f'**{PREFIX}{command.qualified_name}**'
            if command.signature:
                result += f' *{command.signature}*'

            if command.help:
                command_help = command.help.format(bot_name=self.bot_name)
                yield result + f'\n{command_help}\n\n'
            else:
                logger.info(f"{command.name} has no help message")

    @staticmethod
    def split_descriptions(commands_help_parts):
        commands_help_parts = list(commands_help_parts)
        if len(commands_help_parts) % 5 == 1:
            n = 6
        else:
            n = 5

        for parts in batched(commands_help_parts, n):
            yield ''.join(parts)

    def get_embeds_for_cog(self, cog: Cog):
        commands = cog.get_commands()
        if commands:
            commands_help_parts = [self.get_cog_description(cog) + "\n"*2]
            for command in sorted(commands, key=attrgetter("qualified_name")):
                commands_help_parts.extend(self.get_recursive_help_for_command(command))

            if len(commands_help_parts) > 1:
                title = self.get_cog_title(cog)
                for description in self.split_descriptions(commands_help_parts):
                    yield Embed(title=title, description=description)

    @property
    def bot_name(self):
        user = self.context.bot.user
        assert user is not None
        return user.display_name

    def get_cog_description(self, cog: Cog) -> str:
        desc: str | None = getattr(cog, '_cog_description', None)
        if desc:
            desc = desc.strip()
        else:
            desc = f"Commands related to {cog.qualified_name}"

        desc = desc.format(bot_name=self.bot_name)
        return desc

    def get_cog_title(self, cog: Cog):
        emoji = getattr(cog, 'emoji', '⚙')
        return f'{emoji} {cog.qualified_name}'

    async def send_bot_help(self, mapping: Mapping[Optional[Cog], List[Command]]):
        first_embed = Embed(title=f'{self.bot_name} commands manual',
                            description='')
        embeds = []
        cogs = (cog for cog in mapping if cog is not None)

        for cog in sorted(cogs, key=attrgetter('qualified_name')):
            cog_embeds = list(self.get_embeds_for_cog(cog))

            if cog_embeds:
                desc = self.get_cog_description(cog)
                title = self.get_cog_title(cog)

                first_embed.add_field(name=title,
                                      value=desc,
                                      inline=False)

                embeds.extend(cog_embeds)

        embeds.insert(0, first_embed)
        pages = [{'embed': embed} for embed in embeds]
        await HelpReactionListener.create(self.context.bot,
                                          self.get_destination().send,
                                          pages=pages)

    async def send_cog_help(self, cog: Cog):
        pages = [{'embed': embed} for embed in self.get_embeds_for_cog(cog)]
        if pages:
            await NavigatorView.create(cast('Bot', self.context.bot),
                                       self.get_destination().send,
                                       pages=pages)
        else:
            await self.get_destination().send(content=self.command_not_found(cog.qualified_name))

    async def send_group_help(self, group: Group):
        help = self.get_recursive_help_for_command(group)
        if help:
            embeds = [Embed(title=group.qualified_name, description=description)
                      for description in self.split_descriptions(help)]
            pages = [{'embed': embed} for embed in embeds]
            await NavigatorView.create(cast('Bot', self.context.bot),
                                       self.get_destination().send,
                                       pages=pages)
        else:
            await self.get_destination().send(content=self.command_not_found(group.qualified_name))

    async def send_command_help(self, command: Command):
        help = self.get_recursive_help_for_command(command)
        if help:
            embeds = [Embed(description=description)
                      for description in self.split_descriptions(help)]
            pages = [{'embed': embed} for embed in embeds]
            await NavigatorView.create(cast('Bot', self.context.bot),
                                       self.get_destination().send,
                                       pages=pages)
        else:
            await self.get_destination().send(
                content=self.command_not_found(command.qualified_name)
            )
