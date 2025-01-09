import random

from discord.ext import commands
from discord.ext.commands import Bot

from nanachan.discord.helpers import MultiplexingContext
from nanachan.extensions.ai import AI


class Tsundere(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        message = ctx.message
        if message.author.bot:
            return

        if self.bot.user.display_name in message.content or self.bot.user in message.mentions:
            ai_cog = AI.get_cog(self.bot)
            if ai_cog is not None and ctx.channel.id in ai_cog.chats:
                return

            messages = [
                '何言ってんの？ばか！ 😡',
                '別にそんなことないけど…',
                'へ？どういう意味？アホか？',
                'とっとと消え失せろ',
            ]
            await message.send(random.choice(messages))


async def setup(bot: Bot):
    await bot.add_cog(Tsundere(bot))
