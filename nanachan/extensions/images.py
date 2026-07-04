from enum import Enum

import discord
from discord import Interaction, app_commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.utils.misc import get_session


class NekosChoice(Enum):
    smug = 'smug'
    woof = 'woof'
    gasm = 'gasm'
    # eightball = '8ball'
    goose = 'goose'
    cuddle = 'cuddle'
    avatar = 'avatar'
    slap = 'slap'
    # v3 = 'v3'
    pat = 'pat'
    gecg = 'gecg'
    feed = 'feed'
    fox_girl = 'fox_girl'
    lizard = 'lizard'
    neko = 'neko'
    hug = 'hug'
    meow = 'meow'
    kiss = 'kiss'
    wallpaper = 'wallpaper'
    tickle = 'tickle'
    spank = 'spank'
    waifu = 'waifu'
    lewd = 'lewd'
    # ngif = 'ngif'


@app_commands.guild_only()
class Images(NanaGroupCog, group_name='image'):
    async def send_image(self, interaction: Interaction[Bot], option, user, url):
        optstr = option.value

        e = 'e' if optstr[-1] == 's' else ''
        hype = interaction.client.get_nana_emoji('hype')
        content = f'{interaction.user.mention} **{optstr}{e}s** {user.mention}!'
        if hype is not None:
            content = f'{hype} {content}'

        embed = Embed()
        embed.set_image(url=url)

        await interaction.followup.send(content=content, embed=embed)

    @app_commands.command()
    async def nekos(self, interaction: Interaction[Bot], option: NekosChoice, user: discord.User):
        """Hugs, kisses, pats and many more from nekos.life"""
        await interaction.response.defer()
        async with get_session().get(f'https://nekos.life/api/v2/img/{option.value}') as r:
            data = await r.json()
        await self.send_image(interaction, option, user, data['url'])


async def setup(bot: Bot):
    await bot.add_cog(Images())
