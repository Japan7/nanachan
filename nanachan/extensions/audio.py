import asyncio
import logging
from collections.abc import Coroutine, MutableSequence
from dataclasses import dataclass
from typing import Any, Callable

import discord
from discord.abc import Messageable
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.ui import Button, button
from yt_dlp import YoutubeDL

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.discord.views import BaseView, ChoiceView
from nanachan.settings import BOT_VOICE_ID, OPUS_LIB_LOCATION, YOUTUBE_DL_CONFIG

log = logging.getLogger(__name__)

MUTE_EMOJI = '\N{SPEAKER WITH CANCELLATION STROKE}'
DECREASE_EMOJI = '\N{SPEAKER WITH ONE SOUND WAVE}'
INCREASE_EMOJI = '\N{SPEAKER WITH THREE SOUND WAVES}'


class AudioControlsView(BaseView):
    def __init__(self, bot: Bot, cog: 'Audio', timeout: float | None = None):
        super().__init__(bot, timeout=timeout)
        self.cog = cog

    @button(emoji=MUTE_EMOJI, style=ButtonStyle.red)
    async def mute(self, interaction: discord.Interaction, _: Button[BaseView]):
        await interaction.response.defer()
        self.cog.muted = not self.cog.muted
        await self._manage_volume()

    @button(emoji=DECREASE_EMOJI, style=ButtonStyle.grey)
    async def decrease(self, interaction: discord.Interaction, _: Button[BaseView]):
        await interaction.response.defer()
        self.cog.volume = max(0.0, self.cog.volume - 0.1)
        await self._manage_volume()

    @button(emoji=INCREASE_EMOJI, style=ButtonStyle.grey)
    async def increase(self, interaction: discord.Interaction, _: Button[BaseView]):
        await interaction.response.defer()
        self.cog.volume = min(1.0, self.cog.volume + 0.1)
        await self._manage_volume()

    async def _manage_volume(self):
        if self.cog.audio_source is not None:
            self.cog.audio_source.volume = 0 if self.cog.muted else self.cog.volume
        await self.cog.refresh_control_message()


class YTVideo:
    def __init__(self, data):
        self.title = data['title']
        self.url = data['url']
        self.display_url = f'https://youtu.be/{data["id"]}'

    def __str__(self):
        return self.title


@dataclass
class TrackInfo:
    title: str
    display_url: str | None


@dataclass(slots=True)
class PlaylistEntry[T]:
    item: T
    callback: Callable[[T], Coroutine[Any, Any, None]]
    name: str

    async def __call__(self):
        return await self.callback(self.item)


