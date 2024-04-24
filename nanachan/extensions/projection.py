import re
from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum
from functools import partial
from operator import getitem
from typing import Iterable, MutableSequence, cast
from uuid import UUID

import discord
from discord import (
    EntityType,
    EventStatus,
    Interaction,
    PrivacyLevel,
    Thread,
    app_commands,
)
from discord.abc import GuildChannel
from discord.channel import TextChannel
from discord.errors import NotFound
from discord.ext import commands

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import get_option
from nanachan.discord.views import AutoNavigatorView
from nanachan.extensions.calendar import Calendar_Generator
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    NewProjectionBody,
    NewProjectionEventBody,
    ProjectionStatus,
    ProjoAddExternalMediaBody,
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
from nanachan.utils.misc import autocomplete_truncate, get_session
from nanachan.utils.projection import ProjectionView, get_active_projo, get_projo_embed_view


@RequiresProjo
class ProjectionCog(NanaGroupCog, name="Projection", group_name="projo"):
    """ Suggest, vote and plan anime for upcoming projections """
    emoji = "📽"

    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_cache: dict[int, discord.Message] = {}

    @Cog.listener()
    async def on_ready(self):
        resp = await get_nanapi().projection.projection_get_projections(
            ProjectionStatus.ONGOING.value)
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result
        if projos is None:
            return
        for projo in projos:
            self.bot.add_view(ProjectionView(self.bot, projo.id))

    async def add_projo_leader_role(self, user: discord.Member | discord.User,
                                    reason: str = "Created a projection"):
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
            raise commands.CommandError(
                'This command should be used inside a thread.')

        resp = await get_nanapi().projection.projection_get_projections(
            channel_id=ctx.channel.id)
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result
        if any([projo.status is ProjectionStatus.ONGOING for projo in projos]):
            raise commands.CommandError(
                "A projection is already ongoing in this thread")

        resp = await get_nanapi().projection.projection_new_projection(
            NewProjectionBody(name=name, channel_id=ctx.channel.id))
        if not success(resp):
            raise RuntimeError(resp.result)
        projo = resp.result

        embed, view = await get_projo_embed_view(self.bot, projo.id)
        vote_chan = self.bot.get_text_channel(PROJO_THREADS_ROOM)
        assert vote_chan
        info_msg = await vote_chan.send(embed=embed, view=view)

        resp1 = await get_nanapi().projection.projection_set_projection_message_id(
            projo.id, SetProjectionMessageIdBody(message_id=info_msg.id))
        if not success(resp1):
            raise RuntimeError(resp1.result)

        await ctx.reply(
            f"New **{name}** [projection]({info_msg.jump_url}) started. "
            f"{self.bot.get_emoji_str('FubukiGO')}")
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
            projo.id, SetProjectionNameBody(name=name))
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        'This command should be used inside an active projection thread'
                    )
                case _:
                    raise RuntimeError(resp.result)

        embed, view = await get_projo_embed_view(self.bot, projo.id)
        assert projo.message_id is not None
        info_msg = await self.fetch_message(projo.message_id)
        await info_msg.edit(embed=embed, view=view)
        await ctx.reply(
            f"Projection renamed. {self.bot.get_emoji_str('FubukiGO')}",
            embed=embed)

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
        info_msg = await self.fetch_message(projo.message_id)
        await info_msg.delete()
        await ctx.reply(
            f"The projection was cancelled. {self.bot.get_emoji_str('FubukiGO')}"
        )

    class MediaChoice(Enum):
        anime = "anime"
        other = "other"

    async def add_autocomplete(self, interaction: Interaction, current: str):
        media_type = get_option(interaction,
                                'media_type',
                                cast_func=partial(getitem, self.MediaChoice))

        if media_type is self.MediaChoice.anime:
            return await media_autocomplete(MediaType.ANIME,
                                            id_al_as_value=True)(interaction,
                                                                 current)
        else:
            return []

    @app_commands.command()
    @app_commands.autocomplete(name=add_autocomplete)
    @legacy_command()
    async def add(self, ctx: LegacyCommandContext, media_type: MediaChoice,
                  name: str):
        """Add something to the projection"""
        await ctx.defer()

        projo = await get_active_projo(ctx.channel.id)
        if projo is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        if media_type is self.MediaChoice.anime:
            anime_id = int(name)
            resp = await get_nanapi(
            ).projection.projection_add_projection_anilist_media(
                projo.id, anime_id)
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            resp = await get_nanapi(
            ).projection.projection_add_projection_external_media(
                projo.id, ProjoAddExternalMediaBody(title=name))
            if not success(resp):
                raise RuntimeError(resp.result)

        embed, view = await get_projo_embed_view(self.bot, projo.id)

        assert projo.message_id is not None
        info_msg = await self.fetch_message(projo.message_id)

        await info_msg.edit(embed=embed, view=view)
        await ctx.reply(
            f"**{name}** added to the projection. {self.bot.get_emoji_str('FubukiGO')}",
            embed=embed)


    class ProjectionFolder(Enum):
        anno = "anno"
        miyazaki = "miyazaki"
        naoko = "naoko"
        oshii = "oshii"
        shinbou = "shinbou"

    async def get_projo_events(self, channel: Thread):
        calcog = Calendar_Generator.get_cog(self.bot)
        if calcog is None:
            return

        assert channel is not None
        for discord_event_id, event in calcog.events.items():
            if event.description is None:
                continue

            if channel.mention in event.description:
                assert channel.guild is not None
                with suppress(NotFound):
                    d_event = await channel.guild.fetch_scheduled_event(discord_event_id)
                    if d_event.status == EventStatus.scheduled:
                        yield d_event

    dans_regexp = re.compile(r"^\[📽️(\/?[^\[\]]*)\]")

    @app_commands.command(name="dans")
    async def projo_dans(self, interaction: Interaction, folder: ProjectionFolder):
        if not isinstance(interaction.channel, Thread):
            await interaction.response.send_message(
                "This command should only be used in a thread"
            )
            return
        await interaction.response.defer()

        discord_event = None
        async for discord_event in self.get_projo_events(interaction.channel):
            new_name = self.dans_regexp.sub(f"[📽️/{folder.value}]", discord_event.name)
            await discord_event.edit(name=new_name)
            await interaction.followup.send(f"[projo]({discord_event.url}) dans {folder.value}")
            break # only set the first event

        if discord_event is None:
            await interaction.followup.send("Event not found")
            return

    async def remove_autocomplete(self, interaction: Interaction, current: str):
        assert interaction.channel is not None
        projo = await get_active_projo(interaction.channel.id)
        if projo is None:
            return []

        media_type = get_option(interaction,
                                'media_type',
                                cast_func=partial(getitem, self.MediaChoice))
        if media_type is self.MediaChoice.anime:
            return [
                app_commands.Choice(name=autocomplete_truncate(media.title_user_preferred),
                                    value=str(media.id_al))
                for media in projo.medias
            ]
        elif media_type is self.MediaChoice.other:
            return [
                app_commands.Choice(name=autocomplete_truncate(media.title),
                                    value=str(media.id))
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
                projo.id, id_al)
            if not success(resp):
                raise RuntimeError(resp.result)
        elif media_type is self.MediaChoice.other:
            uuid = UUID(item)
            resp = await get_nanapi().projection.projection_remove_projection_external_media(
                projo.id, uuid)
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            raise RuntimeError('How did you get here?')
        embed, view = await get_projo_embed_view(self.bot, projo.id)

        assert projo.message_id is not None
        info_msg = await self.fetch_message(projo.message_id)
        await info_msg.edit(embed=embed, view=view)
        await ctx.reply(
            f"Media removed from the projection. "
            f"{self.bot.get_emoji_str('FubukiGO')}",
            embed=embed)

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
            projo.id,
            SetProjectionStatusBody(status=ProjectionStatus.COMPLETED.value))
        if not success(resp):
            raise RuntimeError(resp.result)

        assert projo.message_id is not None
        info_msg = await self.fetch_message(projo.message_id)
        await info_msg.delete()
        await ctx.reply(
            f"The projection was marked as completed. {self.bot.get_emoji_str('FubukiGO')}"
        )

    slash_projo_event = app_commands.Group(
        name="event", description="Commands related to events")

    class EventChoice(Enum):
        onsite = "onsite"
        online = "online"

    @slash_projo_event.command(name="add")
    @app_commands.describe(date_str="YYYY-MM-DD")
    @app_commands.rename(date_str="date")
    @legacy_command()
    async def event_add(self, ctx: LegacyCommandContext,
                        event_type: EventChoice, name: str, date_str: str,
                        hour: int, minute: int):
        """Plan an new event"""
        await ctx.defer()

        try:
            date: datetime = datetime.fromisoformat(date_str)
        except ValueError:
            raise commands.BadArgument("Date format is `YYYY-MM-DD`")
        date = date.replace(hour=hour, minute=minute, tzinfo=TZ)

        today = datetime.today()
        today = today.replace(tzinfo=TZ)

        if date < today:
            eilene_ded = self.bot.get_emoji_str('EileneDed')
            raise commands.CommandError(
                f"Event date is in the past {eilene_ded}")

        projection = await get_active_projo(ctx.channel.id)
        if projection is None:
            raise commands.CommandError(
                'This command should be used inside an active projection thread'
            )

        resp = await get_nanapi().projection.projection_new_projection_event(
            projection.id, NewProjectionEventBody(description=name, date=date))
        if not success(resp):
            raise RuntimeError(resp.result)

        assert projection.message_id is not None
        message = await self.fetch_message(projection.message_id)
        embed, view = await get_projo_embed_view(self.bot, projection.id)
        await message.edit(embed=embed, view=view)

        # discord guild event
        event = await self.create_guild_event(projection, event_type, name,
                                              date)

        await ctx.reply(f"[New event]({event.url}) added. "
                        f"{self.bot.get_emoji_str('FubukiGO')}")
        await self.add_projo_leader_role(ctx.author)

    async def create_guild_event(self, projection: ProjoSelectResult,
                                 event_type: EventChoice, event_name: str,
                                 date: datetime):
        orga_chan = self.bot.get_channel(projection.channel_id)
        assert isinstance(orga_chan, TextChannel | Thread)
        ev_desc = [orga_chan.mention, f"**{projection.name}**"]

        def desc_len(description: list[str], new_entry: str):
            return sum(map(len, description)) + len(description) + len(new_entry)

        anime_ids = []
        for anime in projection.medias:
            entry = f"• {anime.title_user_preferred} – https://anilist.co/anime/{anime.id_al}"
            if desc_len(ev_desc, entry) < 1000:
                ev_desc.append(entry)
            anime_ids.append(anime.id_al)

        if len(anime_ids) > 0:
            anime_ids_str = ','.join(map(str, anime_ids))
            async with get_session().get(f"{NANAPI_URL}/anilist/medias/collages",
                                         params=dict(ids_al=anime_ids_str)) as resp:
                img = await resp.read()
        else:
            img = discord.utils.MISSING

        for other in projection.external_medias:
            entry = f"• {other.title}"
            if desc_len(ev_desc, entry) < 1000:
                ev_desc.append(entry)

        date = date.replace(tzinfo=TZ)
        if event_type is self.EventChoice.online:
            projo_voice = self.bot.get_channel(PROJO_VOICE)
            assert isinstance(projo_voice, discord.VoiceChannel)
            event = await projo_voice.guild.create_scheduled_event(
                name=f"[📽️] {event_name}",
                channel=projo_voice,
                start_time=date,
                description='\n'.join(ev_desc),
                privacy_level=PrivacyLevel.guild_only,
                image=img)
        else:
            projo_chan = self.bot.get_channel(PROJO_ROOM)
            assert isinstance(projo_chan, TextChannel)
            event = await projo_chan.guild.create_scheduled_event(
                name=f"[📽️] {event_name}",
                start_time=date,
                end_time=date + timedelta(hours=1, minutes=30),
                location='n7 – A301',
                entity_type=EntityType.external,
                privacy_level=PrivacyLevel.guild_only,
                description='\n'.join(ev_desc),
                image=img)

        return event

    @slash_projo_event.command(name="clear")
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
        embed, view = await get_projo_embed_view(self.bot, projection.id)

        assert projection.message_id is not None
        info_msg = await self.fetch_message(projection.message_id)
        await info_msg.edit(embed=embed, view=view)

        assert isinstance(ctx.channel, Thread)
        async for discord_event in self.get_projo_events(ctx.channel):
            await discord_event.delete()

        await ctx.reply(
            f"Upcoming events cleared. {self.bot.get_emoji_str('FubukiGO')}",
            embed=embed)

    @app_commands.command()
    @legacy_command()
    async def history(self, ctx: LegacyCommandContext):
        """Projections history"""
        await ctx.defer()

        resp = await get_nanapi().projection.projection_get_projections(
            status=ProjectionStatus.COMPLETED.value)
        if not success(resp):
            raise RuntimeError(resp.result)
        projos = resp.result

        content: list[str] = []
        last_events: MutableSequence[datetime | None] = []
        for projo in projos:
            events = projo.events
            if events:
                last_events.append(events[-1].date)
                date = f"`[{events[-1].date}]` "
            else:
                last_events.append(None)
                date = ''

            subcontent = [f"**{projo.name}**"]
            all_medias = projo.medias + projo.external_medias
            for media in sorted(all_medias,
                                key=lambda m: m.added_alias if m.added_alias is not None else 0):
                if isinstance(media, ProjoSelectResultMedias):
                    subcontent.append(
                        f"​　　[{media.title_user_preferred}](https://anilist.co/anime/{media.id_al})"
                    )
                else:
                    subcontent.append(f"​　　{media.title}")

            content.append(date + '\n'.join(sorted(subcontent, key=str.casefold)))

        # First sort the ones with event date
        content1, _ = zip(
            *sorted((cast(tuple[str, datetime], cpl) for cpl in zip(content, last_events)
                     if cpl[1] is not None),
                    key=lambda cpl: cpl[1],
                    reverse=True))

        # Then the others by event name
        content2, _, _ = zip(*sorted(
            filter(lambda cpl: not cpl[2], zip(content, projos, last_events)),
            key=lambda cpl: cpl[1].name.casefold()))

        content_iter: Iterable[str] = content1 + content2  # type: ignore

        await AutoNavigatorView.create(self.bot,
                                       ctx.reply,
                                       title="Watched anime",
                                       description='\n'.join(content_iter),
                                       color=0x9966cc)

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
                print("message not found:", message_id)
                raise
        return self.message_cache[message_id]

    @Cog.listener()
    async def on_thread_update(self, before: discord.Thread,
                               after: discord.Thread):
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
            embed, view = await get_projo_embed_view(self.bot, projo.id)
            assert projo.message_id is not None
            message = await self.fetch_message(projo.message_id)
            await message.edit(embed=embed, view=view)

    @Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember):
        user = self.bot.get_user(member.id)
        assert user is not None
        if user.bot:
            return

        projo = await get_active_projo(member.thread_id)
        if projo is not None:
            embed, view = await get_projo_embed_view(self.bot, projo.id)
            assert projo.message_id
            message = await self.fetch_message(projo.message_id)
            await message.edit(embed=embed, view=view)


async def setup(bot: Bot):
    await bot.add_cog(ProjectionCog(bot))
