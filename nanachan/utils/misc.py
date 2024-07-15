import asyncio
import io
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from functools import cache, lru_cache, singledispatch, update_wrapper
from typing import Any, AsyncIterable, Coroutine, Optional, Type, TypedDict, Union, cast

import aiohttp
import backoff
import orjson
import tldr
from discord.ext.commands import Paginator
from rich import traceback
from rich.console import Console
from yarl import URL

from nanachan.settings import PRODUCER_TOKEN, PRODUCER_UPLOAD_ENDPOINT

__all__ = ('framed_header',
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
           'EXECUTOR')


EXECUTOR = ProcessPoolExecutor()


conn_backoff = backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientConnectorError,
     aiohttp.ClientConnectionError, aiohttp.ContentTypeError),
    max_time=600
)


def give_up(exception):
    return 400 <= exception.status < 500


response_backoff = backoff.on_exception(
    backoff.expo,
    aiohttp.ClientResponseError,
    max_time=600,
    giveup=give_up
)

timeout_backoff = backoff.on_exception(
    backoff.expo,
    aiohttp.ServerTimeoutError,
    max_time=300,
    max_tries=5
)


default_backoff = timeout_backoff(conn_backoff(response_backoff))


def framed_header(header):
    return (f'┌─{"─" * len(header)}─┐\n'
            f'│ {header} │\n'
            f'└─{"─" * len(header)}─┘')


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
        return cast(Any, coro)


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


@cache
def get_session() -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_connect=5)
    # until they fix https://github.com/aio-libs/aiohttp/issues/5975
    json_serialize = lambda d: orjson.dumps(d, option=orjson.OPT_SERIALIZE_NUMPY).decode()
    return aiohttp.ClientSession(timeout=timeout, json_serialize=json_serialize)


class ProducerResponse(TypedDict):
    url: str


@singledispatch
@default_backoff
async def to_producer(file: Union[str, URL]) -> ProducerResponse:
    url = URL(file) if isinstance(file, str) else file

    async with get_session().get(url) as req:
        filename = url.name
        data = aiohttp.FormData()
        data.add_field("file", req.content, filename=filename)
        headers = {
            "Authorization": PRODUCER_TOKEN,
            "Expires": 0,
        }

        async with get_session().post(PRODUCER_UPLOAD_ENDPOINT,
                                      headers=headers, data=data) as req:
            return await req.json()


@to_producer.register
@default_backoff
async def _(file: io.IOBase, filename=None) -> ProducerResponse:
    if filename is not None:
        file.name = filename  # type: ignore

    headers = {
        "Authorization": PRODUCER_TOKEN,
        "Expires": 0,
    }

    async with get_session().post(PRODUCER_UPLOAD_ENDPOINT,
                                  headers=headers, data=dict(file=file)) as req:
        return await req.json()


async def ignore(exception: Type[Exception], coro: Coroutine[Any, Any, Any]):
    with suppress(exception):
        await run_coro(coro)


@cache
def get_console() -> Console:
    return Console(width=78)


TRACEBACK_KWARGS: dict[str, Any] = {
    'word_wrap': True
}


def get_traceback(e: Optional[BaseException] = None) -> traceback.Traceback:
    if e is None:
        return get_traceback_exc()

    return traceback.Traceback.from_exception(type(e), e, e.__traceback__, **TRACEBACK_KWARGS)


def get_traceback_str(trace: traceback.Traceback) -> str:
    console = get_console()
    return "".join(s.text for s in console.render(trace))


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


tldr_arg = re.compile(r"{{(.+?)}}")


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
            return page.replace(f"# {command}", "").strip()


def truncate_at(length: int, string: str) -> str:
    string = string.strip()
    if len(string) <= length:
        return string
    else:
        space_index = max(i for i, c in enumerate(string)
                          if c == ' ' and i < length)
        return string[:space_index] + '…'


@lru_cache(maxsize=1024)
def autocomplete_truncate(name: str) -> str:
    while len(name) > 100:
        name, *_ = name.rpartition(" ")

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
