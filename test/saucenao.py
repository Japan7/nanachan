import asyncio
import sys
from pathlib import Path

main_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(main_dir))

from nanachan.utils.misc import get_session, saucenao_lookup  # noqa: E402


async def main():
    async with get_session():
        data = await saucenao_lookup(
            'https://i.pximg.net/img-master/img/2023/02/24/20/49/35/105674029_p0_master1200.jpg'
        )
        # data = await saucenao_lookup('https://files.catbox.moe/jpsuyh.jpg')
        for r in data:
            if r.similarity > 60:
                print(r)
                print('-------')


if __name__ == '__main__':
    asyncio.run(main())
