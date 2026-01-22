from __future__ import annotations

import abc
import asyncio
import datetime
import logging
import random
import re
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from functools import cached_property, wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    NotRequired,
    TypedDict,
    TypeVar,
    Unpack,
    cast,
)

import discord
import parsedatetime.parsedatetime as pdt
from discord import (
    ForumChannel,
    HTTPException,
    Message,
    StickerItem,
    TextChannel,
    Thread,
    User,
    Webhook,
    app_commands,
)
from discord.abc import PrivateChannel
from discord.ext import commands
from discord.ext.commands import BadArgument, Command
from discord.ext.commands.converter import MemberConverter
from discord.ext.commands.view import StringView
from discord.mentions import AllowedMentions
from discord.types.embed import EmbedType
from discord.webhook import WebhookMessage as DpyWebhookMessage
from yarl import URL

from nanachan.settings import DEFAULT_COLOUR, PREFIX, TZ
from nanachan.utils.misc import default_backoff, run_coro, truncate_at

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot
    from nanachan.extensions.easter_eggs import Bananas


__all__ = (
    'ChannelListener',
    'Colour',
    'Embed',
    'Members',
    'MembersTransformer',
    'MultiplexingContext',
    'MultiplexingMessage',
    'UserType',
    'WebhookMessage',
    'clean_markdown',
    'context_modifier',
    'default_backoff',
    'get_multiplexing_level',
    'get_option',
    'parse_timestamp',
    'timestamp_autocomplete',
    'typing',
)

logger = logging.getLogger(__name__)


class Colour(discord.Colour):
    colour_prog = re.compile(r'(rgba?|hsv)\s*\((\d+%?)\s*,\s*(\d+%?)\s*,\s*(\d+%?)')

    @classmethod
    def from_hex(cls, string: str):
        string = string.strip('#')
        if len(string) == 3:
            string = ''.join(c + c for c in string)

        return cls(int(string, 16))

    @staticmethod
    def _get_values(values: Sequence[str]):
        for val in values:
            if val.endswith('%'):
                yield round(int(val[:-1]) * 255 / 100)
            else:
                yield int(val)

    @classmethod
    def from_string(cls, string: str):
        string = string.strip()
        if string.startswith('#'):
            return cls.from_hex(string)

        match = cls.colour_prog.search(string)
        if match is None:
            predefined_colour = getattr(cls, string, None)
            if predefined_colour:
                return predefined_colour()
        else:
            groups = match.groups()
            kwargs = {k: v for k, v in zip(groups[0][:3], cls._get_values(groups[1:]))}

            if groups[0].startswith('rgb'):
                return cls.from_rgb(**kwargs)
            if groups[0].startswith('hsv'):
                return cls.from_hsv(**kwargs)

        return cls.default()

    @classmethod
    def default(cls):
        return cls(DEFAULT_COLOUR)


@dataclass
class EmbedField:
    name: str
    value: Any
    inline: bool = True


class EmbedExtraKWArgs(TypedDict):
    type: NotRequired[EmbedType]
    timestamp: NotRequired[datetime.datetime | None]


class Embed(discord.Embed):
    def __init__(
        self,
        title: str | None = None,
        description: str | None = None,
        url: str | None = None,
        colour: int | discord.Colour | None = None,
        color: int | discord.Colour | None = None,
        **kwargs: Unpack[EmbedExtraKWArgs],
    ):
        if title:
            title = truncate_at(256, title)

        if description:
            description = truncate_at(2048, description)

        if colour is None:
            if color is None:
                colour = Colour.default()
            else:
                colour = color

        super().__init__(title=title, url=url, description=description, colour=colour, **kwargs)


fuckin_markdown_star = re.compile(r'(\*+)(?P<clean>[^*\n]*)\1')
fuckin_markdown_underscore = re.compile(r'(?P<stop>https?://[^\s]*)?(\_+)(?P<clean>[^_\n]*)\2')
fuckin_markdown_strike = re.compile(r'(~~)(?P<clean>[^_\n]*?)~~')
markdown_cleaners = [
    fuckin_markdown_star,
    fuckin_markdown_underscore,
    fuckin_markdown_strike,
]


