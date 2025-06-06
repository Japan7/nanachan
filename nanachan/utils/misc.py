import asyncio
import io
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from functools import cache, lru_cache, singledispatch, update_wrapper
from typing import Any, AsyncIterable, Coroutine, NotRequired, Optional, Type, TypedDict

import aiohttp
import backoff
import pydantic
import tldr
from discord.ext.commands import Paginator
from rich import traceback
from rich.console import Console
from yarl import URL

from nanachan.settings import PRODUCER_TOKEN, PRODUCER_UPLOAD_ENDPOINT, SAUCENAO_API_KEY

__all__ = (
    'framed_header',
    'list_display',
    'run_coro',
    'fake_method',
    'dummy',
    'async_dummy',
    'get_session',
    'to_producer',
    'ignore',
    'get_console',
    'get_traceback',
    'get_traceback_exc',
    'get_traceback_str',
    'print_exc',
    'ic',
    'tldr_get_page',
    'async_all',
    'EXECUTOR',
)


EXECUTOR = ProcessPoolExecutor()


conn_backoff = backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError, aiohttp.ContentTypeError),
    max_time=600,
)


def give_up(exception):
    return 400 <= exception.status < 500


response_backoff = backoff.on_exception(
    backoff.expo, aiohttp.ClientResponseError, max_time=600, giveup=give_up
)

timeout_backoff = backoff.on_exception(
    backoff.expo, aiohttp.ServerTimeoutError, max_time=300, max_tries=5
)


default_backoff = timeout_backoff(conn_backoff(response_backoff))


def framed_header(header):
    return f'┌─{"─" * len(header)}─┐\n│ {header} │\n└─{"─" * len(header)}─┘'


def list_display(header, elems):
    p = Paginator()
    p.add_line(framed_header(header))
    for elem in elems:
        p.add_line(elem)
    return p.pages


async def run_coro(coro: Coroutine[Any, Any, Any] | Any):
    if asyncio.iscoroutine(coro):
        return await coro
    else:
        return coro


class FakeMethod:
    def __init__(self, instance, func):
        self.instance = instance
        self.func = func
        update_wrapper(self, func)

    def __getattr__(self, key):
        return getattr(self.func, key)

    def __call__(self, *args, **kwargs):
        return self.func(self.instance, *args, **kwargs)


def fake_method(instance, func):
    if func is not None and not hasattr(func, '__self__'):
        return FakeMethod(instance, func)

    return func


def dummy(*args, **kwargs):
    pass


async def async_dummy(*args, **kwargs):
    pass


def json_dumps(d: Any) -> str:
    return json.dumps(d, separators=(',', ':'))


@cache
def get_session() -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_connect=5)
    return aiohttp.ClientSession(timeout=timeout)


class ProducerResponse(TypedDict):
    url: str


@singledispatch
async def to_producer(file: str | URL | io.IOBase) -> ProducerResponse:
    raise RuntimeError('shouldn’t be here')


@to_producer.register
@default_backoff
async def _(file: str | URL) -> ProducerResponse:
    url = URL(file) if isinstance(file, str) else file

    async with get_session().get(url) as resp:
        filename = url.name
        headers: dict[str, str] = {
            'Authorization': PRODUCER_TOKEN,
            'Expires': '0',
            'Filename': filename,
        }

        async with get_session().post(
            PRODUCER_UPLOAD_ENDPOINT, headers=headers, data=resp.content
        ) as req:
            return await req.json()


async def chunk_iter(file: io.IOBase):
    while chunk := file.read(64 * 1024):
        yield chunk


@to_producer.register
@default_backoff
async def _(file: io.IOBase, filename: str) -> ProducerResponse:
    headers: dict[str, str] = {
        'Authorization': PRODUCER_TOKEN,
        'Expires': '0',
        'Filename': filename,
    }

    async with get_session().post(
        PRODUCER_UPLOAD_ENDPOINT, headers=headers, data=chunk_iter(file)
    ) as req:
        return await req.json()


async def ignore(exception: Type[Exception], coro: Coroutine[Any, Any, Any]):
    with suppress(exception):
        await run_coro(coro)


@cache
def get_console() -> Console:
    return Console(width=78)


TRACEBACK_KWARGS: dict[str, Any] = {'word_wrap': True}


def get_traceback(e: Optional[BaseException] = None) -> traceback.Traceback:
    if e is None:
        return get_traceback_exc()

    return traceback.Traceback.from_exception(type(e), e, e.__traceback__, **TRACEBACK_KWARGS)


def get_traceback_str(trace: traceback.Traceback) -> str:
    console = get_console()
    return ''.join(s.text for s in console.render(trace))


def get_traceback_exc() -> traceback.Traceback:
    exc_type, exc, trace = sys.exc_info()
    assert exc_type is not None
    assert exc is not None
    return traceback.Traceback.from_exception(exc_type, exc, trace, **TRACEBACK_KWARGS)


def print_exc(e: Optional[BaseException] = None):
    trace = get_traceback(e)
    get_console().print(trace)


def ic(*args, **kwargs):
    get_console().log(*args, **kwargs)

    if not args:
        return None
    if len(args) == 1:
        return args[0]

    return args


