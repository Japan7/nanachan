import asyncio
import logging
import re
from contextlib import suppress
from datetime import datetime, time, timedelta
from enum import Enum
from functools import partial
from operator import getitem
from typing import Iterable, MutableSequence, cast, override
from uuid import UUID

import discord
from discord import (
    EntityType,
    Interaction,
    PrivacyLevel,
    Thread,
    app_commands,
)
from discord.abc import GuildChannel
from discord.channel import TextChannel
from discord.errors import NotFound
from discord.ext import commands, tasks

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import get_option
from nanachan.discord.views import AutoNavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    GuildEventDeleteResultProjection,
    GuildEventMergeResultProjection,
    NewProjectionBody,
    ParticipantAddBody,
    ProjectionStatus,
    ProjoAddExternalMediaBody,
    ProjoInsertResult,
    ProjoSelectResult,
    ProjoSelectResultMedias,
    SetProjectionMessageIdBody,
    SetProjectionNameBody,
    SetProjectionStatusBody,
)
from nanachan.settings import (
    NANAPI_URL,
    PROJO_LEADER_ROLE_ID,
    PROJO_ROOM,
    PROJO_THREADS_ROOM,
    PROJO_VOICE,
    TZ,
    RequiresProjo,
)
from nanachan.utils.anilist import MediaType, media_autocomplete
from nanachan.utils.calendar import upsert_event
from nanachan.utils.misc import autocomplete_truncate, get_session
from nanachan.utils.projection import ProjectionView, get_active_projo, get_projo_embed_view

logger = logging.getLogger(__name__)