def _clean(match):
    groupdict = match.groupdict()
    if groupdict.get('stop', False):
        return match.group(0)
    else:
        return groupdict['clean']


def clean_markdown(text: str) -> str:
    for cleaner in markdown_cleaners:
        text = cleaner.sub(_clean, text)

    return text


MULTIPLEXING_CHARS: dict[str, tuple[str, str]] = {
    '(': ('(', ')'),
    '[': ('[', ']'),
    '{': ('{', '}'),
    '|': ('||', '||'),
    '~': ('~~', '~~'),
    '_': ('_', '_'),
    '*': ('*', '*'),
    '`': ('`', '`'),
}


def _get_multiplexing_level(text: str):
    if text:
        opening, closing = MULTIPLEXING_CHARS.get(text[0], (None, None))
        if (
            opening is not None
            and closing is not None
            and text.startswith(opening)
            and text.endswith(closing)
        ):
            text = strip_multiplexing_chars(text, opening, closing)
            yield opening, closing
            yield from _get_multiplexing_level(text)


def get_multiplexing_level(message: discord.Message | str):
    if isinstance(message, str):
        text = message
    else:
        text = message.content

    if multiplexing_level := list(map(''.join, zip(*_get_multiplexing_level(text)))):
        return multiplexing_level[0], multiplexing_level[1][::-1]


def strip_multiplexing_chars(text: str, opening: str | None, closing: str | None):
    if opening and closing:
        return text[len(opening) : -len(closing)]
    else:
        return text


context_modifiers = []


def context_modifier(func):
    context_modifiers.append(func)
    return func


ContextModifier = context_modifier


