import asyncio
import bisect
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
from operator import attrgetter, itemgetter
from typing import cast

import aiofiles
import aiofiles.os
import aiojobs
from discord import FFmpegPCMAudio, File, app_commands
from discord.ext.commands import BadArgument
from matplotlib import axes, dates, pyplot, ticker

from nanachan.discord.application_commands import legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.views import ChoiceView, ConfirmationView
from nanachan.extensions.audio import Audio, PlaylistEntry, TrackInfo
from nanachan.settings import (
    IGNORED_TIMERS,
    KARA_BASE,
    RequiresKaraoke,
)
from nanachan.utils.misc import list_display

MUGEN_DOMAIN = 'kara.moe'


@dataclass
class KaraSong:
    name: str
    path: str
    lyrics: list[str]


class CancellableMessage(ConfirmationView):
    def __init__(self, bot, user):
        super().__init__(bot, no_user=user)
        self.remove_item(self.accept_bt)


class Date(date):
    fmts = ['%Y-%m-%d', '%Y-%m', '%Y']

    @classmethod
    async def convert(cls, ctx, argument) -> date:
        for fmt in cls.fmts:
            try:
                return datetime.strptime(argument, fmt).date()
            except ValueError:
                pass
        raise BadArgument(
            'Cannot successfully parse date (should be `YYYY`, `YYYY-MM` or `YYYY-MM-DD`)'
        )


