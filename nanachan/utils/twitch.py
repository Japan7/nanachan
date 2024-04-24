from functools import cache
from typing import Optional

import aiohttp

from nanachan.utils.misc import get_session

__all__ = ('TwitchAPI',)


class TwitchAPI:
    oauth_endpoint = "https://id.twitch.tv/oauth2/token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.bearer = None

    async def auth(self):
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': ""
        }

        async with get_session().post(TwitchAPI.oauth_endpoint,
                                      raise_for_status=True,
                                      params=params) as req:
            resp = await req.json()
            self.bearer = resp['access_token']

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        if self.bearer is None:
            await self.auth()

        headers = {
            'Authorization': f"Bearer {self.bearer}",
            'Client-Id': self.client_id,
        }

        async with get_session().request(method=method,
                                         url=url,
                                         headers=headers,
                                         raise_for_status=True,
                                         **kwargs) as resp:
            return await resp.json()

    async def request(self, method: str, url, **kwargs) -> dict:
        try:
            return await self._request(method, url, **kwargs)
        except aiohttp.ClientResponseError:
            await self.auth()
            return await self._request(method, url, **kwargs)

    async def api(self, method: str, *path, **params) -> dict:
        url = '/'.join(("https://api.twitch.tv/helix", *path))
        return await self.request('GET', url, params=params)

    @classmethod
    @cache
    def get_twitch(cls) -> Optional['TwitchAPI']:
        from nanachan.settings import TWITCH_CLIENT_ID  # noqa
        from nanachan.settings import TWITCH_CLIENT_SECRET, RequiresTwitch
        if RequiresTwitch:
            assert TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET
            return cls(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
