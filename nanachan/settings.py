# Extensions
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from aiohttp import BasicAuth
from discord.utils import utcnow

NANAPI_URL = 'https://nanapi.japan7.bde.enseeiht.fr/prod'
NANAPI_PUBLIC_URL = NANAPI_URL

DISABLED_EXTENSIONS = set('snowflake')

JAPAN7_AUTH: BasicAuth | None = None

# Karaoke
IGNORED_TIMERS = ['Toyunda Epitanime', '???',
                  'Extérieur', 'Joysound Exporter Japan7', 'Pititi-N']
KARA_BASE: str | None = None
MUGEN_IMPORT_API = "https://dakara.japan7.bde.enseeiht.fr/mugen"

# YoutubeDL
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

# Redis
REDIS_HOST = None
REDIS_PORT = 6379
REDIS_KWARGS = {}

# Debug
DEBUG = True
TADAIMA = False
ERROR_WEBHOOK = None

# Logging
LOG_LEVEL = 'INFO'

# Sound
OPUS_LIB_LOCATION = None
for p in ('/usr/lib/libopus.so.0', '/usr/lib64/libopus.so.0'):
    if Path(p).exists():
        OPUS_LIB_LOCATION = p

# Colour
DEFAULT_COLOUR = 0xe91e63

# Anas
ANAS_ID = 0000

# Bot
PREFIX = '7'
SLASH_PREFIX = ''
TZ = ZoneInfo('Europe/Paris')

# Welcome messages
WELCOME_MSG = ":relaxed: いらっしゃいませ〜〜！ :relaxed:"
WELCOME_BOT = "びーぷ！びぷぶぷ？"
FAREWELL_MSG = "ばいばい {member}〜〜！"

# Easter eggs
WASABI_FREQUENCY = 250
WASABI_RANGE = 50

# Anime
DELETE_ENTRY_IF_CLEANING_ERROR = False

# AMQ
AMQ_USERNAME: str | None = None
AMQ_PASSWORD: str | None = None
AMQ_ROOM_NAME: str | None = None
AMQ_ROOM_PASSWORD: str | None = None
AMQ_DEFAULT_SETTINGS: str | None = None
AMQ_ROOM = 0000

# Projection
PROJO_ROOM = 0000
PROJO_VOICE = 0000
PROJO_THREADS_ROOM = 0000
PROJO_LEADER_ROLE_ID = 0000

# SauceNAO
SAUCENAO_API_KEY = None

# Twitch
TWITCH_CLIENT_ID: str | None = None
TWITCH_CLIENT_SECRET: str | None = None

# AniList
LOW_PRIORITY_THRESH = 30
AL_CACHE_EXPIRE = 3600 * 24

# Role assignment
ROLE_ASSIGNMENT_CHANNEL = 0000

# Waifu
VERIFIED_ROLE: None | int = None
WC_ROLE: None | int = None
WC_CHANNEL = None
DROP_RATE = 1000
GLOBAL_COIN_MULTIPLIER = 1
WC_WEB = 'https://waicolle.japan7.bde.enseeiht.fr'

# Quizz
ANIME_QUIZZ_CHANNEL = 0000
MANGA_QUIZZ_CHANNEL = 0000
LOUIS_QUIZZ_CHANNEL = 0000

# Calendar
ICS_PATH = None
REFRESH_FREQ = 6

# Churros
CHURROS_TOKEN = None
CHURROS_REFRESH_INTERVAL = 15     # in minutes

# ollama
OLLAMA_HOST = ''
OLLAMA_MODEL = ''

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

# Year roles
YEAR_ROLES: Sequence[int] = tuple()

# Bureau
BUREAU_ROLE_ID = 0000

# Local settings
try:
    from .local_settings import *  # noqa: F403
except ImportError:
    raise Exception('A local_settings.py file is required to run this project')

from nanachan.utils.settings import RequiredSettings  # noqa: E402

RequiresAMQ = RequiredSettings(AMQ_DEFAULT_SETTINGS, AMQ_ROOM_PASSWORD,
                               AMQ_ROOM_NAME, AMQ_PASSWORD, AMQ_USERNAME,
                               AMQ_ROOM)
RequiresKaraoke = RequiredSettings(KARA_BASE)
RequiresTwitch = RequiredSettings(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
RequiresRoleAssignment = RequiredSettings(ROLE_ASSIGNMENT_CHANNEL)
RequiresWaicolle = RequiredSettings(WC_ROLE, WC_CHANNEL)
RequiresProjo = RequiredSettings(PROJO_THREADS_ROOM, PROJO_ROOM, PROJO_VOICE, PROJO_LEADER_ROLE_ID)
RequiresQuizz = RequiredSettings(
    ANIME_QUIZZ_CHANNEL, MANGA_QUIZZ_CHANNEL, LOUIS_QUIZZ_CHANNEL)
RequiresCalendar = RequiredSettings(ICS_PATH)
RequiresChurros = RequiredSettings(CHURROS_TOKEN)
RequiresAI = RequiredSettings(OLLAMA_HOST, OLLAMA_MODEL)
