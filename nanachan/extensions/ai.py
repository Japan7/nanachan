import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import AllowedMentions, Thread, app_commands
from discord.app_commands import Choice
from discord.app_commands.tree import ALL_GUILDS
from discord.ext import commands
from pydantic_ai import Agent, BinaryContent, RunContext
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, NanaGroup, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import InsertPromptBody
from nanachan.settings import (
    AI_DEFAULT_MODEL,
    AI_FLAGSHIP_MODEL,
    AI_GROK_MODEL,
    ENABLE_MESSAGE_EXPORT,
    TZ,
    RequiresAI,
)
from nanachan.utils.ai import (
    discord_toolset,
    get_model,
    iter_stream,
    nanapi_toolset,
    python_toolset,
    search_toolset,
)
from nanachan.utils.misc import autocomplete_truncate

if TYPE_CHECKING:
    from discord.types.gateway import MessageCreateEvent
    from discord.types.message import Message

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    model_name: str
    history: list[ModelMessage] = field(default_factory=list)


async def prompt_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]:
    resp = await get_nanapi().ai.ai_prompt_index()
    if not success(resp):
        raise RuntimeError(resp.result)
    choices = [
        Choice(
            name=autocomplete_truncate(f'{prompt.name} ({prompt.description})'),
            value=prompt.name,
        )
        for prompt in resp.result
        if current.lower() in prompt.name.lower()
    ]
    return choices[:25]


