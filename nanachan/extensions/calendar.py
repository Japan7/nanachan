import logging

import aiofiles
import arrow
import discord.utils
import ics
from discord.scheduled_event import ScheduledEvent

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import MultiplexingContext
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import UpsertCalendarBody
from nanachan.settings import ICS_PATH, VERIFIED_ROLE, RequiresCalendar

logger = logging.getLogger(__name__)


@RequiresCalendar
class Calendar_Generator(Cog, name="Calendar"):
    emoji = '📅'

    def __init__(self, bot: Bot):
        self.bot = bot
        self.events: dict[int, ics.Event] = {}

    def generate_ics_event(self, event: ScheduledEvent):
        e = ics.Event()

        guild = event.guild
        assert guild is not None
        if event.channel is not None:
            loc = "#" + event.channel.name
            role = discord.utils.get(guild.roles, name="@everyone")
            if VERIFIED_ROLE is not None and (role := guild.get_role(VERIFIED_ROLE)) is not None:
                perms = event.channel.permissions_for(role)
                if not perms.read_messages:
                    return
        else:
            assert event.location is not None
            loc = event.location

        e.name = event.name
        e.location = loc
        e.begin = arrow.get(event.start_time)

        if event.end_time is not None:
            e.end = arrow.get(event.end_time)
        else:
            e.end = arrow.get(event.start_time).shift(hours=2, minutes=30)

        description = ""
        if event.description is not None:
            description += event.description + "\n"
        description += event.url
        e.description = description
        return e

    def add_or_ignore(self, event: ScheduledEvent):
        if (e := self.generate_ics_event(event)) is not None:
            self.events[event.id] = e

    async def fetch_calendar(self):
        for guild in self.bot.guilds:
            for event in await guild.fetch_scheduled_events():
                self.add_or_ignore(event)

    @Cog.listener()
    async def on_ready(self):
        from .profiles import Profiles

        profiles_cog = Profiles.get_cog(self.bot)
        if profiles_cog is not None:
            profiles_cog.registrars['Calendar'] = self.register

        await self.fetch_calendar()
        await self.update_ics()

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

        resp1 = await get_nanapi().user.user_upsert_calendar(
            interaction.user.id,
            UpsertCalendarBody(discord_username=str(interaction.user), ics=ics),
        )
        if not success(resp1):
            raise RuntimeError(resp1.result)
        await interaction.followup.send(content=self.bot.get_emoji_str('FubukiGO'))

    @Cog.listener()
    async def on_scheduled_event_create(self, event: ScheduledEvent):
        self.add_or_ignore(event)
        await self.update_ics()

    @Cog.listener()
    async def on_scheduled_event_delete(self, event: ScheduledEvent):
        await self.fetch_calendar()
        if event.id in self.events:
            del self.events[event.id]
            await self.update_ics()

    @Cog.listener()
    async def on_scheduled_event_update(self, _: ScheduledEvent, after: ScheduledEvent):
        await self.fetch_calendar()
        if after.id in self.events:
            if (e := self.generate_ics_event(after)) is not None:
                self.events[after.id] = e
            else:  # event turned private or something
                del self.events[after.id]

            await self.update_ics()

    async def update_ics(self):
        calendar = ics.Calendar(events=self.events.values())
        assert ICS_PATH is not None
        async with aiofiles.open(ICS_PATH, 'w') as f:
            await f.writelines(calendar.serialize_iter())

        logger.info(f"updated calendar {ICS_PATH}")


async def setup(bot: Bot):
    await bot.add_cog(Calendar_Generator(bot))
