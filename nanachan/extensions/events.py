
from contextlib import suppress

from discord import EventStatus, Member, VoiceState
from discord.errors import Forbidden

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog


class EventCog(Cog):

    @Cog.listener()
    async def on_voice_state_update(self, member: Member,
                                    before: VoiceState, after: VoiceState):
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
    await bot.add_cog(EventCog(bot))