@app_commands.guild_only()
class AI(Cog, required_settings=RequiresAI):
    slash_ai = NanaGroup(name='ai', guild_ids=[ALL_GUILDS], description='AI commands')
    slash_pr = app_commands.Group(name='prompt', parent=slash_ai, description='AI prompts')

    @staticmethod
    def system_prompt(run_ctx: RunContext[commands.Context[Bot]]):
        ctx = run_ctx.deps
        assert ctx.bot.user and ctx.guild
        return f"""
The assistant is {ctx.bot.user.display_name}, a Discord bot for the {ctx.guild.name} Discord server.

The current date is {datetime.now(TZ)}.

{ctx.bot.user.display_name}'s Discord ID is {ctx.bot.user.id}.

When using retrieved context to answer the user, {ctx.bot.user.display_name} must reference the pertinent messages and provide their links.
For instance: "Snapchat is a beautiful cat (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>) and it loves Louis (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>)."

If the agent is asked to factcheck something, this something may be a replied message or the last messages in the channel.
"""  # noqa: E501

    @staticmethod
    def author_instructions(run_ctx: RunContext[commands.Context[Bot]]):
        ctx = run_ctx.deps
        assert ctx.bot.user
        return (
            f'{ctx.bot.user.display_name} is now being connected with {ctx.author.display_name} '
            f'(ID {ctx.author.id}).'
        )

    def __init__(self, bot: Bot):
        self.bot = bot

        self.agent = Agent(
            deps_type=commands.Context[Bot],
            toolsets=[nanapi_toolset, discord_toolset, search_toolset, python_toolset],  # type: ignore
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

        thread = await self.get_chat_thread(resp, name='/ai chat')
        await thread.add_user(ctx.author)
        self.contexts[thread.id] = ChatContext(model_name=model_name)

        assert self.bot.user
        await thread.send(
            f'Mention {self.bot.user.mention} to prompt **{model_name}**.',
            allowed_mentions=AllowedMentions.none(),
        )

    async def get_chat_thread(self, message: discord.Message, name: str):
        if isinstance(message.channel, discord.Thread):
            thread = message.channel
        else:
            thread = await message.create_thread(
                name=f'{name} – {datetime.now(TZ):%Y-%m-%d %H:%M}',
                auto_archive_duration=60,
            )
        return thread

    async def chat(
        self,
        ctx: commands.Context[Bot],
        thread: discord.Thread,
        prompt: str,
        attachments: list[discord.Attachment],
    ):
        async with self.agent_lock, thread.typing():
            chat_ctx = self.contexts[thread.id]
            model = get_model(chat_ctx.model_name)

            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type:
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

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
                        deps=ctx,
                        yield_call_tools=True,
                    ):
                        resp = await send(part, allowed_mentions=allowed_mentions)
                        send = resp.reply
            except Exception as e:
                await send(f'An error occured while running the agent:\n```\n{e}\n```')
                logger.exception(e)

    @slash_pr.command(name='save')
    @legacy_command()
    async def prompt_save(self, ctx: LegacyCommandContext, name: str, what: str):
        """Save a prompt"""
        await ctx.defer()
        async with self.agent_lock, self.agent:
            result = await self.agent.run(
                f'Create a prompt named `{name}` (make it snake_case) '
                f'that does the following task:\n{what}',
                output_type=InsertPromptBody,
                model=get_model(AI_FLAGSHIP_MODEL),
                deps=ctx,
            )
        body = result.output
        resp = await get_nanapi().ai.ai_insert_prompt(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        embed = Embed(title=f'`{body.name}`', description=body.description)
        embed.add_field(name='Prompt', value=body.prompt, inline=False)
        for arg in body.arguments:
            embed.add_field(name=f'`{arg.name}`', value=arg.description, inline=True)
        await ctx.reply(embed=embed)

    @slash_pr.command(name='delete')
    @app_commands.autocomplete(name=prompt_autocomplete)
    @legacy_command()
    async def prompt_delete(self, ctx: LegacyCommandContext, name: str):
        """Delete a prompt"""
        resp = await get_nanapi().ai.ai_delete_prompt(name)
        if not success(resp):
            raise RuntimeError(resp.result)
        await ctx.reply(self.bot.get_emoji_str('FubukiGO'))

    @slash_pr.command(name='use')
    @app_commands.autocomplete(name=prompt_autocomplete)
    @legacy_command()
    async def prompt_use(
        self,
        ctx: LegacyCommandContext,
        name: str,
        model_name: str | None = None,
    ):
        """Use a prompt"""
        if not model_name:
            model_name = AI_DEFAULT_MODEL

        resp = await get_nanapi().ai.ai_get_prompt(name)
        if not success(resp):
            raise commands.CommandError('Prompt not found')
        prompt = resp.result

        chat_prompt = prompt.prompt
        if prompt.arguments:
            chat_prompt += '\n\nBefore proceeding, ask the user the following arguments:\n'
            for arg in prompt.arguments:
                chat_prompt += f'{arg.name}: {arg.description}\n'

        embed = Embed(description=f'`/{prompt.name}`')
        embed.set_footer(text=model_name)
        resp = await ctx.reply(embed=embed)

        thread = await self.get_chat_thread(resp, name=prompt.name)
        await thread.add_user(ctx.author)
        self.contexts[thread.id] = ChatContext(model_name=model_name)

        await self.chat(ctx, thread, chat_prompt, [])

    @NanaGroupCog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if (
            self.bot.user in message.mentions
            and isinstance(message.channel, discord.Thread)
            and message.channel.id in self.contexts
        ):
            ctx = await self.bot.get_context(message, cls=commands.Context[Bot])
            await self.chat(
                ctx,
                message.channel,
                message.content,
                message.attachments,
            )
            return

        if message.content.startswith('@grok'):
            ctx = await self.bot.get_context(message, cls=commands.Context[Bot])
            thread = await self.get_chat_thread(message, name='@grok')
            await thread.add_user(message.author)
            self.contexts[thread.id] = ChatContext(model_name=AI_GROK_MODEL)
            await self.chat(
                ctx,
                thread,
                message.content.removeprefix('@grok '),
                message.attachments,
            )
            return


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))

    async def on_raw_message(data: 'MessageCreateEvent'):
        await upsert_message(data)

    async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
        await upsert_message(payload.data)

    async def upsert_message(data: 'Message'):
        noindex = None
        if str(data['author']['id']) == str(bot.bot_id):
            noindex = 'nanachan'
        elif data['author'].get('bot'):
            noindex = 'bot'
        elif await is_nana_thread(data):
            noindex = 'nanachan thread'  # AI chat ?
        await get_nanapi().discord.discord_upsert_message(
            str(data['id']), json.dumps(data), noindex=noindex
        )

    async def is_nana_thread(data: 'Message'):
        if (thread := data.get('thread')) and str(thread['owner_id']) == str(bot.bot_id):
            return True
        channel_id = int(data['channel_id'])
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        return isinstance(channel, Thread) and channel.owner_id == bot.bot_id

    async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
        await get_nanapi().discord.discord_delete_messages(str(payload.message_id))

    async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
        await get_nanapi().discord.discord_delete_messages(','.join(map(str, payload.message_ids)))

    if ENABLE_MESSAGE_EXPORT:
        bot.add_listener(on_raw_message)
        bot.add_listener(on_raw_message_edit)
        bot.add_listener(on_raw_message_delete)
        bot.add_listener(on_raw_bulk_message_delete)
