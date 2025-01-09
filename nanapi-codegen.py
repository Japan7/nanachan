#!/usr/bin/env python3
import asyncio
from pathlib import Path

from mahou.parsers.openapi import OpenAPIParser
from mahou.serializers.aiohttp_client import OpenAPIaiohttpClientSerializer
from mahou.serializers.model import OpenAPIModelSerializer

import nanachan.nanapi
from nanachan.settings import JAPAN7_AUTH, NANAPI_URL
from nanachan.utils.misc import get_session


async def main():
    module = Path(nanachan.nanapi.__file__).parent

    async with get_session().get(f'{NANAPI_URL}/openapi.json', auth=JAPAN7_AUTH) as resp:
        raw = await resp.read()
    data = raw.decode()

    parser = OpenAPIParser()
    server = parser.parse(data)

    model_serializer = OpenAPIModelSerializer()
    data = model_serializer.serialize(list(server.schemas.values()))
    with open(module / 'model.py', 'w') as f:
        f.write(data)

    client_serializer = OpenAPIaiohttpClientSerializer()
    model = client_serializer.serialize(server)
    with open(module / '_client.py', 'w') as f:
        f.write(model)


if __name__ == '__main__':
    asyncio.run(main())
