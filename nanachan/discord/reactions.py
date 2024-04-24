from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union, cast

import discord
import numpy as np
from discord.abc import PrivateChannel

from nanachan.discord.helpers import WebhookMessage
from nanachan.utils.misc import fake_method, ignore, run_coro

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot

logger = logging.getLogger(__name__)


__all__ = ('UnregisterListener',
           'ReactionHandler',
           'ReactionListener')


T = TypeVar('T')


class UnregisterListener(Exception):
    pass


class ReactionHandler:

    def __init__(self,
                 func,
                 reaction: str,
                 on_add: bool = False,
                 on_remove: bool = False,
                 remove_reaction=True):
        self.func = func
        self.reaction = reaction
        self.remove_reaction = remove_reaction
        self.on_add = on_add
        self.on_remove = on_remove

    def __call__(self, listener, user, remove_reaction=True):
        message = listener.message
        if remove_reaction and self.remove_reaction and message.guild is not None:
            asyncio.create_task(ignore(discord.NotFound,
                                       message.remove_reaction(self.reaction, user)))

        func = fake_method(listener, self.func)
        return func(user)

    @classmethod
    def on_reaction(cls, reaction: str, func, on_add=True, on_remove=True):
        return cls(func, reaction, on_add, on_remove)

    @classmethod
    def on_add_reaction(cls, reaction):
        return partial(cls.on_reaction, reaction, on_add=True, on_remove=False)

    @classmethod
    def on_remove_reaction(cls, reaction):
        return partial(cls.on_reaction, reaction, on_add=False, on_remove=True)


class MetaReactionListener(type):

    @classmethod
    def __prepare__(cls, *args, **kwargs):
        return OrderedDict()

    def __new__(cls, name, bases, attrs, **kwargs):
        reaction_handlers: dict[str, dict[str, ReactionHandler]] = {
            'add': OrderedDict(),
            'remove': OrderedDict()
        }

        for base in bases:
            if base_handlers := getattr(base, '_cls_reaction_handlers', None):
                for k in reaction_handlers:
                    reaction_handlers[k].update(base_handlers[k])

        for attr in attrs.values():
            if isinstance(attr, ReactionHandler):
                if attr.on_add:
                    reaction_handlers['add'][attr.reaction] = attr
                if attr.on_remove:
                    reaction_handlers['remove'][attr.reaction] = attr

        attrs['_cls_reaction_handlers'] = reaction_handlers

        return super().__new__(cls, name, bases, attrs)


class HandlerException(Exception):

    def __init__(self, listener: ReactionListener):
        self.listener = listener
        super().__init__(f"{listener} for message {listener.message_id} ({listener.message})")