class MultiplexingContext(commands.Context['Bot']):
    bot: Bot
    listeners: list[
        tuple[Callable[[MultiplexingContext], bool], asyncio.Future[MultiplexingContext]]
    ] = []

    async def get_user_webhook(self, app_cmd_context: bool = False) -> 'WebhookProxy':
        if self.guild is None:
            raise RuntimeError('Webhook cannot be created outside of a guild')

        assert isinstance(self.channel, (TextChannel, ForumChannel, Thread))
        webhook = await self.bot.get_webhook(self.channel)
        webhook = CheckEmptyWebhook(webhook)
        webhook = UserWebhook(webhook, cast(User, self.author))

        if not app_cmd_context:
            webhook = ReplyWebhook(webhook, self.message)
            webhook = AttachmentsWebhook(webhook, self.message.attachments)

            if self.message.stickers:
                webhook = StickerWebhook(webhook, self.message.stickers)

        if isinstance(self.channel, discord.Thread):
            webhook = ThreadWebhook(webhook, self.channel)
        else:
            webhook = WebhookProxy(webhook)

        if self.bananased:
            webhook = BananasWebhook(webhook)

        return webhook

    @cached_property
    def bananased(self) -> bool:
        bananas_cog = cast('Bananas | None', self.bot.get_cog('Bananas'))
        if bananas_cog is not None:
            if perms := getattr(self.author, 'guild_permissions', None):
                bananas_cmd = getattr(self, 'command', None) in (
                    bananas_cog.unbananas,
                    bananas_cog.bananas,
                )
                if perms.administrator and bananas_cmd:
                    return False

            return self.author.id in bananas_cog.bananased_member_ids

        return False

    @cached_property
    def webhooked(self) -> bool:
        return (
            not self.author.bot
            and self.guild is not None
            and self.message.system_content == self.message.content
            and self.bananased
        )

    def __init__(self, message: discord.Message, **attrs):
        self._command = None
        if multiplexing_level := get_multiplexing_level(message):
            self.opening, self.closing = multiplexing_level
        else:
            self.opening, self.closing = '', ''

        self.amqed: bool = getattr(message, 'amqed', False)
        super().__init__(message=message, **attrs)

        if quizz_cog := self.bot.get_cog('Quizz'):
            imaaaage = re.match(rf'{re.escape(PREFIX)}ima+ge', self.message.stripped_content)
            if imaaaage is not None:
                self.command = cast(Command, quizz_cog.image)  # type: ignore # I don't even get it

        self.will_delete = self.get_will_delete()

    async def wait(self):
        if self.is_user_message:
            modifiers_tasks = [
                asyncio.create_task(run_coro(listener(self))) for listener in context_modifiers
            ]
            if modifiers_tasks:
                await asyncio.wait(modifiers_tasks)

    @classmethod
    def set_will_delete(
        cls, *, check: Callable[[MultiplexingContext], bool]
    ) -> asyncio.Future[MultiplexingContext]:
        fut = asyncio.get_running_loop().create_future()
        cls.listeners.append((check, fut))
        return fut

    @property
    def is_user_message(self):
        return not self.webhooked or self.message.is_webhook_message

    def get_will_delete(self):
        if not self.is_user_message:
            return

        listeners = self.__class__.listeners
        removed = []

        for i, (condition, future) in enumerate(listeners):
            if future.cancelled():
                removed.append(i)
                continue

            try:
                result = condition(self)
            except Exception as e:
                future.set_exception(e)
                removed.append(i)
                continue

            if result:
                future.set_result(self)
                removed.append(i)

        for idx in reversed(removed):
            del listeners[idx]

        return len(removed) > 0

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):  # type: ignore # trust me bro
        self._message = MultiplexingMessage(value)

    @property
    def command(self) -> Command | None:
        return self._command

    @command.setter
    def command(self, value: Command | None):
        if value is not None:
            self._command = value

    @property
    def view(self) -> StringView:
        return self._view

    @view.setter
    def view(self, value: StringView):  # type: ignore # trust me bro
        if (
            self.opening
            and self.closing
            and value.buffer.startswith(self.opening)
            and value.buffer.endswith(self.closing)
        ):
            value.buffer = value.buffer[: -len(self.closing)]
            value.end = len(value.buffer)

        self._view = value

    @default_backoff
    async def send(self, content: str | None = None, *args, **kwargs):  # type: ignore # trust me bro
        logger.info('send')
        if content is not None:
            content = f'{self.opening}{content}{self.closing}'

        return MultiplexingMessage(await super().send(content, *args, **kwargs))


