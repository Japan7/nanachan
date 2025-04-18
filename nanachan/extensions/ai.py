import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

import discord
from discord import AllowedMentions, app_commands
from pydantic_ai import Agent, BinaryContent, RunContext, Tool
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPartDelta,
    UserContent,
)

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed, MultiplexingContext, MultiplexingMessage, UserType
from nanachan.nanapi.client import get_nanapi_tools
from nanachan.settings import AI_MODEL, RequiresAI

logger = logging.getLogger(__name__)


@dataclass
class RunDeps:
    author: UserType


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.agent = Agent(AI_MODEL, tools=list(self.get_tools()), deps_type=RunDeps)
        self.messages = defaultdict[int, list[ModelMessage]](list)
        self.lock = asyncio.Lock()

    def get_tools(self) -> Iterable[Tool[RunDeps]]:
        def get_current_user_infos(run_ctx: RunContext[RunDeps]):
            """Get name and Discord ID of the current user."""
            author = run_ctx.deps.author
            return dict(
                id=author.id,
                display_name=author.display_name,
                global_name=author.global_name,
            )

        yield Tool(get_current_user_infos)

        def get_members_name_discord_id_map():
            """Generate a mapping of Discord member display names to their Discord IDs."""
            return {member.display_name: str(member.id) for member in self.bot.get_all_members()}

        yield Tool(get_members_name_discord_id_map)

        yield from get_nanapi_tools()

    @app_commands.command(name='chat')
    @legacy_command()
    async def new_chat(
        self, ctx: LegacyCommandContext, prompt: str, image: discord.Attachment | None = None
    ):
        """Chat with AI"""
        embed = Embed(description=prompt, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        if image:
            embed.set_image(url=image.url)
        assert AI_MODEL
        embed.set_footer(text=AI_MODEL.model_name)
        resp = await ctx.reply(embed=embed)

        attachments = [image] if image else []

        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                thread = await resp.create_thread(name=prompt[:100], auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None

        await self.chat(ctx.author, thread, prompt, attachments, reply_to=reply_to)

    async def chat(
        self,
        author: UserType,
        thread: discord.Thread,
        prompt: str,
        attachments: list[discord.Attachment],
        reply_to: discord.Message | MultiplexingMessage | None = None,
    ):
        async with thread.typing(), self.lock:
            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

            history = self.messages[thread.id]

            deps = RunDeps(author)

            send = reply_to.reply if reply_to is not None else thread.send
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                async for block in self.agent_iter(content, history, deps):
                    resp = await send(block, allowed_mentions=allowed_mentions)
                    send = resp.reply
            except Exception as e:
                await send(f'An error occured while streaming the response:\n```{e}```')
                logger.exception(e)

    async def agent_iter(
        self,
        user_prompt: Sequence[UserContent],
        message_history: list[ModelMessage],
        deps: RunDeps,
    ):
        """https://ai.pydantic.dev/agents/#streaming"""
        async with self.agent.iter(user_prompt, message_history=message_history, deps=deps) as run:
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    # A user prompt node => The user has provided input
                    ...
                elif Agent.is_model_request_node(node):
                    # A model request node => We can stream tokens from the model's request
                    async with node.stream(run.ctx) as request_stream:
                        buf = ''
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart):
                                    buf += event.part.content
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    buf += event.delta.content_delta
                                elif isinstance(event.delta, ToolCallPartDelta):
                                    ...
                            elif isinstance(event, FinalResultEvent):
                                ...
                            if len(buf) > 2000:
                                blocks = buf.split('\n')
                                buf = ''
                                for block in blocks:
                                    if len(buf) + len(block) > 2000:
                                        yield buf
                                        buf = block
                                    else:
                                        buf += '\n' + block
                        if buf:
                            yield buf
                elif Agent.is_call_tools_node(node):
                    # A handle-response node =>
                    # The model returned some data, potentially calls a tool
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                yield (f'```[TOOL] {event.part.tool_name} {event.part.args}```')
                            elif isinstance(event, FunctionToolResultEvent):
                                ...
                elif Agent.is_end_node(node):
                    # Once an End node is reached, the agent run is complete
                    assert run.result
                    message_history.extend(run.result.new_messages())

    @NanaGroupCog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if (
            ctx.bot.user in ctx.message.mentions
            and isinstance(ctx.channel, discord.Thread)
            and ctx.channel.id in self.messages
        ):
            prompt = ctx.message.stripped_content
            if ctx.bot.user is not None:
                prompt = prompt.replace(ctx.bot.user.mention, '')
            attachments = ctx.message.attachments
            await self.chat(ctx.author, ctx.channel, prompt, attachments, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
