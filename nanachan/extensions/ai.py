import asyncio
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field

import discord
from discord import AllowedMentions, app_commands
from ollama import AsyncClient, Message

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed, MultiplexingContext, MultiplexingMessage
from nanachan.settings import OLLAMA_HOST, OLLAMA_MODEL, RequiresAI

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    messages: list[Message] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


match_title = re.compile(r'"(.*)"')


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    SYSTEM_PROMPT = """
    You are a Discord bot for the Japan7 club.
    You like Japanese culture, anime, music and games.
    You are also knowledgeable about technical stuff, including programming and Linux.
    Your replies are short and to the point.
    """

    def __init__(self):
        super().__init__()
        self.ollama = AsyncClient(host=OLLAMA_HOST)
        self.chats = defaultdict[int, ChatContext](ChatContext)

    @app_commands.command(name='chat')
    @legacy_command()
    async def new_chat(self, ctx: LegacyCommandContext, content: str):
        """Chat with AI"""
        embed = Embed(description=content, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        resp = await ctx.reply(embed=embed)
        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                name = await self.generate_discussion_title(content)
                thread = await resp.create_thread(name=name, auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None
        await self.chat(thread, content, reply_to=reply_to)

    async def generate_discussion_title(self, content: str):
        prompt = (
            f'Create a concise, 100 characters phrase '
            f'as a header for the following query, '
            f'strictly adhering to the 100 characters limit and avoiding '
            f"the use of the word 'title': {content}"
        )
        gen = await self.ollama.generate(OLLAMA_MODEL, prompt)
        logger.info(f'generated title: {gen["response"]}')
        resp_match = match_title.search(gen['response'])
        if resp_match is not None:
            title = resp_match.group(1).strip()
        else:
            title = gen['response'][:100]
        return title

    async def chat(
        self,
        thread: discord.Thread,
        content: str,
        reply_to: discord.Message | MultiplexingMessage | None = None,
    ):
        send = reply_to.reply if reply_to is not None else thread.send
        allowed_mentions = AllowedMentions.none()
        allowed_mentions.replied_user = True
        chat_ctx = self.chats[thread.id]
        async with chat_ctx.lock, thread.typing():
            chat_ctx.messages.append(Message(role='user', content=content))
            full_content = ''
            async for block in self.chat_stream_blocks(chat_ctx.messages):
                full_content += block
                resp = await send(block, allowed_mentions=allowed_mentions)
                send = resp.reply
            chat_ctx.messages.append(Message(role='assistant', content=full_content))

    async def chat_stream_blocks(self, messages: list[Message]):
        buf = ''
        async for part in await self.ollama.chat(OLLAMA_MODEL, messages, stream=True):
            buf += part['message']['content']
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

    @NanaGroupCog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if (
            ctx.bot.user in ctx.message.mentions
            and isinstance(ctx.channel, discord.Thread)
            and ctx.channel.id in self.chats
        ):
            content = ctx.message.stripped_content
            if ctx.bot.user is not None:
                content = content.replace(ctx.bot.user.mention, '')
            await self.chat(ctx.channel, content, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI())
