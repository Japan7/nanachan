import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import discord
from discord import AllowedMentions, app_commands
from discord.app_commands.tree import ALL_GUILDS
from discord.ext import commands
from pydantic_ai import Agent, BinaryContent, RunContext
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, NanaGroup, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.settings import (
    AI_ADDITIONAL_TOOLSETS,
    AI_DEFAULT_MODEL,
    AI_GROK_MODEL,
    GITHUB_REPO_SLUG,
    SLASH_PREFIX,
    TZ,
    RequiresAI,
)
from nanachan.utils.ai import ChatDeps, all_toolsets, get_model, iter_stream

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    model_name: str
    history: list[ModelMessage] = field(default_factory=list)


@app_commands.guild_only()
class AI(Cog, required_settings=RequiresAI):
    slash_ai = NanaGroup(name='ai', guild_ids=[ALL_GUILDS], description='AI commands')

    @staticmethod
    def system_prompt(run_ctx: RunContext[ChatDeps]):
        ctx = run_ctx.deps.ctx
        assert ctx.bot.user and ctx.guild
        return f"""
The assistant is {ctx.bot.user.display_name}, a Discord bot for the {ctx.guild.name} Discord server.

The current date is {datetime.now(TZ)}.

{ctx.bot.user.display_name}'s Discord ID is {ctx.bot.user.id}.

When using retrieved context to answer the user, {ctx.bot.user.display_name} must reference the pertinent messages and provide their links.
For instance: "Snapchat is a beautiful cat (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>) and it loves Louis (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>)."

If the agent is asked to factcheck something, this something may be a replied message or the last messages in the channel.

The Discord bot code repository is hosted at https://github.com/{GITHUB_REPO_SLUG}.
The backend code repository is hosted at https://github.com/Japan7/nanapi.
"""  # noqa: E501

    @staticmethod
    def author_instructions(run_ctx: RunContext[ChatDeps]):
        ctx = run_ctx.deps.ctx
        assert ctx.bot.user
        return (
            f'{ctx.bot.user.display_name} is now being connected with {ctx.author.display_name} '
            f'(ID {ctx.author.id}).'
        )

    def __init__(self, bot: Bot):
        self.bot = bot

        self.agent = Agent(
            deps_type=ChatDeps,
            toolsets=[*all_toolsets, *AI_ADDITIONAL_TOOLSETS],
        )
        self.agent.system_prompt(self.system_prompt)
        self.agent.instructions(self.author_instructions)
        self.agent_lock = asyncio.Lock()

        self.contexts = dict[int, ChatContext]()

    @slash_ai.command(name='chat')
    @legacy_command()
    async def new_chat(self, ctx: LegacyCommandContext, model_name: str | None = None):
        """Chat with AI"""
        if not model_name:
            model_name = AI_DEFAULT_MODEL

        embed = Embed()
        embed.set_footer(text=model_name)
        resp = await ctx.reply(embed=embed)

        thread = await self.get_chat_thread(resp, name_prefix=model_name, user_to_add=ctx.author)
        self.contexts[thread.id] = ChatContext(model_name=model_name)

        assert self.bot.user
        await thread.send(
            f'Mention {self.bot.user.mention} to prompt **{model_name}**.',
            allowed_mentions=AllowedMentions.none(),
        )

    async def get_chat_thread(
        self,
        message: discord.Message,
        name_prefix: str,
        user_to_add: discord.Member | discord.User | None = None,
    ):
        if isinstance(message.channel, discord.Thread):
            thread = message.channel
        else:
            thread = await message.create_thread(
                name=f'{name_prefix} – {datetime.now(TZ):%Y-%m-%d %H:%M}',
                auto_archive_duration=60,
            )
        if user_to_add:
            await thread.add_user(user_to_add)
        return thread

    async def chat(
        self,
        ctx: commands.Context[Bot],
        thread: discord.Thread,
        model_name: str | None = None,
    ):
        async with self.agent_lock, thread.typing():
            chat_ctx = self.contexts[thread.id]
            model = get_model(model_name or chat_ctx.model_name)

            message = await ctx._state.http.get_message(ctx.channel.id, ctx.message.id)  # pyright: ignore[reportPrivateUsage]
            content: list[UserContent] = [
                ctx.message.content,
                f'This is the raw user message data: {json.dumps(message)}',
            ]
            for attachment in ctx.message.attachments:
                if attachment.content_type:
                    data = await attachment.read()
                    content.extend(
                        [
                            f'This is attachment {attachment.filename}:',
                            BinaryContent(
                                data,
                                media_type=attachment.content_type,
                                identifier=attachment.filename,
                            ),
                        ]
                    )

            send = (
                ctx.message.reply
                if isinstance(ctx.message.channel, discord.Thread)
                else thread.send
            )
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                async with self.agent:
                    async for part in iter_stream(
                        self.agent,
                        user_prompt=content,
                        message_history=chat_ctx.history,
                        model=model,
                        deps=ChatDeps(ctx, thread),
                    ):
                        resp = await send(part, allowed_mentions=allowed_mentions)
                        send = resp.reply
            except Exception as e:
                await send(f'An error occured while running the agent:\n```\n{e}\n```')
                logger.exception(e)

    @NanaGroupCog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if self.bot.user in message.mentions:
            await self.on_chat_message(message)
            return

        if message.content.startswith(f'@{SLASH_PREFIX}grok'):
            await self.on_chat_message(message, model_name=AI_GROK_MODEL)
            return

    async def on_chat_message(self, message: discord.Message, model_name: str | None = None):
        ctx = await self.bot.get_context(message, cls=commands.Context[Bot])
        thread = await self.get_chat_thread(
            message, name_prefix=model_name or AI_DEFAULT_MODEL, user_to_add=message.author
        )
        if thread.id not in self.contexts:
            self.contexts[thread.id] = ChatContext(model_name or AI_DEFAULT_MODEL)
        await self.chat(ctx, thread, model_name=model_name)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
