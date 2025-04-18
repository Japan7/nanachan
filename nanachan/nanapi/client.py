import asyncio
from functools import cache

import backoff
from aiohttp import ClientResponse
from pydantic_ai.tools import Tool

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


async def load_bearer_token():
    global bearer_token
    if load_lock.locked():
        return
    async with load_lock:
        bearer_ready.clear()

        session = get_session(NANAPI_URL)
        session_backoff = backoff.on_predicate(backoff.expo, check_invalid)
        session._request = session_backoff(session._request)

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

    session._request = auth_backoff(session_backoff(wrap_request(session._request)))

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


def get_nanapi_tools() -> list[Tool]:
    nanapi = get_nanapi()
    tools = [
        nanapi.anilist.anilist_get_accounts,
        nanapi.anilist.anilist_get_account_entries,
        nanapi.anilist.anilist_get_medias,
        nanapi.anilist.anilist_media_search,
        nanapi.anilist.anilist_get_media_list_entries,
        nanapi.anilist.anilist_get_media_chara_edges,
        nanapi.anilist.anilist_get_charas,
        nanapi.anilist.anilist_chara_search,
        nanapi.anilist.anilist_get_chara_chara_edges,
        nanapi.anilist.anilist_get_staffs,
        nanapi.anilist.anilist_staff_search,
        nanapi.anilist.anilist_get_staff_chara_edges,
        nanapi.user.user_get_profile,
        nanapi.waicolle.waicolle_get_players,
        nanapi.waicolle.waicolle_get_player,
        nanapi.waicolle.waicolle_get_player_tracked_items,
        nanapi.waicolle.waicolle_get_player_track_unlocked,
        nanapi.waicolle.waicolle_get_player_track_reversed,
        nanapi.waicolle.waicolle_get_player_media_stats,
        nanapi.waicolle.waicolle_get_player_staff_stats,
        nanapi.waicolle.waicolle_get_player_collection_stats,
        nanapi.waicolle.waicolle_get_waifus,
        nanapi.waicolle.waicolle_trade_index,
        nanapi.waicolle.waicolle_get_collection,
    ]
    return [Tool(tool) for tool in tools]
