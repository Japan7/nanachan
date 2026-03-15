import importlib.util
import json
import sys
import types
import unittest
from itertools import count
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = next(
    (parent for parent in Path(__file__).resolve().parents if (parent / 'pyproject.toml').exists()),
    Path(__file__).resolve().parents[1],
)
CONDITIONS_MODULE_PATH = PROJECT_ROOT / 'nanachan' / 'utils' / 'conditions.py'
MODULE_COUNTER = count()


def load_conditions_module():
    def package(name: str):
        module = types.ModuleType(name)
        module.__path__ = []
        return module

    discord_abc = types.ModuleType('discord.abc')
    discord_abc.Messageable = object

    discord_member = types.ModuleType('discord.member')
    discord_member.Member = type('Member', (), {})

    discord_user = types.ModuleType('discord.user')
    discord_user.User = type('User', (), {})

    valkey_exceptions = types.ModuleType('valkey.exceptions')
    valkey_exceptions.ConnectionError = type('ValkeyConnectionError', (Exception,), {})
    valkey_exceptions.TimeoutError = type('ValkeyTimeoutError', (Exception,), {})

    redis_base = types.ModuleType('nanachan.redis.base')

    async def get_valkey():
        return None

    redis_base.get_valkey = get_valkey
    redis_base.make_redis_key = lambda key: key

    misc = types.ModuleType('nanachan.utils.misc')
    misc.json_dumps = lambda value: json.dumps(value, separators=(',', ':'))

    stubbed_modules = {
        'discord': package('discord'),
        'discord.abc': discord_abc,
        'discord.member': discord_member,
        'discord.user': discord_user,
        'valkey': package('valkey'),
        'valkey.exceptions': valkey_exceptions,
        'nanachan': package('nanachan'),
        'nanachan.redis': package('nanachan.redis'),
        'nanachan.redis.base': redis_base,
        'nanachan.utils': package('nanachan.utils'),
        'nanachan.utils.misc': misc,
    }
    stubbed_modules['discord'].abc = discord_abc
    stubbed_modules['discord'].member = discord_member
    stubbed_modules['discord'].user = discord_user
    stubbed_modules['valkey'].exceptions = valkey_exceptions
    stubbed_modules['nanachan'].redis = stubbed_modules['nanachan.redis']
    stubbed_modules['nanachan'].utils = stubbed_modules['nanachan.utils']
    stubbed_modules['nanachan.redis'].base = redis_base
    stubbed_modules['nanachan.utils'].misc = misc

    dynamically_loaded_module_name = f'test_conditions_module_{next(MODULE_COUNTER)}'
    spec = importlib.util.spec_from_file_location(
        dynamically_loaded_module_name, CONDITIONS_MODULE_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, stubbed_modules):
        sys.modules[dynamically_loaded_module_name] = module
        spec.loader.exec_module(module)

    return module


class LoadConditionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_conditions_marks_ready_when_redis_is_disabled(self):
        module = load_conditions_module()
        conditions = module.Conditions()
        waifu_cog = types.SimpleNamespace(bot=types.SimpleNamespace(on_error=AsyncMock()))

        await conditions.load_conditions(waifu_cog)

        self.assertTrue(conditions.ready.is_set())
        waifu_cog.bot.on_error.assert_not_awaited()

    async def test_load_conditions_gracefully_handles_valkey_connection_errors(self):
        module = load_conditions_module()

        async def get_valkey():
            raise module.ValkeyConnectionError('connection refused')

        module.get_valkey = get_valkey
        conditions = module.Conditions()
        waifu_cog = types.SimpleNamespace(bot=types.SimpleNamespace(on_error=AsyncMock()))

        with self.assertLogs(module.logger.name, level='WARNING') as logs:
            await conditions.load_conditions(waifu_cog)

        self.assertTrue(conditions.ready.is_set())
        waifu_cog.bot.on_error.assert_not_awaited()
        self.assertIn('Could not load persisted drop conditions from Valkey', logs.output[0])

    async def test_load_conditions_gracefully_handles_timeouts(self):
        for error_factory in (
            lambda module: TimeoutError('timed out'),
            lambda module: module.ValkeyTimeoutError('timed out'),
        ):
            module = load_conditions_module()
            error = error_factory(module)

            with self.subTest(error_type=type(error).__name__):
                async def get_valkey():
                    raise error

                module.get_valkey = get_valkey
                conditions = module.Conditions()
                waifu_cog = types.SimpleNamespace(bot=types.SimpleNamespace(on_error=AsyncMock()))

                with self.assertLogs(module.logger.name, level='WARNING'):
                    await conditions.load_conditions(waifu_cog)

                self.assertTrue(conditions.ready.is_set())
                waifu_cog.bot.on_error.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
