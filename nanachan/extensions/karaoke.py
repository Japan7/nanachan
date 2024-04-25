import asyncio
import bisect
import os
import re
from asyncio import CancelledError
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
from operator import attrgetter, itemgetter
from typing import Any, Optional, Tuple, cast
from urllib.parse import quote_plus, urlparse

import aiofiles
import aiofiles.os
import aiojobs
from discord import FFmpegPCMAudio, File, app_commands
from discord.abc import Messageable
from discord.ext.commands import BadArgument, CommandError, group
from matplotlib import axes, dates, pyplot, ticker
from toolz.curried import compose, first, get, map

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.helpers import Embed
from nanachan.discord.views import ChoiceView, CompositeNavigatorView, ConfirmationView
from nanachan.extensions.audio import Audio, PlaylistEntry, TrackInfo
from nanachan.settings import (
    IGNORED_TIMERS,
    JAPAN7_AUTH,
    KARA_BASE,
    MUGEN_IMPORT_API,
    RequiresKaraoke,
)
from nanachan.utils.misc import get_session, list_display

MUGEN_DOMAIN = "kara.moe"



class MugenImportError(Exception):

    def __init__(self, detail):
        if isinstance(detail, str):
            super().__init__(detail)
        else:
            msg = '\n'.join(f"{d['msg']}" for d in detail)
            super().__init__(msg)


@dataclass
class KaraSong:
    name: str
    path: str
    lyrics: list[str]


def get_result_embed(base: str, result) -> dict[str, Any]:
    domain = MUGEN_DOMAIN
    title, *_ = result['subfile'].rpartition('.')
    url = f"https://{domain}/base/kara/oke/{result['kid']}"

    embed = Embed(title=title, url=url)

    get_names = compose(list, map(get('name')))
    shows = get_names(result['series'])
    singers = get_names(result['singers'])
    songwriters = get_names(result['songwriters'])
    timers = get_names(result['authors'])

    def plural(l, singular="", plural="s"):
        return singular if len(l) == 1 else plural

    if shows:
        embed.add_field(name=f"Show{plural(shows)}",
                        value="\n".join(shows),
                        inline=False)

    if songwriters:
        embed.add_field(name=f"Songwriter{plural(songwriters)}",
                        value="\n".join(songwriters),
                        inline=False)

    if singers:
        embed.add_field(name=f"Singer{plural(singers)}",
                        value="\n".join(singers),
                        inline=False)

    if timers:
        embed.add_field(name=f"Timer{plural(timers)}",
                        value="\n".join(timers),
                        inline=False)

    return {'embed': embed}


class MugenResults(CompositeNavigatorView):

    def __init__(self, bot, pages):
        self.confirmation_view = ConfirmationView(bot)
        super().__init__(bot, self.confirmation_view, pages=pages)
        self.choice = self.bot.loop.create_future()

    @property
    def confirmation(self):
        return self.confirmation_view.confirmation

    @classmethod
    async def from_results(cls, bot, base, results, messageable: Messageable):
        pages = [get_result_embed(base, r) for r in results['content']]
        _, view = await cls.create(bot, messageable.send, pages=pages)
        if await view.confirmation:
            return results['content'][view.displayed_page]


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


