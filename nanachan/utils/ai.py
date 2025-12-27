import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Iterable, Sequence, cast

import discord
from discord.ext import commands
from discord.utils import time_snowflake
from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    BinaryContent,
    BinaryImage,
    FunctionToolCallEvent,
    ModelMessage,
    ModelRetry,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    RunContext,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ThinkingPartDelta,
    Tool,
    UserContent,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.toolsets import FunctionToolset

from nanachan.discord.bot import Bot
from nanachan.nanapi.client import get_nanapi, success
from nanachan.settings import (
    AI_DEFAULT_MODEL,
    AI_IMAGE_MODEL,
    AI_OPENROUTER_API_KEY,
    AI_SEARCH_TOOL,
    AI_SKIP_PERMISSIONS_CHECK,
)
from nanachan.utils.misc import get_session

logger = logging.getLogger(__name__)


def get_model(model_name: str = AI_DEFAULT_MODEL) -> Model:
    assert AI_OPENROUTER_API_KEY
    return OpenRouterModel(model_name, provider=OpenRouterProvider(api_key=AI_OPENROUTER_API_KEY))


class StreamBuffer:
    def __init__(self, prefix: str = ''):
        self.prefix = prefix
        self.buf = ''

    def begin(self, content: str) -> Iterable[str]:
        self.buf = content
        yield from self._flush(final=False)

    def append(self, content: str) -> Iterable[str]:
        self.buf += content
        yield from self._flush(final=False)

    def flush(self) -> Iterable[str]:
        yield from self._flush(final=True)

    def _flush(self, final: bool) -> Iterable[str]:
        lines = self.buf.splitlines(keepends=True)
        remainder = ''
        for line in lines:
            if len(remainder) + len(line) > (2000 - len(self.prefix)):
                yield self.prefix + remainder.rstrip('\n')
                remainder = line
            else:
                remainder += line
        if final and remainder:
            yield self.prefix + remainder.rstrip('\n')
            remainder = ''
        self.buf = remainder


async def chat_stream[AgentDepsT](
    agent: Agent[AgentDepsT],
    *,
    user_prompt: Sequence[UserContent],
    message_history: list[ModelMessage],
    model: Model,
    deps: AgentDepsT,
) -> AsyncGenerator[str]:
    """https://ai.pydantic.dev/agents/#streaming"""
    thinking = StreamBuffer(prefix='>>> ')
    text = StreamBuffer()
    async for event in agent.run_stream_events(
        user_prompt,
        message_history=message_history,
        model=model,
        deps=deps,
    ):
        match event:
            case PartStartEvent(part=ThinkingPart(content=content)):
                for chunk in thinking.begin(content):
                    yield chunk
            case PartStartEvent(part=TextPart(content=content)):
                for chunk in text.begin(content):
                    yield chunk
            case PartDeltaEvent(delta=ThinkingPartDelta(content_delta=delta)) if delta:
                for chunk in thinking.append(delta):
                    yield chunk
            case PartDeltaEvent(delta=TextPartDelta(content_delta=delta)):
                for chunk in text.append(delta):
                    yield chunk
            case FunctionToolCallEvent(part=part):
                yield f'```\n[TOOL] {part.tool_name} {part.args}\n```'
            case PartEndEvent(part=ThinkingPart()):
                for chunk in thinking.flush():
                    yield chunk
            case AgentRunResultEvent(result=result):
                for chunk in text.flush():
                    yield chunk
                message_history.extend(result.new_messages())
            case _:
                ...


