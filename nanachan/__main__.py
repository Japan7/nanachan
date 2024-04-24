import logging

import uvloop
from rich import pretty, traceback

from nanachan.discord.bot import Bot
from nanachan.settings import LOG_LEVEL, TOKEN


def main():
    logging.basicConfig(level=LOG_LEVEL)
    uvloop.install()
    pretty.install()
    traceback.install()
    Bot().run(TOKEN)


if __name__ == '__main__':
    main()
