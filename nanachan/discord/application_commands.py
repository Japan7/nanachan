from __future__ import annotations

import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar, override

from discord import Interaction, InteractionCallbackResponse, app_commands
from discord.ext.commands import CommandError, Context
from discord.interactions import InteractionMessage
from discord.webhook import WebhookMessage

from nanachan.discord.bot import Bot
from nanachan.settings import SLASH_PREFIX

__all__ = ('LegacyCommandContext', 'nana_command', 'legacy_command', 'handle_command_errors')

logger = logging.getLogger(__name__)


class LegacyCommandContext(Context[Bot]):
    ephemeral: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sending = asyncio.Lock()
        self.ephemeral = False

    @override
    @classmethod
    async def from_interaction(cls, interaction: Interaction[Bot], ephemeral: bool = False):
        inst = await super().from_interaction(interaction)
        inst.ephemeral = ephemeral
        return inst

    async def send_initial_message(self):
        try:
            await asyncio.sleep(1)
            await self.defer(ephemeral=self.ephemeral)
        except Exception as error:
            self.bot.dispatch('command_error', self, error)

    async def defer(self, *, ephemeral: bool = False):
        assert self.interaction is not None
        async with self._sending:
            if not self.interaction.response.is_done():
                await self.interaction.response.defer(ephemeral=ephemeral)

    async def reply(self, *args, **kwargs):
        return await self.send(*args, **kwargs)

    async def send(
        self, content: str | None = None, **kwargs
    ) -> InteractionMessage | WebhookMessage:
        assert self.interaction is not None
        if content is not None:
            kwargs['content'] = content

        async with self._sending:
            if self.interaction.response.is_done():
                send = self.interaction.followup.send
            else:
                send = self.interaction.response.send_message
                kwargs.setdefault('ephemeral', self.ephemeral)

            signature = inspect.signature(send)
            to_remove = [key for key in kwargs if key not in signature.parameters]
            for key in to_remove:
                logger.info(f'ignoring {key}')
                del kwargs[key]

            message = await send(**kwargs)
            if isinstance(message, InteractionCallbackResponse) or message is None:
                self._message = await self.interaction.original_response()
                return self._message

            return message


T = TypeVar('T')
P = ParamSpec('P')


def app_command_decorator(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def decorated(*args, **kwargs):
        def cmd_decorator(func):
            kwargs['name'] = SLASH_PREFIX + kwargs.get('name', func.__name__)

            return app_commands.command(*args, **kwargs)(func)

        return cmd_decorator

    return decorated  # type: ignore


nana_command = app_command_decorator(app_commands.command)


def group_decorator(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def decorated(*args, **kwargs):
        kwargs['name'] = SLASH_PREFIX + kwargs.get('name', func.__name__)
        return func(*args, **kwargs)

    return decorated


@group_decorator
class NanaGroup(app_commands.Group):
    pass


def handle_command_errors(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    async def decorated(interaction: Interaction, *args, **kwargs):
        try:
            return await func(interaction, *args, **kwargs)  # type: ignore
        except CommandError as e:
            if interaction.response.is_done():
                await interaction.followup.send(str(e))
            else:
                await interaction.response.send_message(str(e))

    return decorated  # type: ignore


def legacy_command(ephemeral: bool = False):
    def decorator(
        func: Callable[Concatenate[Any, LegacyCommandContext, P], T],
    ) -> Callable[Concatenate[Any, Interaction, P], T]:
        @wraps(func)
        async def decorated(cog, interaction: Interaction[Bot], *args, **kwargs) -> T | None:
            ctx = await LegacyCommandContext.from_interaction(interaction, ephemeral=ephemeral)
            _ = asyncio.create_task(ctx.send_initial_message())
            try:
                return await func(cog, ctx, *args, **kwargs)  # type: ignore
            except CommandError as e:
                await ctx.send(str(e))

        return decorated  # type: ignore

    return decorator