@discord.app_commands.guild_only()
class Audio(NanaGroupCog, group_name='audio'):
    """Make {bot_name} sing and talk to you while you play with your friends"""

    emoji = '\N{SPEAKER}'

    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot
        self.connection: discord.VoiceClient | None = None
        self.audio_source: discord.PCMVolumeTransformer[discord.AudioSource] | None = None
        self.track_info: TrackInfo | None = None
        self.control_message: discord.Message | None = None
        self.volume = 0.5
        self.muted = False
        self.playlist: MutableSequence[PlaylistEntry[Any]] = []

    @discord.app_commands.command(description='Stop audio playback if any')
    async def stop(self, interaction: discord.Interaction[Bot]):
        await interaction.response.defer()
        await self._disconnect()
        await interaction.followup.send(':ok_hand:')

    @discord.app_commands.command(name='play', description='Play music from Youtube')
    @legacy_command()
    async def ytdl_play(self, ctx: LegacyCommandContext, query_or_url: str):
        async def play_yt_video(video: YTVideo):
            audio_source = discord.FFmpegPCMAudio(
                video.url,
                options='-vn',
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            )
            track_info = TrackInfo(video.title, video.display_url)
            await self.play(ctx, audio_source, track_info=track_info)

        async def add_to_playlist(video: YTVideo):
            await self.add_to_playlist(PlaylistEntry(video, play_yt_video, video.title))

        async with ctx.typing():
            videos = await asyncio.to_thread(self._find_yt_video, query_or_url)
            if len(videos) == 0:
                await ctx.reply('No result found')
                return
            elif len(videos) == 1:
                await add_to_playlist(videos[0])
            else:
                view = ChoiceView(self.bot, videos, add_to_playlist)
                await ctx.reply('**What do you want to listen to?**', view=view)

    @discord.app_commands.command(description='Play next item in playlist')
    async def skip(self, interaction: discord.Interaction[Bot]):
        await interaction.response.defer()
        if self.connection is not None and self.connection.is_playing():
            self.connection.stop()
            # self._play_next() is called by the connection callback (_end_sync_callback)
        await interaction.followup.send('Skipped song.')

    async def play(
        self,
        ctx: commands.Context[Bot],
        audio_source: discord.AudioSource,
        track_info: TrackInfo | None = None,
        volume: float | None = None,
        show_control: bool = True,
    ):
        if self.audio_source:
            await ctx.reply('I am already playing!')
            return

        if not volume:
            volume = self.volume

        if isinstance(audio_source, discord.PCMVolumeTransformer):
            audio_source.volume = volume
        else:
            audio_source = discord.PCMVolumeTransformer(audio_source, volume)

        self.track_info = track_info

        if not self.connection:
            await self._connect(ctx, show_control)

        self.audio_source = audio_source
        await self.refresh_control_message()
        assert self.connection is not None
        self.connection.play(audio_source, after=self._end_sync_callback)

    async def add_to_playlist(self, playlist_entry: PlaylistEntry[Any]):
        if self.connection:
            self.playlist.append(playlist_entry)
            await self.refresh_control_message()
            assert self.control_message is not None
            await self.control_message.channel.send(':ok_hand:')
        else:
            await playlist_entry()

    async def _connect(self, ctx: commands.Context[Bot], show_control: bool):
        if self.connection:
            return

        if (
            isinstance(ctx.author, discord.Member)
            and ctx.author.voice is not None
            and ctx.author.voice.channel is not None
        ):
            room = ctx.author.voice.channel
        else:
            room = self.bot.get_voice_channel(BOT_VOICE_ID)
            assert room is not None

        self.connection = await room.connect()

        if show_control:
            await self._send_control_message(ctx)

    async def _play_next(self):
        if not self.connection:
            return

        self.audio_source = None

        if self.playlist:
            playlist_entry = self.playlist.pop(0)
            if self.control_message:
                control_message = self.control_message  # prevents race condition
                channel = control_message.channel
                self.control_message = None
                await control_message.delete()
                await self._send_control_message(channel)
            await playlist_entry()
        else:
            await self._disconnect()

    async def _disconnect(self):
        if not self.connection:
            return

        connection = self.connection  # prevents race condition
        self.connection = None
        self.audio_source = None
        await connection.disconnect(force=False)

        if self.control_message is not None:
            control_message = self.control_message  # prevents race condition
            self.control_message = None
            await control_message.delete()

    def _end_sync_callback(self, error=None):
        if error:
            log.error(error)

        async def callback():
            await asyncio.sleep(3)
            await self._play_next()

        asyncio.create_task(callback())

    async def _send_control_message(self, ctx: Messageable):
        embed = self._build_control_message()
        view = AudioControlsView(self.bot, self)
        self.control_message = await ctx.send(embed=embed, view=view)

    def _build_control_message(self):
        volume = f'{int(100 * self.volume)}%'
        if self.muted:
            volume += ' (Muted)'

        if self.audio_source is not None and self.track_info is not None:
            music = self.track_info.title
            url = self.track_info.display_url
            if len(self.playlist) > 0:
                next_item = f'> {self.playlist[0].name}'
            else:
                next_item = 'Nothing next'
        else:
            music = '*No music*'
            url = None
            next_item = 'Nothing next'

        embed = Embed(description=f'Volume: {volume}')
        assert self.bot.user is not None
        embed.set_author(name=music, url=url, icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=next_item)

        return embed

    async def refresh_control_message(self):
        if self.control_message is None:
            return
        embed = self._build_control_message()
        await self.control_message.edit(embed=embed)

    @staticmethod
    def _find_yt_video(search_tags: str):
        search_tags = search_tags.lstrip('<').rstrip('>')
        ytdl = YoutubeDL(YOUTUBE_DL_CONFIG)
        data = ytdl.extract_info(search_tags, download=False)

        if data is not None and 'entries' in data:
            videos = [YTVideo(e) for e in data['entries']]
        else:
            videos = [YTVideo(data)]

        return videos


async def setup(bot: Bot):
    if OPUS_LIB_LOCATION is not None and not discord.opus.is_loaded():
        discord.opus.load_opus(OPUS_LIB_LOCATION)
    if discord.opus.is_loaded():
        await bot.add_cog(Audio(bot))
    else:
        log.info('failed to load libopus')