tldr_arg = re.compile(r'{{(.+?)}}')


async def tldr_get_page(command: str):
    platforms = tldr.get_platform_list()

    for platform in platforms:
        url = tldr.get_page_url(command, platform, None, None)  # type: ignore
        async with get_session().get(url) as resp:
            if resp.status == 404:
                continue

            resp.raise_for_status()

            page = await resp.text()
            page = tldr_arg.sub(lambda match: match.group(1), page)
            return page.replace(f'# {command}', '').strip()


def truncate_at(length: int, string: str) -> str:
    string = string.strip()
    if len(string) <= length:
        return string
    else:
        space_index = max(i for i, c in enumerate(string) if c == ' ' and i < length)
        return string[:space_index] + '…'


@lru_cache(maxsize=1024)
def autocomplete_truncate(name: str) -> str:
    while len(name) > 100:
        name, *_ = name.rpartition(' ')

    return name


async def async_all(it: AsyncIterable[bool]) -> bool:
    async for v in it:
        if not v:
            return False

    return True


async def async_any(it: AsyncIterable[bool]) -> bool:
    async for v in it:
        if v:
            return True

    return False


def not_none[T](x: T | None) -> T:
    assert x is not None
    return x


SAUCENAO_API_URL = 'https://saucenao.com/search.php'


class Sauce(pydantic.BaseModel):
    artists: list[str]
    urls: list[str]
    title: str = ''
    part: str = ''
    mal_id: int | None = None
    similarity: float
    index_id: int
    index_name: str
    thumbnail: str

    def __str__(self) -> str:
        parts = [f'[**{self.similarity:.2f}%** ⋅ {self.index_name}]']
        if self.artists:
            parts.append(', '.join(f'**{a}**' for a in self.artists))

        if self.title:
            parts.append(f'*{self.title}*')

        if self.part:
            parts.append(f'*{self.part}*')

        if self.urls:
            parts.append('\n'.join(self.urls))

        return '\n'.join(parts)


class SauceData(TypedDict):
    artist: NotRequired[str]
    author: NotRequired[str]
    creator: NotRequired[list[str] | str]
    member_id: NotRequired[int]
    member_name: NotRequired[str]
    pixiv_id: NotRequired[int]
    danbooru_id: NotRequired[int]
    ext_urls: list[str]
    mal_id: NotRequired[int]
    md_id: NotRequired[str]
    # mu_id: NotRequired[int]
    part: NotRequired[str]
    source: NotRequired[str]


class SauceHeader(pydantic.BaseModel):
    similarity: float
    index_id: int
    index_name: str
    dupes: int
    hidden: int
    thumbnail: str


class SauceResult(pydantic.BaseModel):
    data: SauceData
    header: SauceHeader

    def to_sauce(self) -> Sauce:
        artists = []
        if artist := self.data.get('artist'):
            artists.append(artist)
        if creator := self.data.get('creator'):
            if isinstance(creator, list):
                artists.extend(creator)
            else:
                artists.append(creator)
        if author := self.data.get('author'):
            if isinstance(creator, list):
                artists.extend(author)
            else:
                artists.append(author)
        if member_name := self.data.get('member_name'):
            artists.append(member_name)

        urls = self.data['ext_urls']

        title = ''
        part = ''
        mal_id = None

        match self.header.index_id:
            case 5:  # Pixiv
                pass
            case 21:  # Anime
                assert 'source' in self.data
                assert 'part' in self.data
                title = self.data['source']
                part = f'Episode {self.data["part"]}'
                mal_id = self.data.get('mal_id')
            case 37:  # Mangadex
                assert 'source' in self.data
                assert 'part' in self.data
                title = self.data['source']
                part = self.data['part']
                mal_id = self.data.get('mal_id')
            case _:  # default
                if source := self.data.get('source'):
                    if source.startswith('https://'):
                        urls.insert(0, source)
                    else:
                        title = source
                part = self.data.get('part', '')

        return Sauce(
            artists=artists,
            urls=urls,
            title=title,
            part=part,
            mal_id=mal_id,
            similarity=self.header.similarity,
            index_id=self.header.index_id,
            index_name=self.header.index_name,
            thumbnail=self.header.thumbnail,
        )


class SauceLookup(pydantic.BaseModel):
    results: list[SauceResult]


async def saucenao_lookup(url: str, priority: list[int] | None = None) -> list[Sauce]:
    assert SAUCENAO_API_KEY is not None
    params: dict[str, str | int | float | list[int]] = {
        'url': url,
        'api_key': SAUCENAO_API_KEY,
        'output_type': 2,
        'test_mode': 0,
        'strict_mode': '1',
        'priority': [] if priority is None else priority,
        'priority_tolerance': 10,
    }

    session = get_session()
    res: list[Sauce] = []
    async with session.get(SAUCENAO_API_URL, params=params) as resp:
        data = await resp.json()
        try:
            sauces = SauceLookup.model_validate(data)
            for s in sauces.results:
                res.append(s.to_sauce())
        except Exception as e:
            raise RuntimeError(f'failed to parse {data}') from e

    return res
