from functools import partial

from discord import Interaction
from discord.ui import Button, button

from nanachan.changelog import CHANGELOG
from nanachan.discord.application_commands import nana_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.views import BaseView, NavigatorView
from nanachan.settings import TADAIMA


def format_changelog():
    for i, page in enumerate(CHANGELOG):
        yield {'content': f'```Markdown\nChangelog page {i + 1}/{len(CHANGELOG)}{page}```'}


class Changelog(Cog):
    emoji = '\N{CLIPBOARD}'

    @Cog.listener()
    async def on_ready(self):
        if TADAIMA:
            bot_room = self.bot.get_bot_room()
            await bot_room.send('ただいま〜', view=ChangelogView(self.bot))

    @nana_command()
    async def changelog(self, interaction: Interaction):
        """Read it! It’s awesome!"""
        send = partial(interaction.response.send_message, ephemeral=True)
        await NavigatorView.create(self.bot, send, pages=list(format_changelog()))


class ChangelogView(BaseView):

    @button(emoji=Changelog.emoji)
    async def changelog_button(self, interaction: Interaction, button: Button):
        await NavigatorView.create(
            self.bot,
            partial(interaction.response.send_message, ephemeral=True),
            pages=list(format_changelog()))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Changelog(bot))