class MultiplexingMessage:
    url_prog = re.compile(r'https?://[^\s]+')
    emoji_prog = re.compile(r'<a?(:[^ :]+:)\d+>')
    webhook_author = {}

    def __init__(self, message):
        self._message = message
        if multiplexing_level := get_multiplexing_level(message):
            self.opening, self.closing = multiplexing_level
        else:
            self.opening, self.closing = '', ''

    def __str__(self):
        return (
            f'<{self.__class__.__name__} id={self.id} '
            f'content={repr(self.content)} '
            f'author={repr(self.author)}>'
        )

    @property
    def is_webhook_message(self):
        return isinstance(self._message, WebhookMessage)

    @cached_property
    def urls(self) -> Sequence[URL]:
        return [
            URL(url) for url in set(self.url_prog.findall(clean_markdown(self.stripped_content)))
        ]

    @property
    def author(self):
        return MultiplexingMessage.webhook_author.get(self.id) or self._message.author

    @author.setter
    def author(self, value):
        pass

    @property
    def stripped_content(self):
        return strip_multiplexing_chars(self.content, self.opening, self.closing)

    def __getattr__(self, name):
        return getattr(self._message, name)

    @cached_property
    def clean_content(self):
        clean_content = strip_multiplexing_chars(
            self._message.clean_content, self.opening, self.closing
        )
        return self.emoji_prog.sub(lambda m: m.group(1), clean_content)

    @cached_property
    def quote_embed(self):
        embed = Embed(
            description=self._message.content,
            color=self._message.author.colour,
            timestamp=self._message.created_at,
        )
        embed.set_author(
            name=self._message.author.display_name,
            icon_url=self._message.author.display_avatar.url,
        )
        bang = '' if self._message.guild is None else '#'
        embed.add_field(
            name=f'{bang}{self._message.channel}',
            value=f'[Jump to message]({self._message.jump_url})',
        )
        if self._message.attachments is not None:
            for att in self._message.attachments:
                if att.content_type is not None and att.content_type.split('/')[0] == 'image':
                    embed.set_image(url=att.url)
                    break
        return embed

    @default_backoff
    async def send(self, content=None, *args, **kwargs):
        if content is not None:
            content = f'{self.opening}{content}{self.closing}'

        return MultiplexingMessage(await self.channel.send(content, *args, **kwargs))

    @default_backoff
    async def reply(self, content=None, *args, **kwargs):
        if content is not None:
            content = f'{self.opening}{content}{self.closing}'

        return MultiplexingMessage(await self._message.reply(content, *args, **kwargs))

    @default_backoff
    async def edit(self, content=None, *args, **kwargs):
        if content is not None:
            content = f'{self.opening}{content}{self.closing}'

        return await self._message.edit(*args, content=content, **kwargs)

    @default_backoff
    async def delete(self, *args, **kwargs):
        return await self._message.delete(*args, **kwargs)

    @default_backoff
    async def pin(self, *args, **kwargs):
        return await self._message.pin(*args, **kwargs)

    @default_backoff
    async def unpin(self, *args, **kwargs):
        return await self._message.unpin(*args, **kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__} _message={self._message!r}>'