@RequiresKaraoke
class Karaoke(Cog):
    emoji = '🎤'

    @group(invoke_without_command=True, recursive_help=True,
           help='Play a karaoke or display information about karaoke base')
    async def kara(self, ctx):
        subcommand = ctx.subcommand_passed
        if subcommand is not None:
            raise BadArgument(f'Invalid kara command `{subcommand}`')
        else:
            raise BadArgument('Subcommand needed')

    @kara.command(help='Play a karaoke (with lyrics!)')
    async def play(self, ctx, *, search_tags: str):
        audio = Audio.get_cog(self.bot)
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
                sorted(await self._find_karaokes(regex=search_tags),
                       key=attrgetter('name')))
            if not karaokes:
                await ctx.send(f'Cannot find karaoke with tags "{search_tags}"')
            elif len(karaokes) == 1:
                await add_to_playlist(karaokes[0])
            else:
                view = ChoiceView(self.bot, karaokes, add_to_playlist)
                await ctx.reply('**Which kara do you want to sing?**', view=view)

    @kara.command(help='Display the karaoke leaderboard')
    async def board(self, ctx):
        async with ctx.typing():
            tmp = await ctx.send('Calculating ...')
            page1, *pages = await self._get_leaderboard()
            await tmp.edit(content=page1)
            for page in pages:
                await ctx.send(page)

    @kara.command(help='Display the evolution of someone’s timing across time\n'
                       '[begin] & [end] should be `YYYY`, `YYYY-MM` or `YYYY-MM-DD`')
    async def graph(self, ctx, username: str, begin: Date | None = None, end: Date | None = None):
        if begin is not None and begin >= (end or date.today()):
            await ctx.send('The begin date should be lower than the end date')
            return

        async with ctx.typing():
            await self._send_karagraph(ctx, username, begin, end)

    timing_reg = re.compile(
        r'^(?:Original Timing|Script Updated By): ([^,\n]*)(?:,.*)?$', re.M)

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
                errors.append(
                    re.sub('/', ' / ', re.sub(f'^{path}/', '', file)))

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
                rows.append(
                    f'{" " * len(str(index))} {space}{timer} ({score})')
            else:
                rows.append(f'{index}:{space}{timer} ({score})')
            old_score = score

        if errors:
            rows.append('')
            rows.append('The following files do not have any timer:')
            for error in errors:
                rows.append(f'- {error}')

        return list_display('Japan7 Ultimate Karaoke Timing Leaderboard (J7UKTL)', rows)

    async def _send_karagraph(self, ctx, username: str,
                              begin: date | None = None, end: date | None = None):
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

        ax.yaxis.set_major_locator(
            ticker.MaxNLocator(integer=True, min_n_ticks=1))

        pyplot.setp(ax.xaxis.get_minorticklabels(), rotation=270)
        ax.autoscale_view()

        ax.grid(True, which='both', linestyle=':')

        file = BytesIO()
        filename = f"{username}_karastats.png"
        pyplot.savefig(file, transparent=True,
                       bbox_inches='tight', format="png")
        file.seek(0)

        await ctx.send(f'Stats of {username}:',
                       file=File(file, filename=filename))

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
            file_name_reg = re.compile(
                rf'(?i:{re.escape(kara_name)})\.(?!ass|ssa)[^.]*$')
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


async def get_categories_embed():
    async with get_session().get(f"{MUGEN_IMPORT_API}/categories", auth=JAPAN7_AUTH) as resp:
        categories = await resp.json()
        desc = "\n".join(f"**{cat}**" for cat in categories)
        return Embed(title="Categories", description=desc)


