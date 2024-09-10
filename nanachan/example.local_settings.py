# Copy this file to local_settings.py and edit it before doing anything else
from aiohttp import BasicAuth

JAPAN7_AUTH = BasicAuth('username', 'password')

# nanapi
#NANAPI_URL = 'https://nanapi.japan7.bde.enseeiht.fr/prod'
#NANAPI_PUBLIC_URL = NANAPI_URL
NANAPI_CLIENT_USERNAME = ''
NANAPI_CLIENT_PASSWORD = ''

# Debug
#DEBUG = True
#TADAIMA = False
#ERROR_WEBHOOK = "https://discord.com/api/webhooks/..."  # noqa

# Disabled extensions
#from .settings import DISABLED_EXTENSIONS
#DISABLED_EXTENSIONS.add('animes')
#DISABLED_EXTENSIONS.remove('snowflake')

# Client

TOKEN = 'token'
BOT_ROOM_ID = 0000
BOT_VOICE_ID = 0000

# Bot
#PREFIX = '7'
#SLASH_PREFIX = ''
#from zoneinfo import ZoneInfo
#TZ = ZoneInfo('Europe/Paris')

# Redis
#REDIS_HOST = "redis"
#REDIS_PORT = 6379
#REDIS_KWARGS = {}

# Logging
#LOG_LEVEL = 'INFO'

# Sound
#OPUS_LIB_LOCATION = '/usr/lib/libopus.so.0'

# Nanachan
#DATABASE_PATH = 'db.sqlite3'

# Karaoke
#KARA_BASE = '/path/to/nextcloud'

# Anime
#ANIME_FEED_ROOM_ID = 0000

# Anas
#ANAS_ID = 0000

# Easter eggs
#WASABI_FREQUENCY = 250
#WASABI_RANGE = 50

# AMQ
#AMQ_USERNAME = ""
#AMQ_PASSWORD = ""
#AMQ_ROOM_NAME = ""
#AMQ_ROOM_PASSWORD = ""
#AMQ_DEFAULT_SETTINGS = ""
#AMQ_ROOM = 0000

# Anime
#DELETE_ENTRY_IF_CLEANING_ERROR = False

# Projection
#PROJO_ROOM = 0000
#PROJO_VOICE = 0000
#PROJO_THREADS_ROOM = 0000

# Twitch
#TWITCH_CLIENT_ID = ""
#TWITCH_CLIENT_SECRET = ""

# AniList
#LOW_PRIORITY_THRESH = 30

# Role assignment
#ROLE_ASSIGNMENT_CHANNEL = None

# Waifu
#VERIFIED_ROLE = 0000
#WC_ROLE = 0000
#WC_CHANNEL = 0000
#DROP_RATE = 1000
#GLOBAL_COIN_MULTIPLIER = 1
#WC_WEB = 'https://waicolle.japan7.bde.enseeiht.fr'

# Year roles
# [4A+, 3A, 2A, 1A]
# YEAR_ROLES = [0000, 0000, 0000, 0000]

# Bureau
#BUREAU_ROLE_ID = 0000

# Quizz
# ANIME_QUIZZ_CHANNEL = 0000
# MANGA_QUIZZ_CHANNEL = 0000
# LOUIS_QUIZZ_CHANNEL = 0000

# Churros
# CHURROS_TOKEN = None
# CHURROS_REFRESH_INTERVAL = 0     # in minutes

# ollama
# OLLAMA_HOST = 'http://localhost:11434'
# OLLAMA_MODEL = 'llama3'

# producer
#PRODUCER_UPLOAD_ENDPOINT = "https://producer.japan7.bde.enseeiht.fr"
#PRODUCER_TOKEN = ""
