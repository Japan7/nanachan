from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from aiohttp import BasicAuth
from discord.utils import utcnow
from pydantic_ai.models import Model
from pydantic_ai.providers import Provider

LOG_LEVEL = 'INFO'
DEBUG = True
ERROR_WEBHOOK = None
TADAIMA = False

## Bot
# TOKEN = ''
PREFIX = '7'
SLASH_PREFIX = ''
# BOT_ROOM_ID = 0000
# BOT_VOICE_ID = 0000
TZ = ZoneInfo('Europe/Paris')
DEFAULT_COLOUR = 0xE91E63
DISABLED_EXTENSIONS = set('snowflake')

## nanapi
NANAPI_URL = 'https://nanapi.japan7.bde.enseeiht.fr/prod'
NANAPI_PUBLIC_URL = NANAPI_URL
JAPAN7_AUTH: BasicAuth | None = None
# NANAPI_CLIENT_USERNAME = ''
# NANAPI_CLIENT_PASSWORD = ''

## Redis
REDIS_HOST = None
REDIS_PORT = 6379
REDIS_KWARGS = {}

## Roles
ANAS_ID = 0000
BUREAU_ROLE_ID = 0000
YEAR_ROLES: Sequence[int] = tuple()

## Welcome messages
WELCOME_MSG = ':relaxed: いらっしゃいませ {member}〜〜！ :relaxed:'
WELCOME_BOT = 'びーぷ！びぷぶぷ？'
FAREWELL_MSG = 'ばいばい {member}〜〜！'

## Easter eggs
WASABI_FREQUENCY = 250
WASABI_RANGE = 50

## Audio
YOUTUBE_DL_CONFIG = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch5',
}
OPUS_LIB_LOCATION = None
for p in ('/usr/lib/libopus.so.0', '/usr/lib64/libopus.so.0'):
    if Path(p).exists():
        OPUS_LIB_LOCATION = p

## Karaoke
IGNORED_TIMERS = ['Toyunda Epitanime', '???', 'Extérieur', 'Joysound Exporter Japan7', 'Pititi-N']
KARA_BASE: str | None = None

## AMQ
AMQ_USERNAME: str | None = None
AMQ_PASSWORD: str | None = None
AMQ_ROOM_NAME: str | None = None
AMQ_ROOM_PASSWORD: str | None = None
AMQ_DEFAULT_SETTINGS: str | None = None
AMQ_ROOM = 0000

## Projection
PROJO_ROOM = 0000
PROJO_VOICE = 0000
PROJO_THREADS_ROOM = 0000
PROJO_LEADER_ROLE_ID = 0000

## Quizz
ANIME_QUIZZ_CHANNEL = 0000
MANGA_QUIZZ_CHANNEL = 0000
LOUIS_QUIZZ_CHANNEL = 0000

## WaiColle
WC_ROLE: None | int = None
DROP_RATE = 1000
GLOBAL_COIN_MULTIPLIER = 1
WC_WEB = 'https://waicolle.japan7.bde.enseeiht.fr'

## Calendar
NANALOOK_URL = 'https://nanalook.japan7.bde.enseeiht.fr'

## AI
AI_MODEL_CLS: type[Model] | None = None
AI_DEFAULT_MODEL: str | None = None
AI_REASONING_MODEL: str | None = None
AI_LOW_LATENCY_MODEL: str | None = None
AI_PROVIDER: Provider | None = None

## SauceNAO
SAUCENAO_API_KEY = None

## Producer
PRODUCER_UPLOAD_ENDPOINT = 'https://producer.japan7.bde.enseeiht.fr'
PRODUCER_TOKEN = ''


_spamers = {}
_start_time = utcnow()


async def is_spam(ctx) -> bool:
    if last_spam := _spamers.get(ctx.author.id):
        ts = last_spam.created_at
    else:
        ts = _start_time

    delta = (ctx.message.created_at - ts).total_seconds()
    spam = delta < 5 and ctx.author.id in _spamers
    if not spam:
        _spamers[ctx.author.id] = ctx.message

    return spam


# Local settings
try:
    from .local_settings import *  # noqa: F403
except ImportError:
    raise Exception('A local_settings.py file is required to run this project')

from nanachan.utils.settings import RequiredSettings  # noqa: E402

RequiresKaraoke = RequiredSettings(KARA_BASE)
RequiresAMQ = RequiredSettings(
    AMQ_DEFAULT_SETTINGS, AMQ_ROOM_PASSWORD, AMQ_ROOM_NAME, AMQ_PASSWORD, AMQ_USERNAME, AMQ_ROOM
)
RequiresProjo = RequiredSettings(PROJO_THREADS_ROOM, PROJO_ROOM, PROJO_VOICE, PROJO_LEADER_ROLE_ID)
RequiresQuizz = RequiredSettings(ANIME_QUIZZ_CHANNEL, MANGA_QUIZZ_CHANNEL, LOUIS_QUIZZ_CHANNEL)
RequiresWaicolle = RequiredSettings(WC_ROLE)
RequiresAI = RequiredSettings(
    AI_MODEL_CLS, AI_DEFAULT_MODEL, AI_REASONING_MODEL, AI_LOW_LATENCY_MODEL, AI_PROVIDER
)
