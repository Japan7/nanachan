# TODO: Uncommented variables must be set to work properly.
# ruff: noqa: I001

# from zoneinfo import ZoneInfo

from aiohttp import BasicAuth
# from pydantic_ai.common_tools.tavily import tavily_search_tool
# from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP

# LOG_LEVEL = 'INFO'
# DEBUG = True
# ERROR_WEBHOOK = None
# TADAIMA = False

## GitHub Issues
# GITHUB_ISSUE_ENABLE = not DEBUG
# GITHUB_REPO_SLUG = 'Japan7/nanachan'
# GITHUB_TOKEN = None

## Bot
TOKEN = ''
PREFIX = '7'
SLASH_PREFIX = ''
BOT_ROOM_ID = 0000
BOT_VOICE_ID = 0000
# TZ = ZoneInfo('Europe/Paris')
# DEFAULT_COLOUR = 0xE91E63
# DISABLED_EXTENSIONS = set('snowflake')
# ENABLE_MESSAGE_EXPORT = False

## nanapi
# NANAPI_URL = 'https://nanapi.japan7.bde.enseeiht.fr/prod'
# NANAPI_PUBLIC_URL = NANAPI_URL
JAPAN7_AUTH = BasicAuth('username', 'password')
NANAPI_CLIENT_USERNAME = ''
NANAPI_CLIENT_PASSWORD = ''

## Redis
REDIS_HOST = None
# REDIS_PORT = 6379
# REDIS_KWARGS = {}

## Roles
# ANAS_ID = 0000
# BUREAU_ROLE_ID = 0000
# YEAR_ROLES = tuple()

## Welcome messages
# WELCOME_MSG = ':relaxed: いらっしゃいませ {member}〜〜！ :relaxed:'
# WELCOME_BOT = 'びーぷ！びぷぶぷ？'
# FAREWELL_MSG = 'ばいばい {member}〜〜！'

## Easter eggs
# WASABI_FREQUENCY = 250
# WASABI_RANGE = 50

## Audio
# YOUTUBE_DL_CONFIG = {
#     'format': 'bestaudio/best',
#     'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
#     'restrictfilenames': True,
#     'noplaylist': True,
#     'ignoreerrors': False,
#     'logtostderr': False,
#     'quiet': True,
#     'no_warnings': True,
#     'default_search': 'ytsearch5',
# }
# OPUS_LIB_LOCATION = None

## Karaoke
# IGNORED_TIMERS = ['Toyunda Epitanime', '???', 'Extérieur', 'Joysound Exporter Japan7', 'Pititi-N']
# KARA_BASE = None

## AMQ
# AMQ_USERNAME = None
# AMQ_PASSWORD = None
# AMQ_ROOM_NAME = None
# AMQ_ROOM_PASSWORD = None
# AMQ_DEFAULT_SETTINGS = None
# AMQ_ROOM = 0000

## Projection
# PROJO_ROOM = 0000
# PROJO_VOICE = 0000
# PROJO_THREADS_ROOM = 0000
# PROJO_LEADER_ROLE_ID = 0000

## Quizz
# ANIME_QUIZZ_CHANNEL = 0000
# MANGA_QUIZZ_CHANNEL = 0000
# LOUIS_QUIZZ_CHANNEL = 0000

## WaiColle
# WC_ROLE = None
# DROP_RATE = 1000
# GLOBAL_COIN_MULTIPLIER = 1
# WC_WEB = 'https://waicolle.japan7.bde.enseeiht.fr'

## Calendar
# NANALOOK_URL = 'https://nanalook.japan7.bde.enseeiht.fr'

## AI
# AI_OPENROUTER_API_KEY = ''
# AI_FLAGSHIP_MODEL = 'openai/gpt-4.1'
# AI_DEFAULT_MODEL = 'openai/gpt-4.1-mini'
# AI_LOW_LATENCY_MODEL = 'openai/gpt-4.1-nano'
# AI_GROK_MODEL = 'x-ai/grok-4.1-fast'
# AI_IMAGE_MODEL = 'google/gemini-3-pro-image-preview'
# AI_SKIP_PERMISSIONS_CHECK = False
# AI_SEARCH_TOOL = tavily_search_tool('API_KEY')
AI_ADDITIONAL_TOOLSETS = [
    # MCPServerStreamableHTTP('https://mcp.context7.com/mcp'),
    # MCPServerStreamableHTTP('https://mcp.deepwiki.com/mcp'),
    # MCPServerStdio('uvx', args=['mcp-run-python@latest', 'stdio'], timeout=10),
]

## SauceNAO
# SAUCENAO_API_KEY = None

## Producer
# PRODUCER_UPLOAD_ENDPOINT = 'https://producer.japan7.bde.enseeiht.fr'
# PRODUCER_TOKEN = ''
