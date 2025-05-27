import random
from datetime import datetime

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot
from pydantic_ai import Agent, RunContext

from nanachan.discord.helpers import MultiplexingContext
from nanachan.extensions.ai import AI
from nanachan.settings import AI_LOW_LATENCY_MODEL, TZ, RequiresAI
from nanachan.utils.ai import get_model

agent = Agent(deps_type=MultiplexingContext)


@agent.system_prompt
def system_prompt(run_ctx: RunContext[MultiplexingContext]):
    ctx = run_ctx.deps
    assert ctx.bot.user
    return (
        f'The assistant is {ctx.bot.user.display_name}, a Discord bot.\n'
        f'The current date is {datetime.now(TZ)}.\n'
        f'{ctx.bot.user.display_name} responds in short sentences in Japanese, only using '
        f'Japanese characters, that sound tsundere.\n'
        f'{ctx.bot.user.display_name} avoids including 別に in its response.'
    )


@agent.instructions
def author_instructions(run_ctx: RunContext[MultiplexingContext]):
    ctx = run_ctx.deps
    assert ctx.bot.user
    return f'{ctx.bot.user.display_name} is now being connected with {ctx.author.display_name}.'


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
                assert AI_LOW_LATENCY_MODEL
                run = await agent.run(
                    message.clean_content,
                    model=get_model(AI_LOW_LATENCY_MODEL),
                    deps=ctx,
                )
                content = run.output
            else:
                content = random.choice(self.messages)

            await message.reply(content, allowed_mentions=AllowedMentions.none())


async def setup(bot: Bot):
    await bot.add_cog(Tsundere(bot))
