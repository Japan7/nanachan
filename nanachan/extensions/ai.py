import asyncio
import base64
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import discord
from discord import AllowedMentions, Thread, app_commands
from discord.app_commands import Choice
from discord.app_commands.tree import ALL_GUILDS
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient
from discord.utils import time_snowflake
from pydantic_ai import Agent, BinaryContent, ModelRetry, RunContext
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
    AI_SKIP_PERMISSIONS_CHECK,
    ENABLE_MESSAGE_EXPORT,
    TZ,
    RequiresAI,
    RequiresGemini,
    RequiresOpenAI,
)
from nanachan.utils.ai import (
    GeminiLiveAudioSink,
    get_model,
    get_openai,
    iter_stream,
    nanapi_tools,
    python_mcp_server,
    search_tool,
)
from nanachan.utils.misc import autocomplete_truncate

if TYPE_CHECKING:
    from discord.types.gateway import MessageCreateEvent
    from discord.types.message import Message

logger = logging.getLogger(__name__)


agent = Agent(
    deps_type=commands.Context[Bot],
    tools=(search_tool, *nanapi_tools()),  # type: ignore
    mcp_servers=[python_mcp_server],
)

agent_lock = asyncio.Lock()


@agent.system_prompt
def system_prompt(run_ctx: RunContext[commands.Context[Bot]]):
    ctx = run_ctx.deps
    assert ctx.bot.user and ctx.guild
    return f"""
The assistant is {ctx.bot.user.display_name}, a Discord bot for the {ctx.guild.name} Discord server.

The current date is {datetime.now(TZ)}.

{ctx.bot.user.display_name}'s Discord ID is {ctx.bot.user.id}.

If {ctx.bot.user.display_name} lacks sufficient information to answer a question, and if no other tool is suitable for the task, {ctx.bot.user.display_name} should automatically use the retrieve_context tool to obtain pertinent discussion sections before responding.

When using retrieved context to answer the user, {ctx.bot.user.display_name} must reference the pertinent messages and provide their links.
For instance: "Snapchat is a beautiful cat (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>) and it loves Louis (https://discord.com/channels/<guild_id>/<channel_id>/<message_id>)."

For complex tasks, {ctx.bot.user.display_name} can access to a collection of prompts with ai_prompt_index and ai_get_prompt. These prompts serve as instructions.
"""  # noqa: E501


@agent.instructions
def author_instructions(run_ctx: RunContext[commands.Context[Bot]]):
    ctx = run_ctx.deps
    assert ctx.bot.user
    return (
        f'{ctx.bot.user.display_name} is now being connected with {ctx.author.display_name} '
        f'(ID {ctx.author.id}).'
    )


@agent.tool
def get_members_name_discord_id_map(run_ctx: RunContext[commands.Context[Bot]]):
    """Generate a mapping of Discord member display names to their Discord IDs."""
    ctx = run_ctx.deps
    return {member.display_name: member.id for member in ctx.bot.get_all_members()}


@agent.tool
def get_channels_name_channel_id_map(run_ctx: RunContext[commands.Context[Bot]]):
    """Generate a mapping of Discord channel names to their channel IDs."""
    ctx = run_ctx.deps
    return {channel.name: channel.id for channel in ctx.bot.get_all_channels()}


@agent.tool
async def get_parent_channel(run_ctx: RunContext[commands.Context[Bot]]):
    """Retrieve the parent channel of the current thread in which the assistant is summoned."""
    ctx = run_ctx.deps
    channel_id = (
        ctx.channel.parent.id
        if isinstance(ctx.channel, Thread) and ctx.channel.parent
        else ctx.channel.id
    )
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@agent.tool
async def fetch_channel(run_ctx: RunContext[commands.Context[Bot]], channel_id: str):
    """Fetch a channel."""
    ctx = run_ctx.deps
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@agent.tool
async def fetch_message(
    run_ctx: RunContext[commands.Context[Bot]],
    channel_id: str,
    message_id: str,
):
    """Fetch a message from a channel."""
    ctx = run_ctx.deps
    return await ctx._state.http.get_message(channel_id, message_id)  # pyright: ignore[reportPrivateUsage]


