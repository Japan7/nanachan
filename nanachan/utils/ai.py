import asyncio
import logging
from datetime import datetime
from functools import cache
from queue import Empty, Queue
from typing import AsyncGenerator, Iterable, Literal, Sequence, override

import audioop
import discord
import numpy as np
from discord.ext import commands
from discord.ext.voice_recv import AudioSink
from discord.utils import time_snowflake
from google import genai
from google.genai import live, types
from openai import AsyncOpenAI
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
from pydantic_ai.toolsets import FunctionToolset

from nanachan.discord.bot import Bot
from nanachan.discord.helpers import UserType
from nanachan.nanapi.client import get_nanapi, success
from nanachan.settings import (
    AI_GEMINI_API_KEY,
    AI_MODEL_CLS,
    AI_OPENAI_API_KEY,
    AI_PROVIDER,
    AI_SKIP_PERMISSIONS_CHECK,
    AI_TAVILY_API_KEY,
    TZ,
)

logger = logging.getLogger(__name__)


def get_model(model_name: str) -> Model:
    return AI_MODEL_CLS(model_name, provider=AI_PROVIDER)  # type: ignore


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


@cache
def get_openai():
    assert AI_OPENAI_API_KEY
    return AsyncOpenAI(api_key=AI_OPENAI_API_KEY)


@cache
def get_gemini():
    assert AI_GEMINI_API_KEY
    return genai.Client(api_key=AI_GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})


class GeminiLiveAudioSink(AudioSink):
    type VoiceName = Literal['Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede', 'Leda', 'Orus', 'Zephyr']
    MIN_VOICE_LENGTH = 0.75
    MIN_SILENCE_LENGTH = 1

    def __init__(
        self, bot: Bot, voice_name: VoiceName = 'Aoede', only_with: UserType | None = None
    ):
        super().__init__()
        self.bot = bot
        self.voice_name = voice_name
        self.only_with = only_with

        self.speak_start_time: float | None = None
        self.speak_end_time: float | None = None
        self.end_activity_handle: asyncio.TimerHandle | None = None

        self.write_buf = b''
        self.req_queue = asyncio.Queue[bytes]()
        self.res_queue = Queue[bytes]()

        self.send_loop_task: asyncio.Task[None] | None = None
        self.receive_loop_task: asyncio.Task[None] | None = None
        self.kill_event = asyncio.Event()
        asyncio.create_task(self.gemini_session())

    @property
    def response_source(self):
        return GeminiLiveAudioSource(self.res_queue)

    @override
    def wants_opus(self):
        return False

    @override
    def write(self, user, data):
        if self.only_with is None or user == self.only_with:
            self.write_buf += data.pcm

    @AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member) -> None:
        if self.only_with is None or member == self.only_with:
            looptime = self.bot.loop.time()
            self.speak_start_time = looptime
            if (
                self.end_activity_handle
                and self.speak_end_time
                and looptime - self.speak_end_time < self.MIN_SILENCE_LENGTH
            ):
                self.end_activity_handle.cancel()
                self.end_activity_handle = None

    @AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member) -> None:
        if self.only_with is None or member == self.only_with:
            looptime = self.bot.loop.time()
            self.speak_end_time = looptime
            if self.speak_start_time and looptime - self.speak_start_time >= self.MIN_VOICE_LENGTH:
                if self.end_activity_handle:
                    self.end_activity_handle.cancel()
                self.end_activity_handle = self.bot.loop.call_later(
                    self.MIN_SILENCE_LENGTH, self.sumbit_activity
                )

    def sumbit_activity(self):
        self.req_queue.put_nowait(self.write_buf)
        self.write_buf = b''

    async def gemini_session(self):
        async with get_gemini().aio.live.connect(
            model='gemini-2.5-flash-preview-native-audio-dialog',
            config=types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                enable_affective_dialog=True,
                proactivity=types.ProactivityConfig(proactive_audio=True),
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
                ),
                speech_config=types.SpeechConfig(
                    language_code='fr-FR',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                    ),
                ),
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
                system_instruction=types.Content(
                    parts=[
                        types.Part(
                            text=(
                                f'The assistant is {self.bot.user}, a Discord bot.\n'
                                f'The current date is {datetime.now(TZ)}.\n'
                                f'RESPOND IN FRENCH. YOU MUST RESPOND UNMISTAKABLY IN FRENCH.'
                            )
                        )
                    ]
                ),
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        ) as session:
            logger.info('Gemini Live session started')
            self.receive_loop_task = asyncio.create_task(self.receive_loop(session))
            self.send_loop_task = asyncio.create_task(self.send_loop(session))
            await self.kill_event.wait()

    async def send_loop(self, session: live.AsyncSession):
        while True:
            buf = await self.req_queue.get()
            logger.info('Gemini Live activity sumbit')
            await session.send_realtime_input(activity_start=types.ActivityStart())
            # Discord audio is 32-bit signed stereo PCM at 48KHz.
            # Audio data in the Live API is always raw, little-endian, 16-bit PCM.
            # Input audio is natively 16kHz,
            # but the Live API will resample if needed so any sample rate can be sent.
            data = audioop.lin2lin(buf, 4, 2)
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type='audio/pcm;rate=48000')
            )
            await session.send_realtime_input(activity_end=types.ActivityEnd())

    async def receive_loop(self, session: live.AsyncSession):
        while True:
            with self.res_queue.mutex:
                self.res_queue.queue.clear()
            input_transcription = ''
            output_transcription = ''
            async for message in session.receive():
                if message.data:
                    self.res_queue.put_nowait(message.data)
                if message.server_content:
                    if transcription := message.server_content.input_transcription:
                        input_transcription += transcription.text or ''
                    if transcription := message.server_content.output_transcription:
                        output_transcription += transcription.text or ''
            logger.info(f'[{self.only_with or "Users"}] {input_transcription}')
            logger.info(f'[{self.voice_name}] {output_transcription}')

    @override
    def cleanup(self):
        self.req_queue.shutdown(immediate=True)
        self.res_queue.shutdown(immediate=True)
        if self.send_loop_task:
            self.send_loop_task.cancel()
        if self.receive_loop_task:
            self.receive_loop_task.cancel()
        self.kill_event.set()
        logger.info('Done cleaning Gemini Live')


class GeminiLiveAudioSource(discord.AudioSource):
    INPUT_FRAME_SIZE = 960  # 20ms at 24kHz 16-bit mono
    OUTPUT_FRAME_SIZE = 3840  # 20ms at 48kHz 16-bit stereo
    SILENCE = b'\x00' * OUTPUT_FRAME_SIZE

    def __init__(self, queue: Queue[bytes]):
        self.queue = queue
        self.buffer = bytearray()
        self.position = 0

    @override
    def read(self) -> bytes:
        while len(self.buffer) - self.position < self.INPUT_FRAME_SIZE:
            try:
                item = self.queue.get_nowait()
                self.buffer += item
                self.queue.task_done()
            except Empty:
                return self.SILENCE

        input_frame = self.buffer[self.position : self.position + self.INPUT_FRAME_SIZE]
        self.position += self.INPUT_FRAME_SIZE
        if self.position > 48000:
            self.buffer = self.buffer[self.position :]
            self.position = 0

        input_array = np.frombuffer(input_frame, dtype=np.int16)
        output_array = np.repeat(input_array, 4).astype(np.int16)
        output_frame = output_array.tobytes()

        return output_frame
