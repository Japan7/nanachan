import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from inspect import get_annotations
from typing import TYPE_CHECKING, get_args

import discord
from discord import AllowedMentions, Thread, app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient
from discord.utils import time_snowflake
from pydantic_ai import Agent, BinaryContent, ModelRetry, RunContext
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.nanapi.client import get_nanapi, success
from nanachan.settings import (
    AI_DEFAULT_MODEL,
    AI_MODEL_CLS,
    ENABLE_MESSAGE_EXPORT,
    TZ,
    RequiresAI,
    RequiresGemini,
)
from nanachan.utils.ai import (
    GeminiLiveAudioSink,
    get_model,
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
async def channel_history(
    run_ctx: RunContext[commands.Context[Bot]],
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
    bot = run_ctx.deps.bot
    return await bot.http.logs_from(
        channel_id=channel_id,
        limit=limit,
        before=time_snowflake(before) if before else None,
        after=time_snowflake(after) if after else None,
        around=time_snowflake(around) if around else None,
    )


@agent.tool_plain
async def retrieve_context(search_query: str) -> list[list[str]]:
    """Retrieve relevant discussion sections based on a search query in French."""
    resp = await get_nanapi().discord.discord_rag(search_query)
    if not success(resp):
        raise RuntimeError(resp.result)
    return [
        [m.data for m in sorted(result.messages, key=lambda m: m.timestamp)]
        for result in resp.result
    ]


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
    slash_voicechat = app_commands.Group(name='voicechat', description='AI Voice Chat')

    def __init__(self, bot: Bot):
        self.bot = bot
        self.contexts = dict[int, ChatContext]()
        self.voice_client: VoiceRecvClient | None = None

        if RequiresGemini.configured:
            self.slash_voicechat.command(name='start')(self.voice_start)
            self.slash_voicechat.command(name='stop')(self.voice_stop)

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
