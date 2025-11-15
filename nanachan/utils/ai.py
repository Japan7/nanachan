import base64
import io
import logging
from datetime import datetime
from typing import AsyncGenerator, Iterable, Sequence

import discord
from discord.ext import commands
from discord.utils import time_snowflake
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.common_tools.tavily import tavily_search_tool
from pydantic_ai.mcp import MCPServerStdio
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
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.toolsets import FunctionToolset

from nanachan.discord.bot import Bot
from nanachan.nanapi.client import get_nanapi, success
from nanachan.settings import (
    AI_IMAGE_MODEL,
    AI_OPENROUTER_API_KEY,
    AI_SKIP_PERMISSIONS_CHECK,
    AI_TAVILY_API_KEY,
)
from nanachan.utils.misc import get_session

logger = logging.getLogger(__name__)


def get_model(model_name: str) -> Model:
    assert AI_OPENROUTER_API_KEY
    return OpenAIChatModel(model_name, provider=OpenRouterProvider(api_key=AI_OPENROUTER_API_KEY))


async def iter_stream[AgentDepsT](
    agent: Agent[AgentDepsT],
    *,
    user_prompt: Sequence[UserContent],
    message_history: list[ModelMessage],
    model: Model,
    deps: AgentDepsT,
    yield_call_tools: bool = False,
) -> AsyncGenerator[str]:
    """https://ai.pydantic.dev/agents/#streaming"""
    async with agent.iter(
        user_prompt,
        message_history=message_history,
        model=model,
        deps=deps,
    ) as run:
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
                            elif isinstance(event.delta, ToolCallPartDelta):  # type: ignore
                                ...
                        elif isinstance(event, FinalResultEvent):  # type: ignore
                            ...
                        if len(buf) > 2000:
                            lines = buf.splitlines()
                            buf = ''
                            for line in lines:
                                if len(buf) + len(line) > 2000:
                                    yield buf
                                    buf = line
                                else:
                                    buf += '\n' + line
                    if buf:
                        yield buf
            elif Agent.is_call_tools_node(node):
                # A handle-response node => The model returned some data, potentially calls a tool
                async with node.stream(run.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            if yield_call_tools:
                                yield (
                                    f'```\n[TOOL] {event.part.tool_name} {event.part.args}\n```'
                                )
                        elif isinstance(event, FunctionToolResultEvent):
                            ...
            elif Agent.is_end_node(node):
                # Once an End node is reached, the agent run is complete
                assert run.result
                message_history.extend(run.result.new_messages())


def nanapi_tools() -> Iterable[Tool[None]]:
    nanapi = get_nanapi()
    endpoints = [
        nanapi.ai.ai_prompt_index,
        nanapi.ai.ai_get_prompt,
        nanapi.amq.amq_get_accounts,
        nanapi.anilist.anilist_get_accounts,
        nanapi.anilist.anilist_get_account_entries,
        nanapi.anilist.anilist_get_medias,
        nanapi.anilist.anilist_media_search,
        nanapi.anilist.anilist_get_media_list_entries,
        nanapi.anilist.anilist_get_media_chara_edges,
        nanapi.anilist.anilist_get_charas,
        nanapi.anilist.anilist_chara_search,
        nanapi.anilist.anilist_get_chara_chara_edges,
        nanapi.anilist.anilist_get_staffs,
        nanapi.anilist.anilist_staff_search,
        nanapi.anilist.anilist_get_staff_chara_edges,
        nanapi.calendar.calendar_get_user_calendar,
        nanapi.calendar.calendar_get_guild_events,
        nanapi.histoire.histoire_histoire_index,
        nanapi.histoire.histoire_get_histoire,
        nanapi.projection.projection_get_projections,
        nanapi.reminder.reminder_get_reminders,
        nanapi.user.user_profile_search,
        nanapi.user.user_get_profile,
        nanapi.waicolle.waicolle_get_players,
        nanapi.waicolle.waicolle_get_player,
        nanapi.waicolle.waicolle_get_player_tracked_items,
        nanapi.waicolle.waicolle_get_player_track_unlocked,
        nanapi.waicolle.waicolle_get_player_media_stats,
        nanapi.waicolle.waicolle_get_player_staff_stats,
        nanapi.waicolle.waicolle_get_player_collection_stats,
        nanapi.waicolle.waicolle_get_waifus,
        nanapi.waicolle.waicolle_trade_index,
        nanapi.waicolle.waicolle_get_collection,
    ]
    for endpoint in endpoints:
        yield Tool(endpoint, takes_ctx=None)


nanapi_toolset = FunctionToolset(tools=list(nanapi_tools()))
discord_toolset = FunctionToolset[commands.Context[Bot]]()
search_toolset = FunctionToolset(
    tools=[
        tavily_search_tool(AI_TAVILY_API_KEY)
        if AI_TAVILY_API_KEY is not None
        else duckduckgo_search_tool()
    ]
)
python_toolset = MCPServerStdio(
    'deno',
    args=[
        'run',
        '-N',
        '-R=node_modules',
        '-W=node_modules',
        '--node-modules-dir=auto',
        'jsr:@pydantic/mcp-run-python',
        'stdio',
    ],
)


@discord_toolset.tool
def get_members_name_discord_id_map(run_ctx: RunContext[commands.Context[Bot]]):
    """Generate a mapping of Discord member display names to their Discord IDs."""
    ctx = run_ctx.deps
    return {member.display_name: member.id for member in ctx.bot.get_all_members()}


@discord_toolset.tool
def get_channels_name_channel_id_map(run_ctx: RunContext[commands.Context[Bot]]):
    """Generate a mapping of Discord channel names to their channel IDs."""
    ctx = run_ctx.deps
    return {channel.name: channel.id for channel in ctx.bot.get_all_channels()}


@discord_toolset.tool
async def get_parent_channel(run_ctx: RunContext[commands.Context[Bot]]):
    """Retrieve the parent channel of the current thread in which the assistant is summoned."""
    ctx = run_ctx.deps
    channel_id = (
        ctx.channel.parent.id
        if isinstance(ctx.channel, discord.Thread) and ctx.channel.parent
        else ctx.channel.id
    )
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@discord_toolset.tool
async def get_replied_message(run_ctx: RunContext[commands.Context[Bot]]):
    """Retrieve the message that the current message is replying to, if any."""
    ctx = run_ctx.deps
    if ctx.message.reference and ctx.message.reference.message_id:
        return await ctx._state.http.get_message(  # pyright: ignore[reportPrivateUsage]
            ctx.message.reference.channel_id,
            ctx.message.reference.message_id,
        )
    return None


@discord_toolset.tool
async def fetch_channel(run_ctx: RunContext[commands.Context[Bot]], channel_id: str):
    """Fetch a channel."""
    ctx = run_ctx.deps
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@discord_toolset.tool
async def fetch_message(
    run_ctx: RunContext[commands.Context[Bot]],
    channel_id: str,
    message_id: str,
):
    """Fetch a message from a channel."""
    ctx = run_ctx.deps
    return await ctx._state.http.get_message(channel_id, message_id)  # pyright: ignore[reportPrivateUsage]


@discord_toolset.tool
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


@discord_toolset.tool(retries=5)
async def retrieve_context(run_ctx: RunContext[commands.Context[Bot]], search_query: str):
    """Find relevant past discussion sections using a simple French keyword search."""
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


@discord_toolset.tool
async def generate_image(
    run_ctx: RunContext[commands.Context[Bot]],
    prompt: str,
    base_image_urls: list[str] | None = None,
    include_ctx_attachments: bool = False,
):
    """
    Generate an image and send it on Discord.
    If base_image_urls are provided, these images will be included as base images for editing.
    If include_ctx_attachments is True, images attached to the user prompt will also be included
    as base images for editing.
    """
    headers = {
        'Authorization': f'Bearer {AI_OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
    }
    input_content = [{'type': 'text', 'text': prompt}]
    if base_image_urls:
        for url in base_image_urls:
            input_content.append({'type': 'image_url', 'image_url': url})
    if include_ctx_attachments:
        ctx = run_ctx.deps
        for attachment in ctx.message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_bytes = await attachment.read()
                encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                data_url = f'data:{attachment.content_type};base64,{encoded_image}'
                input_content.append({'type': 'image_url', 'image_url': data_url})
    payload = {
        'model': AI_IMAGE_MODEL,
        'messages': [{'role': 'user', 'content': input_content}],
        'modalities': ['image', 'text'],
    }
    async with get_session().post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers=headers,
        json=payload,
        timeout=None,
    ) as resp:
        resp.raise_for_status()
        result = await resp.json()

    message = result['choices'][0]['message']
    content = message['content']
    image_url = message['images'][0]['image_url']['url']

    # Extract base64 data from data URL
    # Format: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
    header, encoded = image_url.split(',', 1)
    mime_type = header.split(';')[0].split(':')[1]
    extension = mime_type.split('/')[1]

    # Decode base64 to bytes
    image_data = base64.b64decode(encoded)

    # Create a Discord file and send it
    file = discord.File(io.BytesIO(image_data), filename=f'generated.{extension}')
    sent = await run_ctx.deps.send(content, file=file)
    return repr(sent)
