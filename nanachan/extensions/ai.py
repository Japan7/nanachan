import logging
from dataclasses import dataclass, field
from datetime import datetime
from inspect import get_annotations
from typing import get_args

import discord
from discord import AllowedMentions, app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord.utils import time_snowflake
from pydantic_ai import Agent, BinaryContent, ModelRetry, RunContext
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.settings import AI_DEFAULT_MODEL, AI_MODEL_CLS, TZ, RequiresAI
from nanachan.utils.ai import get_model, iter_stream, nanapi_tools, python_mcp_server
from nanachan.utils.misc import autocomplete_truncate

logger = logging.getLogger(__name__)


@dataclass
class RunDeps:
    ctx: commands.Context[Bot]


agent = Agent(
    deps_type=RunDeps,
    tools=(*nanapi_tools(), duckduckgo_search_tool()),  # type: ignore
    mcp_servers=[python_mcp_server],
)


@agent.system_prompt
def system_prompt(run_ctx: RunContext[RunDeps]):
    ctx = run_ctx.deps.ctx
    bot = ctx.bot
    assert ctx.guild and bot.user
    return (
        f'The assistant is a Discord bot named {bot.user.display_name} (ID {bot.user.id}). '
        f'The assistant is answering requests from the members of the {ctx.guild.name} server.'
    )


@agent.instructions
def author_instructions(run_ctx: RunContext[RunDeps]):
    author = run_ctx.deps.ctx.author
    return (
        f'The user {author.display_name} (ID {author.id}) is sending this prompt to the assistant.'
    )


@agent.tool_plain
def get_current_time():
    """Get the current time."""
    return datetime.now(TZ)


@agent.tool
def get_members_name_discord_id_map(run_ctx: RunContext[RunDeps]):
    """Generate a mapping of Discord member display names to their Discord IDs."""
    bot = run_ctx.deps.ctx.bot
    return {member.display_name: member.id for member in bot.get_all_members()}


@agent.tool
def get_channels_name_channel_id_map(run_ctx: RunContext[RunDeps]):
    """Generate a mapping of Discord channel names to their channel IDs."""
    bot = run_ctx.deps.ctx.bot
    return {channel.name: channel.id for channel in bot.get_all_channels()}


@agent.tool
async def channel_history(
    run_ctx: RunContext[RunDeps],
    channel_id: int,
    limit: int = 100,
    before: datetime | None = None,
    after: datetime | None = None,
    around: datetime | None = None,
):
    """
    Get messages in a channel.
    The before, after, and around parameters are mutually exclusive,
    only one may be passed at a time.
    """
    if sum(bool(x) for x in (before, after, around)) > 1:
        raise ModelRetry('Only one of before, after, or around may be passed.')
    if limit > 100:
        raise ModelRetry('Max limit is 100.')
    bot = run_ctx.deps.ctx.bot
    return await bot.http.logs_from(
        channel_id=channel_id,
        limit=limit,
        before=time_snowflake(before) if before else None,
        after=time_snowflake(after) if after else None,
        around=time_snowflake(around) if around else None,
    )


@dataclass
class ChatContext:
    model_name: str
    history: list[ModelMessage] = field(default_factory=list)


async def model_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]:
    assert AI_MODEL_CLS
    # trust me bro
    model_name_type = get_annotations(AI_MODEL_CLS, eval_str=True)['_model_name']
    model_names = get_args(get_args(model_name_type)[1])
    choices = [
        Choice(name=autocomplete_truncate(name), value=name)
        for name in model_names
        if current.lower() in name.lower()
    ]
    return choices[:25]


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.contexts = dict[int, ChatContext]()

    @app_commands.command(name='chat')
    @app_commands.autocomplete(model_name=model_autocomplete)
    @legacy_command()
    async def new_chat(
        self,
        ctx: LegacyCommandContext,
        prompt: str,
        attachment: discord.Attachment | None = None,
        model_name: str | None = None,
    ):
        """Chat with AI"""
        if not model_name:
            assert AI_DEFAULT_MODEL
            model_name = AI_DEFAULT_MODEL

        embed = Embed(description=prompt, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        if attachment and attachment.content_type and attachment.content_type.startswith('image/'):
            embed.set_image(url=attachment.url)
        embed.set_footer(text=model_name)
        resp = await ctx.reply(embed=embed)

        attachments = []
        if attachment:
            attachments.append(attachment)

        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                thread = await resp.create_thread(name=prompt[:100], auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None

        self.contexts[thread.id] = ChatContext(model_name=model_name)
        await self.chat(ctx, thread, prompt, attachments, reply_to=reply_to)

    async def chat(
        self,
        ctx: commands.Context[Bot],
        thread: discord.Thread,
        prompt: str,
        attachments: list[discord.Attachment],
        reply_to: discord.Message | None = None,
    ):
        async with thread.typing():
            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type:
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

            chat_ctx = self.contexts[thread.id]

            model = get_model(chat_ctx.model_name)

            deps = RunDeps(ctx)

            send = reply_to.reply if reply_to else thread.send
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                async for part in iter_stream(
                    agent,
                    user_prompt=content,
                    message_history=chat_ctx.history,
                    model=model,
                    deps=deps,
                ):
                    resp = await send(part, allowed_mentions=allowed_mentions)
                    send = resp.reply
            except Exception as e:
                await send(f'An error occured while running the agent:\n```\n{e}\n```')
                logger.exception(e)

    @NanaGroupCog.listener()
    async def on_message(self, message: discord.Message):
        if (
            not message.author.bot
            and self.bot.user in message.mentions
            and isinstance(message.channel, discord.Thread)
            and message.channel.id in self.contexts
        ):
            ctx = await self.bot.get_context(message, cls=commands.Context[Bot])
            prompt = ctx.message.content
            attachments = ctx.message.attachments
            await self.chat(ctx, message.channel, prompt, attachments, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
