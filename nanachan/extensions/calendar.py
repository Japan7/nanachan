import asyncio
import logging
from datetime import datetime

import discord.utils
from discord import Interaction, ScheduledEvent, User
from yarl import URL

from nanachan.discord.application_commands import nana_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import MultiplexingContext
from nanachan.extensions.projection import ProjectionCog
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import ParticipantAddBody, UpsertUserCalendarBody
from nanachan.settings import JAPAN7_AUTH, NANAPI_CLIENT_USERNAME, NANAPI_URL, TZ
from nanachan.utils.calendar import reconcile_participants, upsert_event

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
        resp = await get_nanapi().calendar.calendar_get_guild_events(
            start_after=datetime.now(TZ).isoformat()  # type: ignore - FIXME: fix mahou.py
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        db_events = {e.discord_id: e for e in resp.result}
        all_events = {e.id: e for guild in self.bot.guilds for e in guild.scheduled_events}
        for discord_id, event in db_events.items():
            if discord_id not in all_events:
                logger.debug(f'Deleting event {event.name} ({discord_id})')
                await get_nanapi().calendar.calendar_delete_guild_event(discord_id)
        for discord_id, event in all_events.items():
            await upsert_event(self.bot, event)
            await reconcile_participants(event, db_events.get(discord_id))
        logger.info('Done syncing all events')

    @nana_command(description='Get my calendar ics link')
    async def ics(self, interaction: Interaction):
        url = URL(NANAPI_URL) / 'calendar' / 'ics'
        if JAPAN7_AUTH:
            url = url.with_user(JAPAN7_AUTH.login)
            url = url.with_password(JAPAN7_AUTH.password)
        url = url.with_query(client=NANAPI_CLIENT_USERNAME, discord_id=interaction.user.id)
        await interaction.response.send_message(content=f'`{url}`')

    @Cog.listener()
    async def on_scheduled_event_create(self, event: ScheduledEvent):
        await upsert_event(self.bot, event)

    @Cog.listener()
    async def on_scheduled_event_delete(self, event: ScheduledEvent):
        logger.debug(f'Deleting event {event.name} ({event.id})')
        resp = await get_nanapi().calendar.calendar_delete_guild_event(event.id)
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_scheduled_event_update(self, before: ScheduledEvent, after: ScheduledEvent):
        db_event = await upsert_event(self.bot, after)
        if db_event.projection:
            projo_cog = ProjectionCog.get_cog(self.bot)
            if projo_cog is not None:
                asyncio.create_task(projo_cog.update_projo_embed(db_event.projection))

    @Cog.listener()
    async def on_scheduled_event_user_add(self, event: ScheduledEvent, user: User):
        body = ParticipantAddBody(participant_id=user.id, participant_username=str(user))
        resp = await get_nanapi().calendar.calendar_add_guild_event_participant(event.id, body)
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_scheduled_event_user_remove(self, event: ScheduledEvent, user: User):
        resp = await get_nanapi().calendar.calendar_remove_guild_event_participant(
            event.id, user.id
        )
        if not success(resp):
            raise RuntimeError(resp.result)


async def setup(bot: Bot):
    await bot.add_cog(Calendar_Generator(bot))
