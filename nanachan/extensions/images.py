from enum import Enum

import discord
from discord import app_commands

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
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


class WaifuPicsChoice(Enum):
    # waifu = 'waifu'
    # neko = 'neko'
    # shinobu = 'shinobu'
    # megumin = 'megumin'
    bully = 'bully'
    cuddle = 'cuddle'
    cry = 'cry'
    hug = 'hug'
    # awoo = 'awoo'
    kiss = 'kiss'
    lick = 'lick'
    pat = 'pat'
    smug = 'smug'
    bonk = 'bonk'
    # yeet = 'yeet'
    blush = 'blush'
    smile = 'smile'
    wave = 'wave'
    highfive = 'highfive'
    handhold = 'handhold'
    nom = 'nom'
    bite = 'bite'
    glomp = 'glomp'
    slap = 'slap'
    kill = 'kill'
    kick = 'kick'
    happy = 'happy'
    wink = 'wink'
    poke = 'poke'
    dance = 'dance'
    cringe = 'cringe'


@app_commands.guild_only()
class Images(NanaGroupCog, group_name='image'):
    async def send_image(self, ctx: LegacyCommandContext, option, user, url):
        optstr = option.value

        e = 'e' if optstr[-1] == 's' else ''
        hype = ctx.bot.get_nana_emoji('hype')
        content = f'{ctx.author.mention} **{optstr}{e}s** {user.mention}!'
        if hype is not None:
            content = f'{hype} {content}'

        embed = Embed()
        embed.set_image(url=url)

        await ctx.reply(content=content, embed=embed)

    @app_commands.command()
    @legacy_command()
    async def nekos(self, ctx: LegacyCommandContext, option: NekosChoice, user: discord.User):
        """Hugs, kisses, pats and many more from nekos.life"""
        async with get_session().get(f'https://nekos.life/api/v2/img/{option.value}') as r:
            data = await r.json()
        await self.send_image(ctx, option, user, data['url'])

    @app_commands.command()
    @legacy_command()
    async def waifupics(
        self, ctx: LegacyCommandContext, option: WaifuPicsChoice, user: discord.User
    ):
        """waifu.pics random image"""
        async with get_session().get(f'https://api.waifu.pics/sfw/{option.value}') as r:
            data = await r.json()
        await self.send_image(ctx, option, user, data['url'])


async def setup(bot: Bot):
    await bot.add_cog(Images())