class ReactionListener(metaclass=MetaReactionListener):
    _cls_reaction_handlers: dict[str, dict[str, ReactionHandler]]

    prefetch_lock = asyncio.Lock()
    PREFETCH_DELAY = 5

    def __init__(self, bot,
                 message: Union[discord.Message, WebhookMessage, discord.WebhookMessage, int],
                 channel_id: int | None = None, first_handlers=None):
        # TODO: remove this when we stop using multiple inherits
        if hasattr(self, "_reaction_handlers"):
            return

        self.bot: Bot = bot
        self.channel_id = channel_id

        if isinstance(message, int):
            self.message = None
            self.message_id = message
        else:
            self.message = message
            self.message_id = message.id
            self.channel_id = cast(int, message.channel.id)  # int | Any???

        if channel_id is not None:
            asyncio.create_task(self.prefetch_message())

        self._done = self.bot.loop.create_future()
        asyncio.create_task(
            self.bot.register_reaction_listener(self.message_id, self)
        )

        self._reaction_handlers = {'add': {},
                                   'remove': {}}
        self._reaction_handlers_order = []
        if first_handlers is not None:
            for handler in first_handlers:
                if handler.on_add:
                    self.on_add_reaction(handler)
                if handler.on_remove:
                    self.on_remove_reaction(handler)

        self.set_cls_handlers()

        if self.message is not None:
            asyncio.create_task(self.check_reactions())

    async def prefetch_message(self):
        async with ReactionListener.prefetch_lock:
            if self.channel_id is None:
                return

            if self.message is None:
                return

            if (channel := self.bot.get_channel(self.channel_id)):
                try:
                    await self.get_message(channel)
                except discord.NotFound:
                    logger.info(f"could not find message {self.message_id}")

                await asyncio.sleep(ReactionListener.PREFETCH_DELAY)

    def get_cls_handlers(self) -> dict[str, dict[str, ReactionHandler]]:
        return self.__class__._cls_reaction_handlers

    def set_cls_handlers(self):
        for h in self.get_cls_handlers()['add'].values():
            self.on_add_reaction(h)
        for h in self.get_cls_handlers()['remove'].values():
            self.on_remove_reaction(h)

    def get_reaction(self, reaction_str: str):
        if emoji := self.bot.get_nana_emoji(reaction_str):
            return emoji

        return reaction_str

    def get_handler(self, action, reaction):
        handlers = self._reaction_handlers[action]
        handler = handlers.get(getattr(reaction, 'name',
                               getattr(reaction, 'emoji', None)))
        if handler is None:
            handler = handlers.get(str(reaction))

        return handler

    async def check_reactions(self):
        assert self.message is not None
        for reaction in self.message.reactions:
            handler = self.get_handler('add', reaction.emoji)
            if handler is None:
                asyncio.create_task(reaction.clear())
            elif reaction.count > 1 and handler.remove_reaction:
                async for user in reaction.users():
                    if not user.bot and user != self.bot.user:
                        await handler(self, user)

    async def clear_reactions(self):
        if self.message is not None:
            with suppress(discord.NotFound):
                await self.message.clear_reactions()

    async def add_reactions(self):
        if self.message is None:
            return

        for handler in self._reaction_handlers_order:
            await self.message.add_reaction(self.get_reaction(handler.reaction))

    async def get_message(self, channel):
        if self.message is None or isinstance(self.message, discord.WebhookMessage):
            self.message = cast(discord.Message, await channel.fetch_message(self.message_id))
            asyncio.create_task(self.check_reactions())

        return self.message

    async def on_reaction(self, payload, action):
        user = self.bot.get_user(payload.user_id)
        if user is None:
            raise RuntimeError(f"Unknown user {payload.user_id}")
        assert self.bot.user is not None
        if user.bot or user.id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if getattr(channel, "guild", None):
            assert not isinstance(channel, PrivateChannel)
            assert channel is not None
            user = channel.guild.get_member(user.id)

        await self.get_message(channel)

        handler = self.get_handler(action, payload.emoji)

        if handler is not None:
            try:
                await handler(self, user, remove_reaction=action == "add")
            except UnregisterListener:
                self.unregister()
            except Exception as e:
                raise HandlerException(self) from e

    def unregister(self):
        self._done.set_result(None)
        return asyncio.create_task(
            self.bot.unregister_reaction_listener(self.message_id)
        )

    async def done(self):
        await self._done

    def add_handler(self, handler):
        if handler.on_add:
            self.on_add_reaction(handler)
        if handler.on_remove:
            self.on_remove_reaction(handler)

    def on_add_reaction(self, handler):
        self._reaction_handlers['add'][handler.reaction] = handler
        self._reaction_handlers_order.append(handler)

    def on_remove_reaction(self, handler):
        self._reaction_handlers['remove'][handler.reaction] = handler
        self._reaction_handlers_order.append(handler)

    def remove_reaction_handler(self, reaction_emoji: str):
        if reaction_emoji in self._reaction_handlers['add']:
            handler = self._reaction_handlers['add'].pop(reaction_emoji)
            self._reaction_handlers_order.remove(handler)
        if reaction_emoji in self._reaction_handlers['remove']:
            del self._reaction_handlers['remove'][reaction_emoji]


@dataclass
class Pages:
    pages: list[Any]
    static_content: Optional[str] = None
    start_at: int = 1
    prefetch_min_batch_size: int = 5
    prefetch_pages: int = 12

    def __post_init__(self):
        self.page_cache = {}
        self._prefetched_upto = 0
        if self.prefetch_pages:
            self.prefetch(self.prefetch_pages)

    def prefetch(self, around: int):
        upto = around + self.prefetch_pages
        from_ = around - self.prefetch_pages
        prefetched_upto = upto + (-upto % self.prefetch_min_batch_size)
        prefetched_from = from_ - (from_ % self.prefetch_min_batch_size)
        prefetchable = np.arange(len(self.pages))
        prefetchable = prefetchable[(prefetchable <= prefetched_upto)
                                  & (prefetchable >= prefetched_from)]  # noqa: E128

        for i in prefetchable:
            if i not in self.page_cache:
                asyncio.create_task(self.get_page(i, prefetch=False))

    async def get_page(self, i, prefetch=True):
        if prefetch:
            self.prefetch(i)

        if i not in self.page_cache:
            loop = asyncio.get_running_loop()
            self.page_cache[i] = loop.create_future()
            try:
                page = await run_coro(self.pages[i])
                if len(self) > 1:
                    page['content'] = '\n'.join(
                        filter(None, [
                            self.static_content,
                            page.get(
                                'content',
                                f"#{self.start_at + i}/{len(self.pages) + self.start_at - 1}"
                            )
                        ]))
                else:
                    page['content'] = self.static_content

                self.page_cache[i].set_result(page)
            except Exception as e:
                self.page_cache[i].set_exception(e)

        return await self.page_cache[i]

    async def get_name(self, i):
        page = await self.get_page(i, prefetch=False)

        embed = None
        if 'embed' in page:
            embed = page['embed']
        elif 'embeds' in page:
            embed = page['embeds'][0]

        if embed is not None:
            return getattr(embed, 'title', None)
        else:
            return None

    def __len__(self):
        return len(self.pages)
