import asyncio
import logging
from datetime import timedelta

import discord.utils
from discord import ScheduledEvent, User

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import MultiplexingContext
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    GuildEventSelectAllResult,
    ParticipantAddBody,
    UpsertGuildEventBody,
    UpsertUserCalendarBody,
)

logger = logging.getLogger(__name__)


class Calendar_Generator(Cog, name='Calendar'):
    emoji = '📅'

    @Cog.listener()
    async def on_ready(self):
        from .profiles import Profiles

        profiles_cog = Profiles.get_cog(self.bot)
        if profiles_cog is not None:
            profiles_cog.registrars['Calendar'] = self.register

        asyncio.create_task(self.sync_all_events())

    async def register(self, interaction: discord.Interaction):
        """Register or change a member calendar"""

        def check(ctx: MultiplexingContext) -> bool:
            return ctx.author == interaction.user

        await interaction.response.edit_message(view=None)

        await interaction.followup.send(
            content=f'{interaction.user.mention}\nWhat is your calendar ics link?'
        )

        resp = await MultiplexingContext.set_will_delete(check=check)
        answer = resp.message
        ics = answer.content

        resp1 = await get_nanapi().calendar.calendar_upsert_user_calendar(
            interaction.user.id,
            UpsertUserCalendarBody(discord_username=str(interaction.user), ics=ics),
        )
        if not success(resp1):
            raise RuntimeError(resp1.result)

        await interaction.followup.send(content=self.bot.get_emoji_str('FubukiGO'))

    async def sync_all_events(self):
        logger.info('Start syncing all events')
        resp = await get_nanapi().calendar.calendar_get_guild_events()
        if not success(resp):
            raise RuntimeError(resp.result)
        db_events = {e.discord_id: e for e in resp.result}
        all_events = {e.id: e for guild in self.bot.guilds for e in guild.scheduled_events}
        for discord_id, event in db_events.items():
            if discord_id not in all_events:
                logger.debug(f'Deleting event {event.name} ({discord_id})')
                await get_nanapi().calendar.calendar_delete_guild_event(discord_id)
        for discord_id, event in all_events.items():
            await self.upsert_event(event)
            await self.reconcile_participants(event, db_events.get(discord_id))
        logger.info('Done syncing all events')

    @Cog.listener()
    async def on_scheduled_event_create(self, event: ScheduledEvent):
        await self.upsert_event(event)

    @Cog.listener()
    async def on_scheduled_event_delete(self, event: ScheduledEvent):
        logger.debug(f'Deleting event {event.name} ({event.id})')
        resp = await get_nanapi().calendar.calendar_delete_guild_event(event.id)
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_scheduled_event_update(self, _: ScheduledEvent, after: ScheduledEvent):
        await self.upsert_event(after)

    @Cog.listener()
    async def on_scheduled_event_user_add(self, event: ScheduledEvent, user: User):
        body = ParticipantAddBody(participant_id=user.id, participant_username=str(user))
        resp = await get_nanapi().calendar.calendar_add_participant_to_guild_event(event.id, body)
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_scheduled_event_user_remove(self, event: ScheduledEvent, user: User):
        resp = await get_nanapi().calendar.calendar_remove_participant_from_guild_event(
            event.id, user.id
        )
        if not success(resp):
            raise RuntimeError(resp.result)

    async def upsert_event(self, event: ScheduledEvent):
        # creator_id will be null and creator will not be included
        # for events created before October 25th, 2021
        if event.creator_id is None:
            return
        if event.creator is None:
            event.creator = await self.bot.fetch_user(event.creator_id)
        logger.debug(f'Creating event {event.name} ({event.id})')
        body = UpsertGuildEventBody(
            name=event.name,
            description=event.description,
            location=event.location or f'#{event.channel}',
            start_time=event.start_time,
            end_time=event.end_time or (event.start_time + timedelta(hours=2)),
            image=event.cover_image.url if event.cover_image else None,
            url=event.url,
            organizer_id=event.creator.id,
            organizer_username=str(event.creator),
        )
        resp = await get_nanapi().calendar.calendar_upsert_guild_event(event.id, body)
        if not success(resp):
            raise RuntimeError(resp.result)

    async def reconcile_participants(
        self,
        event: ScheduledEvent,
        db_event: GuildEventSelectAllResult | None,
    ):
        logger.debug(f'Reconciling participants for {event.name} ({event.id})')
        db_participants = {p.discord_id: p for p in db_event.participants} if db_event else {}
        async for participant in event.users():
            if participant.id not in db_participants:
                body = ParticipantAddBody(
                    participant_id=participant.id, participant_username=str(participant)
                )
                resp = await get_nanapi().calendar.calendar_add_participant_to_guild_event(
                    event.id, body
                )
                if not success(resp):
                    raise RuntimeError(resp.result)
            else:
                db_participants.pop(participant.id)
        for discord_id in db_participants:
            resp = await get_nanapi().calendar.calendar_remove_participant_from_guild_event(
                event.id, discord_id
            )
            if not success(resp):
                raise RuntimeError(resp.result)


async def setup(bot: Bot):
    await bot.add_cog(Calendar_Generator(bot))