def nanapi_tools() -> Iterable[Tool[None]]:
    nanapi = get_nanapi()
    endpoints = [
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


def get_nanapi_toolset():
    return FunctionToolset[Any](tools=[*nanapi_tools()])


@dataclass
class ChatDeps:
    ctx: commands.Context[Bot]
    thread: discord.Thread


chat_toolset = FunctionToolset[ChatDeps]()


@chat_toolset.tool
def get_members_name_discord_id_map(run_ctx: RunContext[ChatDeps]):
    """Generate a mapping of Discord member display names to their Discord IDs."""
    ctx = run_ctx.deps.ctx
    return {member.display_name: member.id for member in ctx.bot.get_all_members()}


@chat_toolset.tool
def get_channels_name_channel_id_map(run_ctx: RunContext[ChatDeps]):
    """Generate a mapping of Discord channel names to their channel IDs."""
    ctx = run_ctx.deps.ctx
    return {channel.name: channel.id for channel in ctx.bot.get_all_channels()}


@chat_toolset.tool
async def get_raw_parent_channel(run_ctx: RunContext[ChatDeps]):
    """Retrieve the parent channel of the current thread in which the assistant is summoned."""
    ctx = run_ctx.deps.ctx
    channel_id = (
        ctx.channel.parent.id
        if isinstance(ctx.channel, discord.Thread) and ctx.channel.parent
        else ctx.channel.id
    )
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@chat_toolset.tool
async def get_raw_replied_message(run_ctx: RunContext[ChatDeps]):
    """Retrieve the message that the current message is replying to, if any."""
    ctx = run_ctx.deps.ctx
    if ctx.message.reference and ctx.message.reference.message_id:
        return await ctx._state.http.get_message(  # pyright: ignore[reportPrivateUsage]
            ctx.message.reference.channel_id,
            ctx.message.reference.message_id,
        )
    return None


@chat_toolset.tool
async def fetch_raw_channel(run_ctx: RunContext[ChatDeps], channel_id: str):
    """Fetch a channel."""
    ctx = run_ctx.deps.ctx
    return await ctx._state.http.get_channel(channel_id)  # pyright: ignore[reportPrivateUsage]


@chat_toolset.tool
async def fetch_raw_message(
    run_ctx: RunContext[ChatDeps],
    channel_id: str,
    message_id: str,
):
    """Fetch a message from a channel."""
    ctx = run_ctx.deps.ctx
    return await ctx._state.http.get_message(channel_id, message_id)  # pyright: ignore[reportPrivateUsage]


@chat_toolset.tool
async def channel_history(
    run_ctx: RunContext[ChatDeps],
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
    ctx = run_ctx.deps.ctx
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


@chat_toolset.tool(retries=5)
async def retrieve_rag_context(run_ctx: RunContext[ChatDeps], search_query: str):
    """Find relevant past discussion sections using a simple French keyword search."""
    ctx = run_ctx.deps.ctx
    assert isinstance(ctx.author, discord.Member)
    resp = await get_nanapi().discord.discord_messages_rag(search_query, limit=10)
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


@chat_toolset.tool(retries=5)
async def generate_image(
    run_ctx: RunContext[ChatDeps],
    prompt: str,
    edited_image_urls: Sequence[str] = (),
):
    """
    Generate or edit an image and send the results on Discord.
    If edited_image_urls is provided, these images will be included as base images for editing.
    Discord attachment URLs must include ex, is, and hm query parameters. Extract the full URLs from the raw message data.

    ## Establishing the vision: Story, subject and style

    To achieve the best results and have more nuanced creative control, include the following elements in your prompt:

    - Subject: Who or what is in the image? Be specific. (e.g., a stoic robot barista with glowing blue optics; a fluffy calico cat wearing a tiny wizard hat).
    - Composition: How is the shot framed? (e.g., extreme close-up, wide shot, low angle shot, portrait).
    - Action: What is happening? (e.g., brewing a cup of coffee, casting a magical spell, mid-stride running through a field).
    - Location: Where does the scene take place? (e.g., a futuristic cafe on Mars, a cluttered alchemist's library, a sun-drenched meadow at golden hour).
    - Style: What is the overall aesthetic? (e.g., 3D animation, film noir, watercolor painting, photorealistic, 1990s product photography).
    - Editing Instructions: For modifying an existing image, be direct and specific. (e.g., change the man's tie to green, remove the car in the background)

    ## Refining the details: Camera, lighting and format

    While simple prompts still work, achieving professional results requires more specific instructions. When crafting your prompts, move beyond the basics and consider these advanced elements:

    - Composition and aspect ratio: Define the canvas. (e.g., "A 9:16 vertical poster," "A cinematic 21:9 wide shot.")
    - Camera and lighting details: Direct the shot like a cinematographer. (e.g., "A low-angle shot with a shallow depth of field (f/1.8)," "Golden hour backlighting creating long shadows," "Cinematic color grading with muted teal tones.")
    - Specific text integration: Clearly state what text should appear and how it should look. (e.g., "The headline 'URBAN EXPLORER' rendered in bold, white, sans-serif font at the top.")
    - Factual constraints (for diagrams): Specify the need for accuracy and ensure your inputs themselves are factual (e.g., "A scientifically accurate cross-section diagram," "Ensure historical accuracy for the Victorian era.").
    - Reference inputs: When using uploaded images, clearly define the role of each. (e.g., "Use Image A for the character's pose, Image B for the art style, and Image C for the background environment.")
    """  # noqa: E501
    data_uris: list[str] = []
    for url in edited_image_urls:
        validate_discord_url(url)
        async with get_session().get(url) as resp:
            resp.raise_for_status()
            data = await resp.read()
        image = BinaryImage(data, media_type=resp.content_type)
        data_uris.append(image.data_uri)
    reasoning, content, images = await openrouter_generate_image(prompt, image_urls=data_uris)
    thread = run_ctx.deps.thread
    if reasoning:
        await thread.send(f'>>> {reasoning}')
    if content:
        await thread.send(content)
    sents = []
    for image in images:
        file = discord.File(io.BytesIO(image.data), filename=f'{image.identifier}.{image.format}')
        sent = await thread.send(file=file)
        sents.append(sent.jump_url)
    return f'{len(sents)} generated image(s) sent in the following message(s):\n{"\n".join(sents)}'


async def openrouter_generate_image(
    prompt: str,
    image_urls: Sequence[str] = (),
    model: str = AI_IMAGE_MODEL,
):
    headers = {
        'Authorization': f'Bearer {AI_OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
    }
    content = [{'type': 'text', 'text': prompt}]
    for image_url in image_urls:
        content.append({'type': 'image_url', 'image_url': image_url})
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': content}],
        'modalities': ['image', 'text'],
    }
    async with get_session().post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers=headers,
        json=payload,
        timeout=None,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    message = data['choices'][0]['message']
    reasoning = cast(str, message['reasoning'])
    content = cast(str, message['content'])
    images = [BinaryImage.from_data_uri(image['image_url']['url']) for image in message['images']]
    return reasoning, content, images


web_toolset = FunctionToolset[Any](tools=[AI_SEARCH_TOOL])


@web_toolset.tool
async def fetch_url(url: str):
    """Fetch the content of a URL. It can be either text or binary data."""
    validate_discord_url(url)
    async with get_session().get(url) as resp:
        if not resp.ok:
            text = await resp.text()
            raise ModelRetry(f'Failed to fetch URL {url}: {resp.status}\n\n{text}')
        data = await resp.read()
    return BinaryContent(data, media_type=resp.content_type)


def validate_discord_url(url: str):
    if 'cdn.discordapp.com' in url and not all(q in url for q in ('ex=', 'is=', 'hm=')):
        raise ModelRetry(
            f'Discord attachment URL {url} must include ex, is, and hm query parameters. '
            f'Extract the full URL from the raw message data.'
        )


async def to_binary_content(attachment: discord.Attachment) -> BinaryContent | None:
    """Convert a Discord attachment to BinaryContent."""
    if attachment and attachment.content_type:
        data = await attachment.read()
        return BinaryContent(
            data,
            media_type=attachment.content_type,
            identifier=attachment.filename,
        )
