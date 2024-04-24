from typing import Optional

from nanachan.utils.misc import get_session

__all__ = ('get_type', 'is_image')


async def get_type(url: str) -> Optional[str]:
    async with get_session().head(url) as req:
        return req.headers.get('Content-Type')


async def is_image(url: str) -> bool:
    if url is None:
        return False

    img_type = await get_type(url)
    return img_type.split('/')[0] == 'image' if img_type is not None else False