@agent.tool
async def channel_history(
    run_ctx: RunContext[commands.Context[Bot]],
    channel_id: str,
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
    ctx = run_ctx.deps
    if not AI_SKIP_PERMISSIONS_CHECK:
        assert isinstance(ctx.author, discord.Member)
        channel = ctx.bot.get_channel(int(channel_id))
        if not channel:
            raise RuntimeError(f'Channel {channel_id} not found.')
        if isinstance(channel, discord.abc.PrivateChannel):
            raise RuntimeError(f'Channel {channel_id} is private.')
        if not channel.permissions_for(ctx.author).read_message_history:
            raise RuntimeError(f'User does not have permission to read channel {channel_id}')
    if sum(bool(x) for x in (before, after, around)) > 1:
        raise ModelRetry('Only one of before, after, or around may be passed.')
    if limit > 100:
        raise ModelRetry('Max limit is 100.')
    return await ctx.bot.http.logs_from(
        channel_id=channel_id,
        limit=limit,
        before=time_snowflake(before) if before else None,
        after=time_snowflake(after) if after else None,
        around=time_snowflake(around) if around else None,
    )


@agent.tool(retries=5)
async def retrieve_context(run_ctx: RunContext[commands.Context[Bot]], search_query: str):
    """Find relevant discussion sections using a simple French keyword search."""
    ctx = run_ctx.deps
    assert isinstance(ctx.author, discord.Member)
    resp = await get_nanapi().discord.discord_messages_rag(search_query, limit=25)
    if not success(resp):
        raise RuntimeError(resp.result)
    messages = [
        [
            m.data
            for m in r.object.messages
            if AI_SKIP_PERMISSIONS_CHECK
            or (channel := ctx.bot.get_channel(int(m.channel_id)))
            and not isinstance(channel, discord.abc.PrivateChannel)
            and channel.permissions_for(ctx.author).read_message_history
        ]
        for r in resp.result
    ]
    messages = [b for b in messages if b]
    if not messages:
        raise ModelRetry('No results found. Try using a simpler query.')
    return messages


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
    slash_vc = app_commands.Group(name='voicechat', parent=slash_ai, description='AI voice chat')

    def __init__(self, bot: Bot):
        self.bot = bot
        self.contexts = dict[int, ChatContext]()
        self.voice_client: VoiceRecvClient | None = None

        if RequiresOpenAI.configured:
            self.slash_ai.command(name='image')(self.imagen)

        if RequiresGemini.configured:
            self.slash_vc.command(name='start')(self.voice_start)
            self.slash_vc.command(name='stop')(self.voice_stop)

    @slash_ai.command(name='chat')
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
        async with agent_lock, thread.typing():
            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type:
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

            chat_ctx = self.contexts[thread.id]

            model = get_model(chat_ctx.model_name)

            send = reply_to.reply if reply_to else thread.send
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                async for part in iter_stream(
                    agent,
                    user_prompt=content,
                    message_history=chat_ctx.history,
                    model=model,
                    deps=ctx,
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
        assert AI_FLAGSHIP_MODEL
        async with agent_lock, agent.run_mcp_servers():
            result = await agent.run(
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
            assert AI_DEFAULT_MODEL
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

        embed = Embed(description=f'`/{prompt.name}`', color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=model_name)
        resp = await ctx.reply(embed=embed)

        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                thread = await resp.create_thread(name=prompt.name, auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None

        self.contexts[thread.id] = ChatContext(model_name=model_name)
        await self.chat(ctx, thread, chat_prompt, attachments=[], reply_to=reply_to)

    @legacy_command()
    async def imagen(
        self,
        ctx: LegacyCommandContext,
        prompt: str,
        attachment: discord.Attachment | None = None,
        model: Literal['gpt-image-1', 'dall-e-2'] = 'gpt-image-1',
        quality: Literal['standard', 'low', 'medium', 'high', 'auto'] = 'auto',
        size: Literal[
            '256x256', '512x512', '1024x1024', '1536x1024', '1024x1536', 'auto'
        ] = 'auto',
    ):
        """OpenAI Image Generation"""
        await ctx.defer()
        embed = Embed(description=prompt, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f'{model} (quality: {quality}, size: {size})')
        if attachment and attachment.content_type and attachment.content_type.startswith('image/'):
            embed.set_image(url=attachment.url)
            data = await attachment.read()
            result = await get_openai().images.edit(
                model=model,
                prompt=prompt,
                image=(attachment.filename, data, attachment.content_type),
                quality=quality,
                size=size,
            )
        else:
            result = await get_openai().images.generate(
                model=model,
                prompt=prompt,
                quality=quality,
                size=size,
            )
        assert result.data
        image_base64 = result.data[0].b64_json
        assert image_base64
        image_bytes = base64.b64decode(image_base64)
        with io.BytesIO() as buf:
            buf.write(image_bytes)
            buf.seek(0)
            await ctx.reply(
                embed=embed,
                file=discord.File(fp=buf, filename=f'{result.created}.png'),
            )

    @legacy_command()
    async def voice_start(
        self,
        ctx: LegacyCommandContext,
        only_with: discord.Member | None = None,
        voice_name: GeminiLiveAudioSink.VoiceName = 'Aoede',
    ):
        """Start Voice Chat with AI"""
        if (
            not isinstance(ctx.author, discord.Member)
            or not ctx.author.voice
            or not ctx.author.voice.channel
        ):
            raise commands.CommandError('You must be in a voice channel')

        if self.voice_client:
            raise commands.CommandError('Already running')

        self.voice_client = await ctx.author.voice.channel.connect(cls=VoiceRecvClient)
        sink = GeminiLiveAudioSink(self.bot, voice_name=voice_name, only_with=only_with)
        self.voice_client.listen(sink)
        self.voice_client.play(sink.response_source, application='voip')

        await ctx.send(self.bot.get_emoji_str('FubukiGO'))

    @legacy_command()
    async def voice_stop(self, ctx: LegacyCommandContext):
        """Stop Voice Chat with AI"""
        if not self.voice_client:
            raise commands.CommandError('Not running')

        await self.voice_client.disconnect()
        self.voice_client = None

        await ctx.send(self.bot.get_emoji_str('FubukiStop'))

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
