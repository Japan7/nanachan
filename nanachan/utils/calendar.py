import logging
from datetime import timedelta

from discord import ScheduledEvent

from nanachan.discord.bot import Bot
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    GuildEventMergeResult,
    GuildEventSelectResult,
    ParticipantAddBody,
    UpsertGuildEventBody,
)

logger = logging.getLogger(__name__)


async def upsert_event(bot: Bot, event: ScheduledEvent) -> GuildEventMergeResult:
    if event.creator_id is None:
        # creator_id will be null and creator will not be included
        # for events created before October 25th, 2021
        raise ValueError('Event creator ID is required')

    if event.creator is None:
        event.creator = await bot.fetch_user(event.creator_id)

    logger.debug(f'Creating event {event.name} ({event.id})')

    end_time = event.end_time
    if end_time is None or end_time <= event.start_time:
        end_time = event.start_time + timedelta(hours=2)

    body = UpsertGuildEventBody(
        name=event.name,
        description=event.description,
        location=event.location or f'#{event.channel}',
        start_time=event.start_time,
        end_time=end_time,
        image=event.cover_image.url if event.cover_image else None,
        url=event.url,
        organizer_id=str(event.creator.id),
        organizer_username=str(event.creator),
    )
    resp = await get_nanapi().calendar.calendar_upsert_guild_event(str(event.id), body)
    if not success(resp):
        raise RuntimeError(resp.result)

    return resp.result


async def reconcile_participants(
    event: ScheduledEvent,
    db_event: GuildEventSelectResult | None,
):
    logger.debug(f'Reconciling participants for {event.name} ({event.id})')
    db_participants = {p.discord_id for p in db_event.participants} if db_event else set()
    async for participant in event.users():
        if participant.id not in db_participants:
            body = ParticipantAddBody(participant_username=str(participant))
            resp = await get_nanapi().calendar.calendar_add_guild_event_participant(
                str(event.id), str(participant.id), body
            )
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            db_participants.remove(str(participant.id))
    for discord_id in db_participants:
        resp = await get_nanapi().calendar.calendar_remove_guild_event_participant(
            str(event.id), discord_id
        )
        if not success(resp):
            raise RuntimeError(resp.result)
