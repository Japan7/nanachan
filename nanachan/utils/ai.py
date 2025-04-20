import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Iterable, Sequence

import discord
from discord.utils import time_snowflake
from pydantic_ai import Agent, ModelRetry, RunContext, Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
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

from nanachan.discord.application_commands import LegacyCommandContext
from nanachan.nanapi.client import get_nanapi
from nanachan.settings import TZ


@dataclass
class RunDeps:
    ctx: LegacyCommandContext


class AgentHelper:
    def __init__(self):
        self.agent = Agent(
            deps_type=RunDeps,
            tools=list(external_tools()),
            mcp_servers=[python_mcp_server],
        )
        self.lock = asyncio.Lock()

        @self.agent.tool
        def get_current_user(run_ctx: RunContext[RunDeps]):
            """Get name and Discord ID of the current user."""
            author = run_ctx.deps.ctx.author
            return {
                'id': author.id,
                'display_name': author.display_name,
                'global_name': author.global_name,
            }

        @self.agent.tool
        def get_current_channel(run_ctx: RunContext[RunDeps]):
            """Get name and channel ID of the current channel."""
            channel = run_ctx.deps.ctx.channel
            assert isinstance(
                channel,
                (discord.TextChannel, discord.Thread, discord.VoiceChannel),
            )
            resp = {
                'id': channel.id,
                'name': channel.name,
                'type': channel.type,
            }
            if isinstance(channel, discord.Thread) and channel.parent:
                resp['parent'] = {
                    'id': channel.parent.id,
                    'name': channel.parent.name,
                    'type': channel.parent.type,
                }
            return resp

        @self.agent.tool
        def get_current_time(run_ctx: RunContext[RunDeps]):
            """Get the current time."""
            return datetime.now(TZ)

        @self.agent.tool
        def get_members_name_discord_id_map(run_ctx: RunContext[RunDeps]):
            """Generate a mapping of Discord member display names to their Discord IDs."""
            bot = run_ctx.deps.ctx.bot
            return {member.display_name: member.id for member in bot.get_all_members()}

        @self.agent.tool
        def get_channels_name_channel_id_map(run_ctx: RunContext[RunDeps]):
            """Generate a mapping of Discord channel names to their channel IDs."""
            bot = run_ctx.deps.ctx.bot
            return {channel.name: channel.id for channel in bot.get_all_channels()}

        @self.agent.tool
        async def channel_history(
            run_ctx: RunContext[RunDeps],
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
            bot = run_ctx.deps.ctx.bot
            return await bot.http.logs_from(
                channel_id=channel_id,
                limit=limit,
                before=time_snowflake(before) if before else None,
                after=time_snowflake(after) if after else None,
                around=time_snowflake(around) if around else None,
            )

    async def iter_stream(
        self,
        user_prompt: Sequence[UserContent],
        message_history: list[ModelMessage],
        model: Model,
        deps: RunDeps,
    ) -> AsyncGenerator[str]:
        """https://ai.pydantic.dev/agents/#streaming"""
        # Workaround to avoid rate limit errors w/ Anthropic
        if isinstance(model, AnthropicModel):
            model.client.max_retries = 100
        async with (
            self.lock,
            self.agent.run_mcp_servers(),
            self.agent.iter(
                user_prompt,
                message_history=message_history,
                model=model,
                deps=deps,
            ) as run,
        ):
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    # A user prompt node
                    # => The user has provided input
                    ...
                elif Agent.is_model_request_node(node):
                    # A model request node
                    # => We can stream tokens from the model's request
                    async with node.stream(run.ctx) as request_stream:
                        buf = ''
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart):
                                    buf += event.part.content
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    buf += event.delta.content_delta
                                elif isinstance(event.delta, ToolCallPartDelta):
                                    ...
                            elif isinstance(event, FinalResultEvent):
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
                    # A handle-response node
                    # => The model returned some data, potentially calls a tool
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                yield f'```\n[TOOL] {event.part.tool_name} {event.part.args}\n```'
                            elif isinstance(event, FunctionToolResultEvent):
                                ...
                elif Agent.is_end_node(node):
                    # Once an End node is reached, the agent run is complete
                    assert run.result
                    message_history.extend(run.result.new_messages())


def external_tools() -> Iterable[Tool[Any]]:
    yield from nanapi_tools()
    yield duckduckgo_search_tool()


def nanapi_tools() -> Iterable[Tool[Any]]:
    nanapi = get_nanapi()
    endpoints = [
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
        nanapi.waicolle.waicolle_get_player_track_reversed,
        nanapi.waicolle.waicolle_get_player_media_stats,
        nanapi.waicolle.waicolle_get_player_staff_stats,
        nanapi.waicolle.waicolle_get_player_collection_stats,
        nanapi.waicolle.waicolle_get_waifus,
        nanapi.waicolle.waicolle_trade_index,
        nanapi.waicolle.waicolle_get_collection,
    ]
    for endpoint in endpoints:
        yield Tool(endpoint)


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
