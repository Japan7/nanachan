from typing import AsyncGenerator, Iterable, Sequence

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

from nanachan.nanapi.client import get_nanapi
from nanachan.settings import AI_MODEL_CLS, AI_PROVIDER


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
