import asyncio
from functools import cache

import aiohttp
import backoff
from aiohttp import ClientResponse

from nanachan.nanapi._client import Error as Error  # noqa: F401
from nanachan.nanapi._client import Success as Success  # noqa: F401
from nanachan.nanapi._client import get_session
from nanachan.nanapi._client import success as success
from nanachan.nanapi.model import Body_client_login
from nanachan.settings import NANAPI_CLIENT_PASSWORD, NANAPI_CLIENT_USERNAME, NANAPI_URL

bearer_token: str | None = None
bearer_ready = asyncio.Event()
load_lock = asyncio.Lock()


def check_invalid(r: ClientResponse):
    return r.status in (502, 520, 522) or (
        'text/plain' in r.headers.get('Content-Type', '') and r.status == 404
    )


# Connection error backoff - retries on network-level errors
conn_exception_backoff = backoff.on_exception(
    backoff.expo,
    (
        aiohttp.ClientConnectorError,
        aiohttp.ClientConnectionError,
        aiohttp.ClientOSError,
        aiohttp.ServerTimeoutError,
    ),
    max_time=600,
)


async def load_bearer_token():
    global bearer_token
    if load_lock.locked():
        return
    async with load_lock:
        bearer_ready.clear()

        session = get_session(NANAPI_URL)
        session_backoff = backoff.on_predicate(backoff.expo, check_invalid)
        # Apply connection error backoff and status code backoff
        session._request = conn_exception_backoff(  # pyright: ignore[reportPrivateUsage]
            session_backoff(session._request)
        )

        body = Body_client_login(
            grant_type='password', username=NANAPI_CLIENT_USERNAME, password=NANAPI_CLIENT_PASSWORD
        )
        resp = await session.client.client_login(body)
        if not success(resp):
            raise RuntimeError(resp.result)

        bearer_token = resp.result.access_token
        bearer_ready.set()


@cache
def get_nanapi():
    session = get_session(NANAPI_URL)

    session_backoff = backoff.on_predicate(backoff.expo, check_invalid)

    async def auth_on_backoff(details):
        await load_bearer_token()
        await bearer_ready.wait()

    auth_backoff = backoff.on_predicate(
        backoff.expo, lambda r: r.status == 401, max_tries=2, on_backoff=auth_on_backoff
    )

    # Apply connection error backoff, auth backoff, and status code backoff
    session._request = conn_exception_backoff(  # pyright: ignore[reportPrivateUsage]
        auth_backoff(session_backoff(wrap_request(session._request)))
    )

    return session


def wrap_request(_request):
    async def _wrapped(*args, **kwargs):
        if not bearer_ready.is_set():
            await load_bearer_token()
        await bearer_ready.wait()
        headers = {'Authorization': f'Bearer {bearer_token}'}
        kwargs.setdefault('headers', {}).update(headers)
        return await _request(*args, **kwargs)

    return _wrapped
