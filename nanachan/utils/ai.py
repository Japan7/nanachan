import asyncio
import logging
from contextlib import suppress
from functools import cache
from queue import Empty, Queue
from typing import AsyncGenerator, Iterable, Sequence, override

import discord
from discord.ext.voice_recv import AudioSink
from google import genai
from google.genai import live, types
from pydantic_ai import Agent, Tool
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
from pydantic_ai.models.anthropic import AnthropicModel

from nanachan.discord.bot import Bot
from nanachan.discord.helpers import UserType
from nanachan.nanapi.client import get_nanapi
from nanachan.settings import AI_GEMINI_API_KEY, AI_MODEL_CLS, AI_PROVIDER

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
) -> AsyncGenerator[str]:
    """https://ai.pydantic.dev/agents/#streaming"""
    # Workaround to avoid rate limit errors w/ Anthropic
    if isinstance(model, AnthropicModel):
        model.client.max_retries = 100
    async with (
        agent.run_mcp_servers(),
        agent.iter(
            user_prompt,
            message_history=message_history,
            model=model,
            deps=deps,
        ) as run,
    ):
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
                            yield f'```\n[TOOL] {event.part.tool_name} {event.part.args}\n```'
                        elif isinstance(event, FunctionToolResultEvent):  # type: ignore
                            ...
            elif Agent.is_end_node(node):
                # Once an End node is reached, the agent run is complete
                assert run.result
                message_history.extend(run.result.new_messages())


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


python_mcp_server = MCPServerStdio(
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


@cache
def get_gemini():
    assert AI_GEMINI_API_KEY
    return genai.Client(api_key=AI_GEMINI_API_KEY)


class GeminiLiveAudioSink(AudioSink):
    MIN_VOICE_LENGTH = 0.5
    MIN_SILENCE_LENGTH = 0.5

    def __init__(self, bot: Bot, user: UserType):
        super().__init__()
        self.bot = bot
        self.user = user

        self.start_activity_handle: asyncio.TimerHandle | None = None
        self.start_activity_time: float | None = None
        self.end_activity_handle: asyncio.TimerHandle | None = None
        self.end_activity_time: float | None = None

        self.in_activity = asyncio.Event()
        self.req_queue = asyncio.Queue[bytes | None]()
        self.res_queue = Queue[bytes]()

        asyncio.create_task(self.gemini_session())
        self.session_receive_task: asyncio.Task[None] | None = None

    @property
    def response_source(self):
        return GeminiLiveAudioSource(self.res_queue)

    @override
    def wants_opus(self):
        return False

    @override
    def write(self, user, data):
        if user == self.user:
            self.req_queue.put_nowait(data.pcm)

    @AudioSink.listener()
    def on_voice_member_speaking_start(self, member: discord.Member) -> None:
        if member == self.user:
            if (
                self.end_activity_handle
                and self.end_activity_time
                and self.bot.loop.time() - self.end_activity_time < self.MIN_SILENCE_LENGTH
            ):
                self.end_activity_handle.cancel()
                self.end_activity_handle = None
            else:
                self.start_activity_time = self.bot.loop.time()
                self.start_activity_handle = self.bot.loop.call_later(
                    self.MIN_VOICE_LENGTH, self.start_activity
                )

    @AudioSink.listener()
    def on_voice_member_speaking_stop(self, member: discord.Member) -> None:
        if member == self.user:
            if (
                self.start_activity_handle
                and self.start_activity_time
                and self.bot.loop.time() - self.start_activity_time < self.MIN_VOICE_LENGTH
            ):
                self.start_activity_handle.cancel()
                self.start_activity_handle = None
            else:
                self.end_activity_time = self.bot.loop.time()
                self.end_activity_handle = self.bot.loop.call_later(
                    self.MIN_SILENCE_LENGTH, self.end_activity
                )

    def start_activity(self):
        logger.info(f'Starting Gemini Live activity for {self.user}')
        self.in_activity.set()

    def end_activity(self):
        logger.info(f'Ending Gemini Live activity for {self.user}')
        self.in_activity.clear()
        self.req_queue.put_nowait(None)

    async def gemini_session(self):
        async with get_gemini().aio.live.connect(
            model='gemini-2.0-flash-live-001',
            config=types.LiveConnectConfig(
                system_instruction=types.Content(
                    parts=[types.Part(text='The assistant is Nana-chan. Nana-chan speaks French.')]
                ),
                response_modalities=[types.Modality.AUDIO],
                realtime_input_config=types.RealtimeInputConfig(
                    automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)
                ),
                speech_config=types.SpeechConfig(
                    language_code='fr-FR',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='aoede')
                    ),
                ),
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        ) as session:
            logger.info(f'Gemini Live session started for {self.user}')
            self.session_receive_task = asyncio.create_task(self.session_receive(session))
            with suppress(asyncio.QueueShutDown):
                await self.process_req_queue(session)

    async def process_req_queue(self, session: live.AsyncSession):
        while True:
            await self.in_activity.wait()
            await session.send_realtime_input(activity_start=types.ActivityStart())
            while True:
                item = await self.req_queue.get()
                if item is None:
                    self.req_queue.task_done()
                    break
                await session.send_realtime_input(
                    audio=types.Blob(data=item, mime_type='audio/pcm;rate=48000')
                )
                self.req_queue.task_done()
            await session.send_realtime_input(activity_end=types.ActivityEnd())

    async def session_receive(self, session: live.AsyncSession):
        while True:
            with self.res_queue.mutex:
                self.res_queue.queue.clear()
            async for message in session.receive():
                if message.data is not None:
                    self.res_queue.put_nowait(message.data)

    @override
    def cleanup(self):
        self.req_queue.shutdown(immediate=True)
        self.res_queue.shutdown(immediate=True)
        if self.session_receive_task:
            self.session_receive_task.cancel()
        logger.info(f'Done cleaning Gemini Live for {self.user}')


class GeminiLiveAudioSource(discord.AudioSource):
    input_frame_size = 960  # 20ms at 24kHz mono
    output_frame_size = 3840  # 20ms at 48kHz stereo
    silence = b'\x00' * output_frame_size

    def __init__(self, queue: Queue[bytes]):
        self.queue = queue
        self.buffer = bytearray()
        self.position = 0

    @override
    def read(self) -> bytes:
        while len(self.buffer) - self.position < self.input_frame_size:
            try:
                item = self.queue.get_nowait()
                self.buffer += item
                self.queue.task_done()
            except Empty:
                return self.silence

        input_frame = self.buffer[self.position : self.position + self.input_frame_size]
        self.position += self.input_frame_size
        if self.position > 48000:
            self.buffer = self.buffer[self.position :]
            self.position = 0

        output_frame = bytearray(self.output_frame_size)
        for i in range(0, len(input_frame), 2):
            sample = input_frame[i : i + 2]
            pos = i * 4
            output_frame[pos : pos + 2] = sample
            output_frame[pos + 2 : pos + 4] = sample
            output_frame[pos + 4 : pos + 6] = sample
            output_frame[pos + 6 : pos + 8] = sample

        return bytes(output_frame)