class ProjectionCog(
    NanaGroupCog, name='Projection', group_name='projo', required_settings=RequiresProjo
):
    """Suggest, vote and plan anime for upcoming projections"""

    emoji = '📽'

    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_cache: dict[int, discord.Message] = {}

    @Cog.listener()
    async def on_ready(self):
        resp = await get_nanapi().projection.projection_get_projections(
            ProjectionStatus.ONGOING.value
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result
        if projos is None:
            return
        for projo in projos:
            self.bot.add_view(ProjectionView(self.bot, projo.id))

        asyncio.create_task(self.sync_participants(projos))

        if not self.remind_projo.is_running():
            self.remind_projo.start()

    @override
    async def cog_unload(self):
        self.remind_projo.cancel()

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=TZ))
    async def remind_projo(self):
        now = datetime.now(tz=TZ)
        resp = await get_nanapi().projection.projection_get_projections(status='ONGOING')
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result
        for projo in projos:
            for event in projo.guild_events:
                if event.start_time > now and event.start_time <= now + timedelta(hours=24):
                    thread = self.bot.get_thread(int(projo.channel_id))
                    event_url = f'https://discord.com/events/{thread.guild.id}/{event.discord_id}'
                    await thread.send(
                        f'[Event]({event_url}) starts <t:{event.start_time.timestamp():.0f}:R>.'
                    )
                    break

    async def sync_participants(self, projos: list[ProjoSelectResult]):
        logger.info('Start syncing projo participants')
        for projo in projos:
            projo_chan = self.bot.get_channel(int(projo.channel_id))
            if not isinstance(projo_chan, Thread):
                continue
            await self.sync_projo_participants(projo, projo_chan)
        logger.info('Done syncing projo participants')

    async def sync_projo_participants(
        self, projo: ProjoSelectResult | ProjoInsertResult, projo_chan: Thread
    ):
        db_participants = (
            {int(p.discord_id) for p in projo.participants}
            if isinstance(projo, ProjoSelectResult)
            else set[int]()
        )

        members = await projo_chan.fetch_members()
        discord_participants = {m.id: self.bot.get_user(m.id) for m in members}

        for discord_id, user in discord_participants.items():
            if discord_id not in db_participants:
                body = ParticipantAddBody(participant_username=str(user))
                resp = await get_nanapi().projection.projection_add_projection_participant(
                    projo.id, str(discord_id), body
                )
                if not success(resp):
                    raise RuntimeError(resp.result)
            else:
                db_participants.remove(discord_id)

        for discord_id in db_participants:
            resp = await get_nanapi().projection.projection_remove_projection_participant(
                projo.id, str(discord_id)
            )
            if not success(resp):
                raise RuntimeError(resp.result)

    async def add_projo_leader_role(
        self, user: discord.Member | discord.User, reason: str = 'Created a projection'
    ):
        if isinstance(user, discord.User):
            # this branch might not be useful but whatever
            projo_chan = self.bot.get_channel(PROJO_ROOM)
            assert isinstance(projo_chan, GuildChannel)
            member = projo_chan.guild.get_member(user.id)
            assert member is not None
        else:
            member = user

        projo_leader_role = member.guild.get_role(PROJO_LEADER_ROLE_ID)
        assert projo_leader_role is not None
        await member.add_roles(projo_leader_role, reason=reason)

    @app_commands.command()
    @legacy_command()
    async def new(self, ctx: LegacyCommandContext, name: str):
        """Start a new projection"""
        await ctx.defer()

        if not isinstance(ctx.channel, discord.Thread):
            raise commands.CommandError('This command should be used inside a thread.')

        resp = await get_nanapi().projection.projection_get_projections(
            channel_id=str(ctx.channel.id)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result
        if any([projo.status is ProjectionStatus.ONGOING for projo in projos]):
            raise commands.CommandError('A projection is already ongoing in this thread')

        resp = await get_nanapi().projection.projection_new_projection(
            NewProjectionBody(name=name, channel_id=str(ctx.channel.id))
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        projo = resp.result

        await self.sync_projo_participants(projo, ctx.channel)

        embed, view = await get_projo_embed_view(self.bot, projo.id)
        vote_chan = self.bot.get_text_channel(PROJO_THREADS_ROOM)
        assert vote_chan
        info_msg = await vote_chan.send(embed=embed, view=view)

        resp1 = await get_nanapi().projection.projection_set_projection_message_id(
            projo.id, SetProjectionMessageIdBody(message_id=str(info_msg.id))
        )
        if not success(resp1):
            raise RuntimeError(resp1.result)

        await ctx.reply(
            f'New **{name}** [projection]({info_msg.jump_url}) started. '
            f'{self.bot.get_emoji_str("FubukiGO")}'
        )
        await self.add_projo_leader_role(ctx.author)

    @app_commands.command()
    @legacy_command()
    async def rename(self, ctx: LegacyCommandContext, name: str):
        """Rename the projection"""
        await ctx.defer()
        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        resp = await get_nanapi().projection.projection_set_projection_name(
            projo.id, SetProjectionNameBody(name=name)
        )
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        'This command should be used inside an active projection thread'
                    )
                case _:
                    raise RuntimeError(resp.result)

        embed = await self.update_projo_embed(projo)
        await ctx.reply(f'Projection renamed. {self.bot.get_emoji_str("FubukiGO")}', embed=embed)

    @app_commands.command()
    @legacy_command()
    async def cancel(self, ctx: LegacyCommandContext):
        """Cancel the projection"""
        await ctx.defer()
        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )
        resp = await get_nanapi().projection.projection_delete_projection(projo.id)
        if not success(resp):
            raise RuntimeError(resp.result)

        assert projo.message_id is not None
        info_msg = await self.fetch_message(int(projo.message_id))
        await info_msg.delete()
        await ctx.reply(f'The projection was cancelled. {self.bot.get_emoji_str("FubukiGO")}')

    class MediaChoice(Enum):
        anime = 'anime'
        other = 'other'

    async def add_autocomplete(self, interaction: Interaction, current: str):
        media_type = get_option(
            interaction, 'media_type', cast_func=partial(getitem, self.MediaChoice)
        )

        if media_type is self.MediaChoice.anime:
            return await media_autocomplete(MediaType.ANIME, id_al_as_value=True)(
                interaction, current
            )
        else:
            return []

    @app_commands.command()
    @app_commands.autocomplete(name=add_autocomplete)
    @legacy_command()
    async def add(self, ctx: LegacyCommandContext, media_type: MediaChoice, name: str):
        """Add something to the projection"""
        await ctx.defer()

        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        if media_type is self.MediaChoice.anime:
            anime_id = int(name)
            resp = await get_nanapi().projection.projection_add_projection_anilist_media(
                projo.id, anime_id
            )
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            resp = await get_nanapi().projection.projection_add_projection_external_media(
                projo.id, ProjoAddExternalMediaBody(title=name)
            )
            if not success(resp):
                raise RuntimeError(resp.result)

        embed = await self.update_projo_embed(projo)
        await ctx.reply(
            f'**{name}** added to the projection. {self.bot.get_emoji_str("FubukiGO")}',
            embed=embed,
        )

    class ProjectionFolder(Enum):
        anno = 'anno'
        miyazaki = 'miyazaki'
        naoko = 'naoko'
        oshii = 'oshii'
        shinbou = 'shinbou'

    dans_regexp = re.compile(r'^\[📽️(\/?[^\[\]]*)\]')

    @app_commands.command(name='dans')
    async def projo_dans(self, interaction: Interaction, folder: ProjectionFolder):
        await interaction.response.defer()

        if not isinstance(interaction.channel, discord.Thread):
            raise commands.CommandError('This command should be used inside a thread.')

        projo = await get_active_projo(interaction.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        discord_event = None
        for event in sorted(projo.guild_events, key=lambda e: e.start_time):
            if event.start_time < datetime.now(TZ):
                continue
            assert interaction.guild
            with suppress(NotFound):
                discord_event = await interaction.guild.fetch_scheduled_event(
                    int(event.discord_id)
                )
                new_name = self.dans_regexp.sub(f'[📽️/{folder.value}]', discord_event.name)
                await discord_event.edit(name=new_name)
                await interaction.followup.send(
                    f'[projo]({discord_event.url}) dans {folder.value}'
                )
                break  # only set the first event

        if discord_event is None:
            await interaction.followup.send('Event not found')
            return

    async def remove_autocomplete(self, interaction: Interaction, current: str):
        assert interaction.channel is not None
        projo = await get_active_projo(interaction.channel.id)
        if projo is None:
            return []

        media_type = get_option(
            interaction, 'media_type', cast_func=partial(getitem, self.MediaChoice)
        )
        if media_type is self.MediaChoice.anime:
            return [
                app_commands.Choice(
                    name=autocomplete_truncate(media.title_user_preferred), value=str(media.id_al)
                )
                for media in projo.medias
            ]
        elif media_type is self.MediaChoice.other:
            return [
                app_commands.Choice(name=autocomplete_truncate(media.title), value=str(media.id))
                for media in projo.external_medias
            ]
        else:
            return []

    @app_commands.command()
    @app_commands.autocomplete(item=remove_autocomplete)
    @legacy_command()
    async def remove(self, ctx: LegacyCommandContext, media_type: MediaChoice, item: str):
        """Remove something from the projection"""
        await ctx.defer()
        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )
        if media_type is self.MediaChoice.anime:
            id_al = int(item)
            resp = await get_nanapi().projection.projection_remove_projection_media(
                projo.id, id_al
            )
            if not success(resp):
                raise RuntimeError(resp.result)
        elif media_type is self.MediaChoice.other:
            uuid = UUID(item)
            resp = await get_nanapi().projection.projection_remove_projection_external_media(
                projo.id, uuid
            )
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            raise RuntimeError('How did you get here?')

        embed = await self.update_projo_embed(projo)
        await ctx.reply(
            f'Media removed from the projection. {self.bot.get_emoji_str("FubukiGO")}',
            embed=embed,
        )

    @app_commands.command()
    @legacy_command()
    async def completed(self, ctx: LegacyCommandContext):
        """Mark current projection as completed"""
        await ctx.defer()
        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )
        resp = await get_nanapi().projection.projection_set_projection_status(
            projo.id, SetProjectionStatusBody(status=ProjectionStatus.COMPLETED.value)
        )
        if not success(resp):
            raise RuntimeError(resp.result)

        assert projo.message_id is not None
        info_msg = await self.fetch_message(int(projo.message_id))
        await info_msg.delete()
        await ctx.reply(
            f'The projection was marked as completed. {self.bot.get_emoji_str("FubukiGO")}'
        )

    slash_projo_event = app_commands.Group(name='event', description='Commands related to events')

    class EventChoice(Enum):
        onsite = 'onsite'
        online = 'online'

    @slash_projo_event.command(name='add')
    @app_commands.describe(date_str='YYYY-MM-DD')
    @app_commands.rename(date_str='date')
    @legacy_command()
    async def event_add(
        self,
        ctx: LegacyCommandContext,
        event_type: EventChoice,
        name: str,
        date_str: str,
        hour: int,
        minute: int,
    ):
        """Plan an new event"""
        await ctx.defer()

        try:
            date: datetime = datetime.fromisoformat(date_str)
        except ValueError:
            raise commands.BadArgument('Date format is `YYYY-MM-DD`')
        date = date.replace(hour=hour, minute=minute, tzinfo=TZ)

        today = datetime.today()
        today = today.replace(tzinfo=TZ)

        if date < today:
            eilene_ded = self.bot.get_emoji_str('EileneDed')
            raise commands.CommandError(f'Event date is in the past {eilene_ded}')

        projection = await get_active_projo(ctx.channel.id)
        if projection is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        # discord guild event
        event = await self.create_guild_event(projection, event_type, name, date)

        db_event = await upsert_event(self.bot, event)  # make sure the event is in the db
        resp = await get_nanapi().projection.projection_add_projection_guild_event(
            projection.id, db_event.discord_id
        )
        if not success(resp):
            raise RuntimeError(resp.result)

        await self.update_projo_embed(projection)

        await ctx.reply(f'[New event]({event.url}) added. {self.bot.get_emoji_str("FubukiGO")}')
        await self.add_projo_leader_role(ctx.author)

    async def create_guild_event(
        self,
        projection: ProjoSelectResult,
        event_type: EventChoice,
        event_name: str,
        date: datetime,
    ):
        orga_chan = self.bot.get_channel(int(projection.channel_id))
        assert isinstance(orga_chan, TextChannel | Thread)
        ev_desc = [orga_chan.mention, f'**{projection.name}**']

        def desc_len(description: list[str], new_entry: str):
            return sum(map(len, description)) + len(description) + len(new_entry)

        anime_ids = []
        for anime in projection.medias:
            entry = f'• {anime.title_user_preferred} – https://anilist.co/anime/{anime.id_al}'
            if desc_len(ev_desc, entry) < 1000:
                ev_desc.append(entry)
            anime_ids.append(anime.id_al)

        if len(anime_ids) > 0:
            anime_ids_str = ','.join(map(str, anime_ids))
            async with get_session().get(
                f'{NANAPI_URL}/anilist/medias/collages', params=dict(ids_al=anime_ids_str)
            ) as resp:
                img = await resp.read()
        else:
            img = discord.utils.MISSING

        for other in projection.external_medias:
            entry = f'• {other.title}'
            if desc_len(ev_desc, entry) < 1000:
                ev_desc.append(entry)

        date = date.replace(tzinfo=TZ)
        if event_type is self.EventChoice.online:
            projo_voice = self.bot.get_channel(PROJO_VOICE)
            assert isinstance(projo_voice, discord.VoiceChannel)
            event = await projo_voice.guild.create_scheduled_event(
                name=f'[📽️] {event_name}',
                channel=projo_voice,
                start_time=date,
                description='\n'.join(ev_desc),
                privacy_level=PrivacyLevel.guild_only,
                image=img,
            )
        else:
            projo_chan = self.bot.get_channel(PROJO_ROOM)
            assert isinstance(projo_chan, TextChannel)
            event = await projo_chan.guild.create_scheduled_event(
                name=f'[📽️] {event_name}',
                start_time=date,
                end_time=date + timedelta(hours=1, minutes=30),
                location='n7 – A301',
                entity_type=EntityType.external,
                privacy_level=PrivacyLevel.guild_only,
                description='\n'.join(ev_desc),
                image=img,
            )

        return event

    @slash_projo_event.command(name='clear')
    @legacy_command()
    async def event_clear(self, ctx: LegacyCommandContext):
        """Clear all upcoming events"""
        await ctx.defer()
        projection = await get_active_projo(ctx.channel.id)
        if projection is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        nanapi = get_nanapi()
        resp = await nanapi.projection.projection_delete_upcoming_projection_events(projection.id)
        if not success(resp):
            raise RuntimeError(resp.result)

        embed = await self.update_projo_embed(projection)

        assert ctx.guild
        for event in projection.guild_events:
            with suppress(NotFound):
                discord_event = await ctx.guild.fetch_scheduled_event(int(event.discord_id))
                await discord_event.delete()

        await ctx.reply(
            f'Upcoming events cleared. {self.bot.get_emoji_str("FubukiGO")}', embed=embed
        )

    @app_commands.command()
    @legacy_command()
    async def history(self, ctx: LegacyCommandContext):
        """Projections history"""
        await ctx.defer()

        resp = await get_nanapi().projection.projection_get_projections(
            status=ProjectionStatus.COMPLETED.value
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result

        content: list[str] = []
        last_events: MutableSequence[datetime | None] = []
        for projo in projos:
            events = projo.guild_events
            if events:
                last_events.append(events[-1].start_time)
                date = f'`[{events[-1].start_time}]` '
            else:
                last_events.append(None)
                date = ''

            subcontent = [f'**{projo.name}**']
            all_medias = projo.medias + projo.external_medias
            for media in sorted(
                all_medias, key=lambda m: m.added_alias if m.added_alias is not None else 0
            ):
                if isinstance(media, ProjoSelectResultMedias):
                    subcontent.append(
                        f'​　　[{media.title_user_preferred}](https://anilist.co/anime/{media.id_al})'
                    )
                else:
                    subcontent.append(f'​　　{media.title}')

            content.append(date + '\n'.join(sorted(subcontent, key=str.casefold)))

        # First sort the ones with event date
        content1, _ = zip(
            *sorted(
                (
                    cast(tuple[str, datetime], cpl)
                    for cpl in zip(content, last_events)
                    if cpl[1] is not None
                ),
                key=lambda cpl: cpl[1],
                reverse=True,
            )
        )

        # Then the others by event name
        content2, _, _ = zip(
            *sorted(
                filter(lambda cpl: not cpl[2], zip(content, projos, last_events)),
                key=lambda cpl: cpl[1].name.casefold(),
            )
        )

        content_iter: Iterable[str] = content1 + content2  # type: ignore

        await AutoNavigatorView.create(
            self.bot,
            ctx.reply,
            title='Watched anime',
            description='\n'.join(content_iter),
            color=0x9966CC,
        )

    async def update_projo_embed(
        self,
        projection: ProjoSelectResult
        | GuildEventMergeResultProjection
        | GuildEventDeleteResultProjection,
    ):
        embed, view = await get_projo_embed_view(self.bot, projection.id)
        assert projection.message_id
        message = await self.fetch_message(int(projection.message_id))
        await message.edit(embed=embed, view=view)
        return embed

    #############
    # Listeners #
    #############

    async def fetch_message(self, message_id: int):
        if message_id not in self.message_cache:
            try:
                channel = self.bot.get_channel(PROJO_THREADS_ROOM)
                assert isinstance(channel, TextChannel)
                self.message_cache[message_id] = await channel.fetch_message(message_id)
            except discord.NotFound:
                print('message not found:', message_id)
                raise
        return self.message_cache[message_id]

    @Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if after.archived:
            projo = await get_active_projo(after.id)
            if projo is not None:
                await after.edit(archived=False)

    @Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        user = self.bot.get_user(member.id)
        if user is None or user.bot:
            return

        projo = await get_active_projo(member.thread_id)
        if projo is not None:
            await self.update_projo_embed(projo)
            body = ParticipantAddBody(participant_username=str(user))
            resp = await get_nanapi().projection.projection_add_projection_participant(
                projo.id, str(user.id), body
            )
            if not success(resp):
                raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember):
        user = self.bot.get_user(member.id)
        assert user is not None
        if user.bot:
            return

        projo = await get_active_projo(member.thread_id)
        if projo is not None:
            await self.update_projo_embed(projo)
            resp = await get_nanapi().projection.projection_remove_projection_participant(
                projo.id, str(user.id)
            )
            if not success(resp):
                raise RuntimeError(resp.result)


async def setup(bot: Bot):
    await bot.add_cog(ProjectionCog(bot))