class ChannelListener(metaclass=abc.ABCMeta):
    def __init__(self, bot, channel: TextChannel | PrivateChannel):
        self.bot = bot
        self.channel = channel
        self.bot.register_channel_listener(self.channel.id, self)

    def unregister(self):
        self.bot.unregister_channel_listener(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.unregister()

    @abc.abstractmethod
    async def on_message(self, message: Message):
        pass


timestamp_re = re.compile(r'<t:(\d+)(:[a-z]?)?>', re.IGNORECASE)


async def timestamp_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[discord.app_commands.Choice[str]]:
    dt = parse_timestamp(current)
    ts = f'<t:{int(dt.timestamp())}:f>'
    return [
        discord.app_commands.Choice(
            name=dt.astimezone(tz=TZ).strftime('%a %d %b %Y at %H:%M %Z'), value=ts
        )
    ]


def parse_timestamp(time_str: str) -> datetime.datetime:
    if parsed_ts := timestamp_re.search(time_str):
        return datetime.datetime.fromtimestamp(float(parsed_ts.group(1)), tz=datetime.UTC)
    else:
        # fallback for text
        cal = pdt.Calendar()
        try:
            holdTime = cal.parse(time_str, datetime.datetime.now(TZ))
        except (ValueError, OverflowError):
            # year too long
            holdTime = cal.parse('9999-12-31')

        if holdTime[1] == 0:
            raise BadArgument(f'Could not parse "{time_str}" as a valid time')

        return datetime.datetime(*(holdTime[0])[:6], tzinfo=TZ)


class WebhookMessage:
    def __init__(self, message: Message, webhook: Webhook | WebhookProxy):
        self.message = message
        self.webhook = webhook

    def __getattr__(self, key):
        return getattr(self.message, key)

    @default_backoff
    async def edit(self, **fields):
        await self.webhook.edit_message(self.message.id, **fields)

    async def _delete(self):
        assert isinstance(self.message.channel, discord.abc.GuildChannel)
        await self.message.channel.delete_messages([self.message])

    async def _delete_with_delay(self, delay: float):
        await asyncio.sleep(delay)
        with suppress(HTTPException):
            await self._delete()

    @default_backoff
    async def delete(self, *, delay: float | None = None):
        if delay is None:
            await self._delete()
        else:
            asyncio.create_task(self._delete_with_delay(delay))


class WebhookProxy:
    def __init__(self, webhook: Webhook | WebhookProxy):
        self.webhook = webhook

    def __getattr__(self, key):
        return getattr(self.webhook, key)

    @default_backoff
    async def send(self, wait=True, **kwargs) -> discord.WebhookMessage:
        return await self.webhook.send(wait=True, **kwargs)


class UserWebhook(WebhookProxy):
    def __init__(
        self,
        webhook: Webhook | WebhookProxy,
        user: discord.User | None = None,
        display_name: str | None = None,
        display_avatar: str | None = None,
        **kwargs,
    ):
        super().__init__(webhook, **kwargs)
        self.user = user
        self.display_name = None
        self.display_avatar = None

        if user is not None:
            self.display_name = user.display_name
            self.display_avatar = user.display_avatar.url
        if display_name is not None:
            self.display_name = display_name
        if display_avatar is not None:
            self.display_avatar = display_avatar

    async def send(self, wait=True, **kwargs):
        display_name = self.display_name

        kwargs.setdefault('username', display_name)
        if self.display_avatar is not None:
            kwargs.setdefault('avatar_url', self.display_avatar)

        sent = await super().send(wait=wait, **kwargs)

        if self.user is not None:
            MultiplexingMessage.webhook_author[sent.id] = self.user
            sent.author = self.user

        return sent


class AMQWebhook(UserWebhook):
    def __init__(self, webhook: Webhook | WebhookProxy, private: bool, **kwargs):
        self.private = private
        super().__init__(webhook, **kwargs)

    @property
    def display_name(self):
        return self._display_name

    @display_name.setter
    def display_name(self, value: str):
        prefix = '[AMQ – Private]' if self.private else '[AMQ]'
        self._display_name = f'{prefix} {value}'

    async def send(self, wait=True, **kwargs):
        return cast(DpyWebhookMessage, AMQMessage(await super().send(wait=wait, **kwargs)))


class ThreadWebhook(WebhookProxy):
    def __init__(self, webhook: Webhook | WebhookProxy, thread: Thread, **kwargs):
        super().__init__(webhook, **kwargs)
        self.thread = thread

    async def send(self, wait=True, **kwargs):
        kwargs.setdefault('thread', self.thread)
        return await super().send(wait=wait, **kwargs)


class BananasWebhook(WebhookProxy):
    def __init__(self, webhook: Webhook | WebhookProxy, **kwargs):
        super().__init__(webhook, **kwargs)

    def _bananas(self, message: str):
        new_message = ':banana:'

        i = 1
        while i < len(message):
            j = random.randint(3, 5)
            new_message += message[i : i + j] + ':banana:'
            i += j + 1

        return new_message

    async def send(self, wait=True, *, content: str | None, **kwargs):
        if content:
            if multiplexing_level := get_multiplexing_level(content):
                opening, closing = multiplexing_level
            else:
                opening, closing = '', ''
            content = self._bananas(strip_multiplexing_chars(content, opening, closing))
            kwargs['content'] = content

        return await super().send(wait=wait, **kwargs)


class WaifuWebhook(WebhookProxy):
    def __init__(
        self,
        webhook: Webhook | WebhookProxy,
        chara,
        display_name: str,
        hide_author: bool = False,
        **kwargs,
    ):
        super().__init__(webhook, **kwargs)
        self.chara = chara
        self.display_name = display_name
        self.hide_author = hide_author

    async def send(self, wait=True, **kwargs):
        await self.chara.load_alchara()

        username = f'{self.chara.alchara.name.userPreferred}'
        if not self.hide_author:
            username += f' — {self.display_name}'

        kwargs.setdefault('username', username)
        kwargs.setdefault('avatar_url', self.chara.alchara.image.large)

        return await super().send(wait=wait, **kwargs)


class ReplyWebhook(WebhookProxy):
    def __init__(
        self, webhook: Webhook | WebhookProxy, message: Message | MultiplexingMessage, **kwargs
    ):
        super().__init__(webhook, **kwargs)
        self.message = message

    async def send(self, wait=True, **kwargs):
        allowed_mentions = AllowedMentions(
            users=self.message.mentions,
            roles=self.message.role_mentions,
            everyone=self.message.mention_everyone,
        )

        if self.message.reference is not None and (replied := self.message.reference.resolved):
            replied = MultiplexingMessage(replied)
            content = f'> **{replied.author.mention}** {replied.jump_url}'
            msg_content = kwargs.get('content')
            if msg_content is not None:
                content += '\n' + msg_content
            kwargs['content'] = content

            user_mentions = list(set((*self.message.mentions, replied.author)))
            allowed_mentions = AllowedMentions(
                users=user_mentions,
                roles=self.message.role_mentions,
                everyone=self.message.mention_everyone,
            )

        kwargs.setdefault('allowed_mentions', allowed_mentions)
        return await super().send(wait=wait, **kwargs)


class StickerWebhook(WebhookProxy):
    def __init__(self, webhook: Webhook | WebhookProxy, stickers: list[StickerItem], **kwargs):
        super().__init__(webhook, **kwargs)
        self.stickers = stickers

    async def send(self, wait=True, **kwargs):
        if self.stickers:
            stickers = '\n'.join(s.url for s in self.stickers)

            content = kwargs.get('content')
            if content:
                content += '\n' + stickers
            else:
                content = stickers

            kwargs['content'] = content

        return await super().send(wait=wait, **kwargs)


class AttachmentsWebhook(WebhookProxy):
    def __init__(self, webhook: Webhook | WebhookProxy, attachments, **kwargs):
        super().__init__(webhook, **kwargs)
        self.attachments = attachments

    async def send(self, wait=True, **kwargs):
        files = await asyncio.gather(*[a.to_file() for a in self.attachments])
        kwargs.setdefault('files', files)

        return await super().send(wait=wait, **kwargs)


class CheckEmptyWebhook(WebhookProxy):
    async def send(self, wait=True, **kwargs):
        content = kwargs.get('content')
        files = kwargs.get('files')
        if not (content or files):
            kwargs['content'] = '\u200b'

        return await super().send(wait=wait, **kwargs)


def typing(func):
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        async with ctx.typing():
            await func(self, ctx, *args, **kwargs)

    return wrapper


@dataclass
class AMQMessage:
    message: discord.WebhookMessage
    amqed: bool = True

    def __getattr__(self, key):
        return getattr(self.message, key)


member_converter = MemberConverter()


class MembersTransformer(app_commands.Transformer):
    split_reg = re.compile(r'(<@!?\d+>)|"([^"]*)"|([^\s"]+)')

    async def transform(
        self, interaction: discord.Interaction[discord.Client], value: str
    ) -> list[discord.Member]:
        interaction = cast(discord.Interaction['Bot'], interaction)
        ctx = await commands.Context.from_interaction(interaction)
        values = (match.group(1) for match in self.split_reg.finditer(value))
        return [await member_converter.convert(ctx, v) for v in values]


Members = app_commands.Transform[list[discord.Member], MembersTransformer]


T = TypeVar('T')


def get_option(
    interaction: discord.Interaction, name: str, cast_func: Callable[[Any], T] = str
) -> T | None:
    if interaction.data is not None and 'options' in interaction.data:
        for option in interaction.data.get('options', []):
            logger.info(f'{option=}')
            return _iter_opt(name, cast_func, option)


def _iter_opt(name, cast_func, option):
    for opt in option.get('options', []):
        if opt['name'] == name and (val := opt.get('value')) is not None:
            logger.info(opt)
            return cast_func(val)
        elif 'options' in opt:
            return _iter_opt(name, cast_func, opt)


UserType = discord.User | discord.Member
