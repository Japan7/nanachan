#!/usr/bin/env python3
import asyncio
import pathlib
import sys
from getpass import getpass
from typing import cast

import rich

sys.path.append(str(pathlib.Path(__file__).parent.parent))

from nanachan.local_settings import NANAPI_CLIENT_PASSWORD, NANAPI_CLIENT_USERNAME
from nanachan.nanapi._client import ClientModule
from nanachan.nanapi.client import Error, Success, get_nanapi_basic_auth
from nanachan.nanapi.model import NewClientBody


async def main() -> None:
    console = rich.console.Console()
    console.print('\nBasic auth credentials', style='bold')
    console.print(
        '(values of BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD in nanapi settings)\n',
        style='italic',
    )
    basic_username = input('basic auth username: ')
    basic_password = getpass('basic auth password: ')

    async with get_nanapi_basic_auth(basic_username, basic_password) as client:
        new_client = NewClientBody(
            username=NANAPI_CLIENT_USERNAME, password=NANAPI_CLIENT_PASSWORD
        )

        # FIXME: ugly hack
        client_mod = cast(ClientModule, client.client)  # pyright: ignore[reportAttributeAccessIssue]
        res = await client_mod.client_register(new_client)
        match res:
            case Success():
                print('successfully registered new client')
            case Error():
                raise RuntimeError(f'failed to register new client.\n{res=}')


if __name__ == '__main__':
    asyncio.run(main())
