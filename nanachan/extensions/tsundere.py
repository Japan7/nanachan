import random

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot
from pydantic_ai import Agent, RunContext

from nanachan.discord.helpers import MultiplexingContext
from nanachan.extensions.ai import AI
from nanachan.settings import AI_FAST_MODEL, RequiresAI
from nanachan.utils.ai import get_model

agent = Agent(deps_type=MultiplexingContext)


@agent.instructions
def instructions(run_ctx: RunContext[MultiplexingContext]):
    ctx = run_ctx.deps
    assert ctx.bot.user
    return (
        f'The assistant is a Discord bot named {ctx.bot.user.display_name}).\n'
        f'{ctx.bot.user.display_name} replies to {ctx.author.display_name} with a short sentence '
        f'in Japanese, only in Japanese characters, that sounds tsundere.'
    )


class Tsundere(commands.Cog):
    messages = [
        '何言ってんの？ばか！ 😡',
        '別にそんなことないけど…',
        'へ？どういう意味？アホか？',
        'とっとと消え失せろ',
    ]

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        message = ctx.message
        if message.author.bot:
            return

        if self.bot.user.display_name in message.content or self.bot.user in message.mentions:
            ai_cog = AI.get_cog(self.bot)
            if ai_cog is not None and ctx.channel.id in ai_cog.contexts:
                return

            if RequiresAI.configured:
                assert AI_FAST_MODEL
                run = await agent.run(
                    message.clean_content,
                    model=get_model(AI_FAST_MODEL),
                    deps=ctx,
                )
                content = run.output
            else:
                content = random.choice(self.messages)

            await message.reply(content, allowed_mentions=AllowedMentions.none())


async def setup(bot: Bot):
    await bot.add_cog(Tsundere(bot))
