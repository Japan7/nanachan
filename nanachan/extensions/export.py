import json
from typing import TYPE_CHECKING

import discord
from discord import Thread

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.nanapi.client import get_nanapi
from nanachan.settings import RequiresMessageExport

if TYPE_CHECKING:
    from discord.types.gateway import MessageCreateEvent
    from discord.types.message import Message


class MessageExport(Cog, required_settings=RequiresMessageExport):
    @Cog.listener()
    async def on_raw_message(self, data: 'MessageCreateEvent'):
        await self.upsert_message(data)

    @Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        await self.upsert_message(payload.data)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        await get_nanapi().discord.discord_delete_messages(str(payload.message_id))

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        await get_nanapi().discord.discord_delete_messages(','.join(map(str, payload.message_ids)))

    async def upsert_message(self, data: 'Message'):
        noindex = None
        if str(data['author']['id']) == str(self.bot.bot_id):
            noindex = 'nanachan'
        elif data['author'].get('bot'):
            noindex = 'bot'
        elif await self.is_nana_thread(data):
            noindex = 'nanachan thread'  # AI chat ?
        await get_nanapi().discord.discord_upsert_message(
            str(data['id']), json.dumps(data), noindex=noindex
        )

    async def is_nana_thread(self, data: 'Message'):
        if (thread := data.get('thread')) and str(thread['owner_id']) == str(self.bot.bot_id):
            return True
        channel_id = int(data['channel_id'])
        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        return isinstance(channel, Thread) and channel.owner_id == self.bot.bot_id


async def setup(bot: Bot):
    await bot.add_cog(MessageExport(bot))