class Karaoke(NanaGroupCog, group_name='kara', required_settings=RequiresKaraoke):
    emoji = '🎤'

    @app_commands.command(description='Play a karaoke (with lyrics!)')
    @legacy_command()
    async def play(self, ctx, *, search_tags: str):
        audio = Audio.get_cog(ctx.bot)
        assert audio is not None

        async def send_karaoke(kara: KaraSong):
            async with ctx.typing():
                audio_source = FFmpegPCMAudio(kara.path)
                track_info = TrackInfo(kara.name, None)
                await audio.play(ctx, audio_source, track_info=track_info)
                for page in list_display(kara.name, kara.lyrics):
                    await ctx.send(page)

        async def add_to_playlist(kara: KaraSong):
            await audio.add_to_playlist(PlaylistEntry(kara, send_karaoke, kara.name))

        async with ctx.typing():
            karaokes = list(
                sorted(await self._find_karaokes(regex=search_tags), key=attrgetter('name'))
            )
            if not karaokes:
                await ctx.send(f'Cannot find karaoke with tags "{search_tags}"')
            elif len(karaokes) == 1:
                await add_to_playlist(karaokes[0])
            else:
                view = ChoiceView(ctx.bot, karaokes, add_to_playlist)
                await ctx.reply('**Which kara do you want to sing?**', view=view)

    @app_commands.command(description='Display the karaoke leaderboard')
    @legacy_command()
    async def board(self, ctx):
        async with ctx.typing():
            tmp = await ctx.send('Calculating ...')
            page1, *pages = await self._get_leaderboard()
            await tmp.edit(content=page1)
            for page in pages:
                await ctx.send(page)

    @app_commands.command(description='Display the evolution of someone’s timing across time')
    @app_commands.describe(begin_str='YYYY-MM-DD')
    @app_commands.rename(begin_str='begin')
    @legacy_command()
    async def graph(
        self, ctx, username: str, begin_str: str | None = None, end_str: str | None = None
    ):
        begin: datetime | None = None
        end: datetime | None = None

        if begin_str is not None:
            try:
                begin = datetime.fromisoformat(begin_str)
            except ValueError:
                await ctx.send('begin format should be YYYY-MM-DD')
                return

        if end_str is not None:
            try:
                end = datetime.fromisoformat(end_str)
            except ValueError:
                await ctx.send('end format should be YYYY-MM-DD')
                return

        if begin is not None and begin >= (end or date.today()):
            await ctx.send('The begin date should be lower than the end date')
            return

        async with ctx.typing():
            await self._send_karagraph(ctx, username, begin, end)

    timing_reg = re.compile(r'^(?:Original Timing|Script Updated By): ([^,\n]*)(?:,.*)?$', re.M)

    async def _get_timer(self, file_path: str, fut: asyncio.Future[tuple[str, set[str]]]):
        try:
            async with aiofiles.open(file_path) as file:
                timer_matches = self.timing_reg.findall(await file.read(1024))
                sub_timers = set(timer_matches)

                fut.set_result((file_path, sub_timers))
        except Exception as e:
            fut.set_exception(e)

    async def _get_karas_by_timers(self):
        assert KARA_BASE is not None
        path = KARA_BASE

        file_name_reg = re.compile(r'.*\.(ass|ssa)$')
        file_paths: list[str] = []
        for root, _, file_names in os.walk(path):
            for file_name in file_names:
                if file_name_reg.match(file_name):
                    file_paths.append(os.path.join(root, file_name))

        sched = aiojobs.Scheduler()
        jobs: list[asyncio.Future[tuple[str, set[str]]]] = []

        for file_path in file_paths:
            fut = asyncio.get_running_loop().create_future()
            await sched.spawn(self._get_timer(file_path, fut))
            jobs.append(fut)

        timers: dict[str, list[str]] = defaultdict(list)
        errors: list[str] = []
        for job in jobs:
            file, file_timers = await job

            if len(file_timers) > 0:
                for timer in file_timers:
                    timers[timer].append(file)
            else:
                errors.append(re.sub('/', ' / ', re.sub(f'^{path}/', '', file)))

        return timers, errors

    async def _get_leaderboard(self):
        timers, errors = await self._get_karas_by_timers()

        scores = {}
        for timer, karas in timers.items():
            if timer in IGNORED_TIMERS:
                continue
            scores[timer] = len(karas)
        ranking = sorted(scores.items(), key=itemgetter(1), reverse=True)

        rows = []
        old_score = 0
        for index, (timer, score) in enumerate(ranking, start=1):
            space = ' ' * (4 - len(str(index)))
            if score == old_score:
                rows.append(f'{" " * len(str(index))} {space}{timer} ({score})')
            else:
                rows.append(f'{index}:{space}{timer} ({score})')
            old_score = score

        if errors:
            rows.append('')
            rows.append('The following files do not have any timer:')
            for error in errors:
                rows.append(f'- {error}')

        return list_display('Japan7 Ultimate Karaoke Timing Leaderboard (J7UKTL)', rows)

    async def _send_karagraph(
        self, ctx, username: str, begin: date | None = None, end: date | None = None
    ):
        timers, errors = await self._get_karas_by_timers()

        if username not in timers:
            await ctx.send(f'No user named {username} found :confounded:')
            return

        stats_fut: list[asyncio.Future[os.stat_result]] = []

        async def stat(file: str, fut: asyncio.Future):
            file_stat = await aiofiles.os.stat(file)
            fut.set_result(file_stat)

        sched = aiojobs.Scheduler()
        for kara_file in timers[username]:
            fut = asyncio.get_running_loop().create_future()
            await sched.spawn(stat(kara_file, fut))
            stats_fut.append(fut)

        mtimes = []

        for stat_fut in stats_fut:
            kara_stat = await stat_fut
            bisect.insort(mtimes, date.fromtimestamp(kara_stat.st_mtime))

        score = 0
        first = mtimes[0] - timedelta(weeks=1)
        end = end or date.today()
        karas_over_time = {first: score}
        for mtime in mtimes:
            if mtime > end:
                break
            score += 1
            karas_over_time[mtime] = score
        karas_over_time[end] = score

        if begin and begin > first:
            last = 0
            for mtime, score in karas_over_time.copy().items():
                if mtime < begin:
                    last = score
                    del karas_over_time[mtime]
            if begin not in karas_over_time:
                karas_over_time[begin] = last
        else:
            begin = first

        assert begin
        delta = end - begin
        if delta < timedelta(weeks=5):
            major = dates.MonthLocator()
            major_fmt = dates.DateFormatter('\n%b')
            minor = dates.DayLocator()
            minor_fmt = dates.DateFormatter('%d')
        elif delta < timedelta(weeks=10):
            major = dates.MonthLocator()
            major_fmt = dates.DateFormatter('\n%b')
            minor = dates.DayLocator(bymonthday=range(1, 31, 5))
            minor_fmt = dates.DateFormatter('%d')
        elif delta < timedelta(weeks=104):
            major = dates.YearLocator()
            major_fmt = dates.DateFormatter('\n\n%Y')
            minor = dates.MonthLocator()
            minor_fmt = dates.DateFormatter('%b')
        elif delta < timedelta(weeks=312):
            major = dates.YearLocator()
            major_fmt = dates.DateFormatter('%Y')
            minor = dates.MonthLocator(bymonth=range(1, 13, 3))
            minor_fmt = dates.DateFormatter('')
        else:
            major = dates.YearLocator()
            major_fmt = dates.DateFormatter('%Y')
            minor = None
            minor_fmt = None

        pyplot.style.use('dark_background')
        fig, ax = pyplot.subplots()
        ax = cast(axes.Axes, ax)
        score_date, scores = zip(*sorted(karas_over_time.items()))
        ax.step(score_date, scores, where='post')

        ax.xaxis.set_major_locator(major)
        ax.xaxis.set_major_formatter(major_fmt)
        if minor is not None:
            ax.xaxis.set_minor_locator(minor)
            assert minor_fmt is not None
            ax.xaxis.set_minor_formatter(minor_fmt)

        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, min_n_ticks=1))

        pyplot.setp(ax.xaxis.get_minorticklabels(), rotation=270)
        ax.autoscale_view()

        ax.grid(True, which='both', linestyle=':')

        file = BytesIO()
        filename = f'{username}_karastats.png'
        pyplot.savefig(file, transparent=True, bbox_inches='tight', format='png')
        file.seek(0)

        await ctx.send(f'Stats of {username}:', file=File(file, filename=filename))

    async def _find_karaokes(self, path=None, regex=''):
        if path is None:
            assert KARA_BASE is not None
            path = KARA_BASE

        regex = re.sub(' ', '.*', regex)
        file_name_reg = re.compile(rf'.*(?i:{regex}).*\.(ass|ssa)$')

        file_paths = []
        for root, _, file_names in os.walk(path):
            for file_name in file_names:
                if file_name_reg.match(file_name):
                    file_path = os.path.join(root, file_name)
                    file_paths.append(file_path)

        lyrics_reg = re.compile(r'[^;].*{\\[kK].*}')
        karas_found = []
        for file_path in file_paths:
            lyrics = []
            cache = []
            async with aiofiles.open(file_path) as file:
                async for line in file:
                    if lyrics_reg.match(line):
                        fields = line.split(',')
                        line = ','.join(fields[9:])
                        line = re.sub(r'{[^}]*}', '', line)
                        line_id = (fields[1], fields[2], line.strip())
                        if line_id not in cache:
                            lyrics.append(line.strip())
                            cache.append(line_id)

            kara_name = os.path.splitext(os.path.basename(file_path))[0]
            file_name_reg = re.compile(rf'(?i:{re.escape(kara_name)})\.(?!ass|ssa)[^.]*$')
            file_path = None
            for root, _, file_names in os.walk(path):
                for file_name in file_names:
                    if file_name_reg.match(file_name):
                        file_path = os.path.join(root, file_name)
                        break
                if file_path is not None:
                    break

            assert file_path is not None

            karas_found.append(KaraSong(kara_name, file_path, lyrics))

        return karas_found


async def setup(bot: Bot):
    await bot.add_cog(Karaoke())
