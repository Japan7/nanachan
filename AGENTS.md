# Nanachan Development Guide

## Project Overview

Nanachan is a Discord bot for the Japan7 community, built with discord.py. The bot uses an **extension-based architecture** where features are implemented as separate cogs loaded dynamically at startup.

## Architecture

### Core Components

- **Bot (`nanachan/discord/bot.py`)**: Custom `AutoShardedBot` subclass with hot-reload support in DEBUG mode, custom command prefix resolution (`7`), and unified error handling
- **Cogs (`nanachan/discord/cog.py`)**: Extensions inherit from `Cog` or `NanaGroupCog` with metaclass `CogMeta` to support:
  - Optional `required_settings` parameter to disable cogs when config is incomplete
  - `group_name` for slash command groups (automatically prefixed with `SLASH_PREFIX`)
- **Extensions (`nanachan/extensions/`)**: Each feature module must export `async def setup(bot: Bot)` to register cogs
- **Settings (`nanachan/settings.py`)**: Centralized configuration with local overrides via `local_settings.py` (required, copy from `example.local_settings.py`)

### API Client (nanapi)

The bot communicates with a backend API (`nanapi`) using **auto-generated client code**:

- **Code generation**: Run `uv run ./nanapi-codegen.py` (or task `nanapi-codegen`) to regenerate `nanachan/nanapi/_client.py` and `nanachan/nanapi/model.py` from the OpenAPI spec
- **Client usage**: Import from `nanachan.nanapi.client` which wraps the generated client with authentication (bearer token), backoff retry logic, and exposes `get_nanapi()` singleton
- **Response handling**: API responses are `Success | Error` types; use `success(resp)` type guard before accessing `resp.result`
- **Backend project**: https://github.com/Japan7/nanapi
- **Local dev environment**: https://github.com/Japan7/nanadev provides one-click setup for both nanapi and nanachan

### Redis Integration

Redis is used for ephemeral state (caching, rate limiting). The `nanachan/redis/` module provides typed abstractions:

- **BaseRedis**: Abstract base with `get()`, `set()`, `expire_at()`, `delete()` methods
- **Specialized types**: `StringValue`, `IntegerValue`, `FloatValue`, `BooleanValue`, `JSONValue`
- **Usage pattern**: Define a class extending one of these types with your `key_prefix`

## Development Workflow

### Running Locally

```bash
# Setup Redis (or use Valkey)
docker run -d --name redis -p 6379:6379 valkey/valkey:latest

# Configure bot (see README.md for Discord app setup)
cp nanachan/example.local_settings.py nanachan/local_settings.py
# Edit nanachan/local_settings.py with your TOKEN and settings

# Run bot
uv run --frozen -m nanachan
```

### Code Quality & Pre-commit

Use the provided git hooks to enforce checks before commits:

```bash
git config core.hookspath hooks
```

The hook runs:
- `ruff check` - linting
- `ruff format --check` - formatting verification
- `fawltydeps` - unused dependency detection
- `pyright` - type checking (only if `HOOKS_PYRIGHT_CHECK` env var is set)

**Run manually**: `uv run --frozen ruff check nanachan/` or `uv run --frozen ruff format nanachan/`

### Hot Reload

In DEBUG mode, the bot watches `nanachan/extensions/` and automatically reloads changed extensions without restarting.

## Code Patterns

### Creating a Cog/Extension

```python
# nanachan/extensions/my_feature.py
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from discord.ext import commands

class MyFeature(Cog):
    """Cog description shown in help"""
    emoji = '🎨'  # Display emoji for help

    def __init__(self, bot: Bot):
        super().__init__(bot)
        # initialization

    @commands.command()
    async def mycommand(self, ctx):
        await ctx.send("Response")

async def setup(bot: Bot):
    await bot.add_cog(MyFeature(bot))
```

### Conditional Feature Loading

Use `RequiredSettings` to disable cogs when config is missing:

```python
from nanachan.settings import RequiresWaicolle  # Example from settings.py

class WaiColle(Cog, required_settings=RequiresWaicolle):
    # Cog only loads if WC_ROLE is configured
```

### Command Contexts & Interactions

- **New commands**: Use discord.py v2 `Interaction` API directly (app commands, slash commands)
- **LegacyCommandContext**: Adapter for old v1 command system - avoid in new code
- **MultiplexingContext**: Supports nested command syntax with `{{` and `}}` delimiters for command chaining
- **Views over reactions**: Prefer `discord.ui.View` (buttons, modals, select menus) over reaction listeners which are deprecated. See `AutoNavigatorView`, `NavigatorView`, `LockedView` in `nanachan/discord/views.py` for patterns

### Custom Emoji Handling

Use `bot.get_emoji_str(name)` to resolve custom guild emojis or fall back to `:name:` format. The bot searches across all guilds it's in.

## Dependencies

- **Package manager**: `uv` (all commands use `uv run --frozen`)
- **Python version**: 3.13+
- **Discord.py**: Custom fork from Japan7 org (see `pyproject.toml` `[tool.uv.sources]`)
- **Type checking**: Pyright in strict mode (see `[tool.pyright]`)
- **Formatting**: Ruff with single quotes, 99 char line length

For discord.py API and usage patterns, consult **Context7**: https://context7.com/websites/discordpy_readthedocs_io_en_stable

## Key Files

- `nanachan/__main__.py` - Entry point, sets up logging and Rich traceback
- `nanachan/settings.py` - All configuration with defaults and `RequiredSettings` validators
- `nanachan/discord/bot.py` - Core bot class with multiplexing, reactions, webhooks, error handling
- `nanachan/extensions/` - All feature implementations (19 modules including `waicolle`, `amq`, `quizz`, `projection`, `ai`, etc.)
- `nanapi-codegen.py` - Regenerate API client from OpenAPI spec
- `hooks/pre-commit` - Quality checks (ruff, fawltydeps, pyright)

## Testing & Debugging

- Set `DEBUG = True` in `local_settings.py` to enable debug-level logging and hot reload
- Testing is done manually on Discord by invoking commands and observing behavior
- Error messages are sent to `ERROR_WEBHOOK` if configured, otherwise to `BOT_ROOM_ID`
- Check console output with Rich formatting for detailed tracebacks
