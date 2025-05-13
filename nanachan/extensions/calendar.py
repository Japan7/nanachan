import asyncio
import logging
from contextlib import suppress
from datetime import datetime

import discord
from discord import (
    AllowedMentions,
    EventStatus,
    Forbidden,
    Interaction,
    Member,
    ScheduledEvent,
    User,
    VoiceState,
)
from discord.ext import commands
from yarl import URL

from nanachan.discord.application_commands import nana_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Members, MultiplexingContext
from nanachan.extensions.projection import ProjectionCog
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import ParticipantAddBody, UpsertUserCalendarBody
from nanachan.settings import NANALOOK_URL, NANAPI_CLIENT_USERNAME, NANAPI_PUBLIC_URL, TZ
from nanachan.utils.calendar import reconcile_participants, upsert_event
from nanachan.utils.projection import get_active_projo

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
            str(interaction.user.id),
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
        db_events = {int(e.discord_id): e for e in resp.result}
        all_events = {e.id: e for guild in self.bot.guilds for e in guild.scheduled_events}
        for discord_id, event in db_events.items():
            if discord_id not in all_events:
                logger.debug(f'Deleting event {event.name} ({discord_id})')
                await get_nanapi().calendar.calendar_delete_guild_event(str(discord_id))
        for discord_id, event in all_events.items():
            await upsert_event(self.bot, event)
            await reconcile_participants(event, db_events.get(discord_id))
        logger.info('Done syncing all events')

    @nana_command(description='Get my calendar ics link')
    async def ics(self, interaction: Interaction):
        url = URL(NANAPI_PUBLIC_URL) / 'calendar' / 'ics'
        url = url.with_query(client=NANAPI_CLIENT_USERNAME, user=interaction.user.id)
        await interaction.response.send_message(content=url, ephemeral=True)

    @nana_command(description='nanalook link')
    async def nanalook(self, interaction: Interaction, members: Members | None = None):
        if members:
            users = set(members)
            mention = ', '.join(u.mention for u in users)
        else:
            if isinstance(interaction.channel, discord.Thread):
                projo = await get_active_projo(interaction.channel.id)
                if projo:
                    url = URL(NANALOOK_URL) / str(projo.id)
                    await interaction.response.send_message(
                        content=f'[nanalook link](<{url}>) for **📽️ {projo.name}**'
                    )
                    return
                thread_members = await interaction.channel.fetch_members()
                users = [
                    user
                    for tm in thread_members
                    if (user := self.bot.get_user(tm.id)) and not user.bot
                ]
            elif isinstance(
                interaction.channel,
                (discord.VoiceChannel, discord.StageChannel, discord.TextChannel),
            ):
                users = [m for m in interaction.channel.members if not m.bot]
            else:
                raise commands.CommandError('This command should be used inside a text channel.')
            mention = interaction.channel.mention
        url = URL(NANALOOK_URL) / 'custom'
        url = url.with_query(users=','.join(str(u.id) for u in users))
        await interaction.response.send_message(
            content=f'[nanalook link](<{url}>) for {mention}',
            allowed_mentions=AllowedMentions.none(),
        )

    @Cog.listener()
    async def on_scheduled_event_create(self, event: ScheduledEvent):
        await upsert_event(self.bot, event)

    @Cog.listener()
    async def on_scheduled_event_delete(self, event: ScheduledEvent):
        logger.debug(f'Deleting event {event.name} ({event.id})')
        resp = await get_nanapi().calendar.calendar_delete_guild_event(str(event.id))
        if not success(resp):
            raise RuntimeError(resp.result)
        db_event = resp.result
        if db_event.projection:
            projo_cog = ProjectionCog.get_cog(self.bot)
            if projo_cog is not None:
                asyncio.create_task(projo_cog.update_projo_embed(db_event.projection))

    @Cog.listener()
    async def on_scheduled_event_update(self, before: ScheduledEvent, after: ScheduledEvent):
        db_event = await upsert_event(self.bot, after)
        if db_event.projection:
            projo_cog = ProjectionCog.get_cog(self.bot)
            if projo_cog is not None:
                asyncio.create_task(projo_cog.update_projo_embed(db_event.projection))

    @Cog.listener()
    async def on_scheduled_event_user_add(self, event: ScheduledEvent, user: User):
        await upsert_event(self.bot, event)
        body = ParticipantAddBody(participant_username=str(user))
        resp = await get_nanapi().calendar.calendar_add_guild_event_participant(
            str(event.id), str(user.id), body
        )
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_scheduled_event_user_remove(self, event: ScheduledEvent, user: User):
        resp = await get_nanapi().calendar.calendar_remove_guild_event_participant(
            str(event.id), str(user.id)
        )
        if not success(resp):
            raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if before.channel is None:
            return  # joining channel

        chan = before.channel

        if len(chan.voice_states) > 0:
            # there are still users in the voice channel
            return

        for event in chan.scheduled_events:
            if event.status is EventStatus.active:
                with suppress(Forbidden):
                    await event.end()


async def setup(bot: Bot):
    await bot.add_cog(Calendar_Generator(bot))
