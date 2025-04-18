import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence

import discord
from discord import AllowedMentions, app_commands
from pydantic_ai import Agent, BinaryContent, Tool
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed, MultiplexingContext, MultiplexingMessage
from nanachan.nanapi.client import get_nanapi_tools
from nanachan.settings import AI_MODEL_MULTIMODAL, AI_MODEL_TEXT, RequiresAI

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    history: list[ModelMessage] = field(default_factory=list)
    multimodal: bool = False


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.chats = defaultdict[int, ChatContext](ChatContext)
        self.lock = asyncio.Lock()
        tools = [Tool(self.get_users_discord_ids)] + get_nanapi_tools()
        self.agent_multimodal = Agent(AI_MODEL_MULTIMODAL, tools=tools)
        self.agent_text = Agent(
            AI_MODEL_TEXT if AI_MODEL_TEXT else AI_MODEL_MULTIMODAL, tools=tools
        )

    def get_users_discord_ids(self):
        """Get all available Discord users. Map of their discord_id to their display name."""
        return {str(user.id): user.display_name for user in self.bot.users}

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

        await self.chat(thread, prompt, attachments, reply_to=reply_to)

    async def chat(
        self,
        thread: discord.Thread,
        prompt: str,
        attachments: list[discord.Attachment],
        reply_to: discord.Message | MultiplexingMessage | None = None,
    ):
        send = reply_to.reply if reply_to is not None else thread.send
        allowed_mentions = AllowedMentions.none()
        allowed_mentions.replied_user = True
        chat_ctx = self.chats[thread.id]
        async with thread.typing(), self.lock:
            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))
            try:
                async for block in self._chat_stream_blocks(chat_ctx, content):
                    resp = await send(block, allowed_mentions=allowed_mentions)
                    send = resp.reply
            except Exception as e:
                await send(f'An error occured while streaming the response:\n{e}')

    async def _chat_stream_blocks(
        self,
        chat_ctx: ChatContext,
        content: Sequence[UserContent],
    ):
        if any(not isinstance(c, str) for c in content):
            chat_ctx.multimodal = True
        agent = self.agent_multimodal if chat_ctx.multimodal else self.agent_text
        async with agent.run_stream(content, message_history=chat_ctx.history) as resp:
            buf = ''
            async for delta in resp.stream_text(delta=True):
                buf += delta
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
            chat_ctx.history.extend(resp.new_messages())

    @NanaGroupCog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if (
            ctx.bot.user in ctx.message.mentions
            and isinstance(ctx.channel, discord.Thread)
            and ctx.channel.id in self.chats
        ):
            prompt = ctx.message.stripped_content
            if ctx.bot.user is not None:
                prompt = prompt.replace(ctx.bot.user.mention, '')
            attachments = ctx.message.attachments
            await self.chat(ctx.channel, prompt, attachments, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