@app_commands.guild_only()
class Mugen(NanaGroupCog, group_name="mugen"):

    async def get_info(self,
                       ctx,
                       kdata,
                       category: Optional[str] = None,
                       name: Optional[str] = None) -> tuple[str, str]:

        def check(message):
            return ctx.author == message.author and ctx.channel == message.channel

        while category is None:
            embed = await get_categories_embed()
            cancel_view = CancellableMessage(ctx.bot, ctx.author)
            cancel_msg = await ctx.send("What is the category of this song?",
                                        embed=embed, view=cancel_view)

            done, _ = await asyncio.wait([
                asyncio.create_task(
                    ctx.bot.wait_for('user_message', check=check)),
                cancel_view.confirmation
            ], return_when=asyncio.FIRST_COMPLETED)
            await cancel_msg.edit(content=cancel_msg.content, view=None)
            if cancel_view.confirmation.done():
                raise CancelledError()

            ctx = await first(done)
            category = ctx.message.content

            async with get_session().get(
                    f"{MUGEN_IMPORT_API}/category/{category}",
                    auth=JAPAN7_AUTH) as resp:
                if resp.status != 200:
                    await ctx.send(f"{category} is not a valid category")
                    category = None

        while name is None:
            cancel_view = CancellableMessage(ctx.bot, ctx.author)
            cancel_msg = await ctx.send("What should this karaoke be called?", view=cancel_view)
            done, _ = await asyncio.wait([
                asyncio.create_task(
                    ctx.bot.wait_for('user_message', check=check)),
                cancel_view.confirmation
            ], return_when=asyncio.FIRST_COMPLETED)
            await cancel_msg.edit(content=cancel_msg.content, view=None)
            if cancel_view.confirmation.done():
                raise CancelledError()

            ctx = await first(done)
            name = ctx.message.content

        return category, name

    async def import_karaoke(self, base: str, kid: str, category: str, name: str):
        json_data = {
            'base': base,
            'kid': kid,
            'category': category,
            'name': name
        }

        url = f"{MUGEN_IMPORT_API}/import"
        async with get_session().post(url, json=json_data, auth=JAPAN7_AUTH) as resp:
            data = await resp.json()
            if 'detail' in data:
                raise MugenImportError(data['detail'])
            else:
                return data

    @staticmethod
    def parse_mugen_url(url: str) -> Tuple[str, str]:
        parsed = urlparse(url)
        base = "moe"

        *_, kid = parsed.path.rpartition('/')
        return base, kid

    async def _import_kara(self, ctx, base, kid, category, name):
        async with ctx.channel.typing():
            data = await self.import_karaoke(base, kid, category, name)
            await ctx.send(f"{data['result']} {ctx.bot.get_emoji_str('FubukiGO')}")

    karaoke_categories = [
        app_commands.Choice(name="Anime", value="Anime"),
        app_commands.Choice(name="Autre", value="Autre"),
        app_commands.Choice(name="CJKmusic", value="CJKmusic"),
        app_commands.Choice(name="Dessin animé", value="Dessin animé"),
        app_commands.Choice(name="Jeu", value="Jeu"),
        app_commands.Choice(name="Live action", value="Live action"),
        app_commands.Choice(name="Wmusic", value="Wmusic"),
    ]

    @app_commands.command(name='import')
    @app_commands.describe(url_or_id="kara.moe url or ID of the karaoke to import.",
                           category="Category of the karaoke.",
                           name="Name of the karaoke.")
    @app_commands.choices(category=karaoke_categories)
    @legacy_command()
    async def import_(self,
                      ctx: LegacyCommandContext,
                      url_or_id: str,
                      category: str,
                      name: str | None = None):
        """Import a karaoke from Karaoke Mugen"""
        async with ctx.channel.typing():
            base, kid = self.parse_mugen_url(url_or_id)

            if category is None or name is None:
                url_or_id = f"https://{MUGEN_DOMAIN}/api/karas/{kid}"
                async with get_session().get(url_or_id) as resp:
                    kdata = await resp.json()
                    await ctx.send(**get_result_embed(base, kdata))

                try:
                    category, name = await self.get_info(ctx, kdata, category, name)
                except CancelledError:
                    return

            try:
                await self._import_kara(ctx, base, kid, category, name)
            except MugenImportError as e:
                raise CommandError(str(e))

    async def is_imported(self, kid: str):
        url = f"{MUGEN_IMPORT_API}/kara/{kid}"
        async with get_session().get(url, auth=JAPAN7_AUTH) as resp:
            return resp.status == 200

    @app_commands.command()
    @legacy_command()
    async def search(self, ctx: LegacyCommandContext, query: str):
        """Look for a karaoke to import"""
        base = "moe"
        domain = MUGEN_DOMAIN

        url = f"https://{domain}/api/karas/search"
        params = {
            'filter': quote_plus(query),
            'size': 10,
            'collections': ",".join([
                "dbcf2c22-524d-4708-99bb-601703633927",
                "c7db86a0-ff64-4044-9be4-66dd1ef1d1c1",
                "2fa2fe3f-bb56-45ee-aa38-eae60e76f224",
                "efe171c0-e8a1-4d03-98c0-60ecf741ad52",
            ])
        }
        async with get_session().get(url, params=params) as search:
            results = await search.json()
            if not results.get('content'):
                raise CommandError("No results found")

            choice = await MugenResults.from_results(ctx.bot, base, results, ctx)
            if choice is None:
                await ctx.send("Aborted")
                return

            if await self.is_imported(choice['kid']):
                raise CommandError("This karaoke has been already imported.")
            else:
                category = None
                while True:
                    try:
                        category, name = await self.get_info(ctx, choice, category=category)
                        await self._import_kara(ctx, base, choice['kid'], category, name)
                        break
                    except CancelledError:
                        return
                    except MugenImportError as e:
                        await ctx.send(str(e))


async def setup(bot: Bot):
    await bot.add_cog(Karaoke(bot))
    await bot.add_cog(Mugen())
