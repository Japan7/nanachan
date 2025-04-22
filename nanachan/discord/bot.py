import asyncio
import logging
import random
import re
import signal
from collections.abc import Coroutine, Sequence
from contextlib import suppress
from functools import partial
from operator import itemgetter as get
from pathlib import Path
from typing import Any, Callable, Literal, cast, override

from discord import (
    AllowedMentions,
    Client,
    Emoji,
    ForumChannel,
    Guild,
    Intents,
    Interaction,
    Member,
    Message,
    NotFound,
    RawReactionActionEvent,
    TextChannel,
    Thread,
    VoiceChannel,
    Webhook,
)
from discord import utils as dutils
from discord.abc import MISSING, Snowflake
from discord.app_commands.errors import AppCommandError
from discord.errors import IHateThe3SecondsTimeout
from discord.ext import commands
from discord.ext.commands import Context, Paginator
from discord.ext.commands.errors import ExtensionError, ExtensionNotLoaded
from watchfiles import Change, awatch
from watchfiles.filters import PythonFilter

import nanachan.extensions
from nanachan.discord.cog import Cog, NanaGroupCog
from nanachan.discord.help import CustomHelpCommand
from nanachan.discord.helpers import (
    ChannelListener,
    Embed,
    MultiplexingContext,
    WebhookMessage,
    get_multiplexing_level,
)
from nanachan.discord.reactions import ReactionListener, UnregisterListener
from nanachan.extensions import load_extensions
from nanachan.redis.base import get_redis
from nanachan.settings import (
    ANAS_ID,
    BOT_ROOM_ID,
    DEBUG,
    DISABLED_EXTENSIONS,
    ERROR_WEBHOOK,
    FAREWELL_MSG,
    PREFIX,
    TADAIMA,
    WELCOME_BOT,
    WELCOME_MSG,
)
from nanachan.utils.misc import (
    framed_header,
    get_console,
    get_session,
    get_traceback,
    get_traceback_exc,
    get_traceback_str,
    ignore,
    not_none,
)

log = logging.getLogger(__name__)
console = get_console()

PREFIX_REG = re.compile(f'{re.escape(PREFIX)}[a-zA-Z]')
EMOJI_REG = re.compile(r':([^ :]+):')


def get_command_prefix(bot, message):
    if multiplexing_level := get_multiplexing_level(message):
        opening, closing = multiplexing_level
        text = message.content[len(opening) : -len(closing)]
    else:
        text = message.content
        opening, closing = '', ''

    if not PREFIX_REG.match(text):
        return opening + PREFIX + 'a'
    return opening + PREFIX


class Bot(commands.AutoShardedBot):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        self.channel_listeners: dict[int, set[ChannelListener]] = {}
        self.reaction_listeners: dict[int, ReactionListener] = {}
        self._cogs: dict[str, commands.Cog] = {}
        self.commands_ready = asyncio.Event()

        super().__init__(
            command_prefix=get_command_prefix,
            intents=intents,
            description=framed_header('Nana-chan commands manual'),
            help_command=CustomHelpCommand(help='Show this message'),
            allowed_mentions=AllowedMentions(everyone=False, roles=False),
            case_insensitive=True,
        )
        self.tree.error(self.on_app_command_error)

    async def start(self, token: str, *, reconnect: bool = True):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, loop.stop)
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

        self.extension_errors = await load_extensions(self)
        await super().start(token, reconnect=reconnect)

    def get_channel_type[T](self, channel_id: int, channel_type: type[T]) -> T | None:
        text_channel = self.get_channel(channel_id)
        assert isinstance(text_channel, channel_type)
        return text_channel

    async def fetch_channel_type[T](self, channel_id: int, channel_type: type[T]) -> T:
        text_channel = await self.fetch_channel(channel_id)
        assert isinstance(text_channel, channel_type)
        return text_channel

    def get_text_channel(self, channel_id: int):
        return not_none(self.get_channel_type(channel_id, TextChannel))

    async def fetch_text_channel(self, channel_id: int):
        return await self.fetch_channel_type(channel_id, TextChannel)

    def get_voice_channel(self, channel_id: int):
        return not_none(self.get_channel_type(channel_id, VoiceChannel))

    async def fetch_voice_channel(self, channel_id: int):
        return await self.fetch_channel_type(channel_id, VoiceChannel)

    def get_thread(self, channel_id: int):
        return not_none(self.get_channel_type(channel_id, Thread))

    async def fetch_thread(self, channel_id: int):
        return await self.fetch_channel_type(channel_id, Thread)

    def get_bot_room(self) -> TextChannel:
        return not_none(self.get_channel_type(BOT_ROOM_ID, channel_type=TextChannel))

    async def close(self):
        if TADAIMA:
            bot_room = self.get_bot_room()
            await bot_room.send('アップデイトがあるから、ちょっと待ってね :wink:')

        redis = await get_redis()
        if redis:
            await redis.close()

        await super().close()

    async def on_command(self, ctx):
        log.info(f'{ctx.message.author} used `{ctx.view.buffer}`')

    async def send_error(
        self,
        error_msg: str,
        reply: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
        itai: bool = True,
    ):
        if reply is None:
            bot_room = self.get_channel(BOT_ROOM_ID)
            assert isinstance(bot_room, TextChannel)
            reply = bot_room.send
            message = 'いたい！ :confounded:'
        else:
            message = 'ごめんなさい！ :confounded:'

        assert reply is not None

        if ERROR_WEBHOOK is None:
            webhook_reply = None
        else:
            assert self.user is not None
            webhook = Webhook.from_url(ERROR_WEBHOOK, session=get_session())
            webhook_reply = partial(
                webhook.send,
                wait=True,
                username=self.user.display_name,
                avatar_url=self.user.display_avatar.url,
            )

        try:
            assert reply is not None
            if itai:
                await reply(message)
                if webhook_reply is not None:
                    await webhook_reply(message)

            paginator = Paginator(max_size=2000)

            for l in error_msg.split('\n'):
                paginator.add_line(l)

            for page in paginator.pages:
                if DEBUG:
                    await reply(page)
                if webhook_reply is not None:
                    await webhook_reply(page)

        except Exception:
            await self.send_error(error_msg)

    async def extract_error(self, error: Exception):
        error_trace = await self.loop.run_in_executor(None, get_traceback, error)
        error_msg = await self.loop.run_in_executor(None, get_traceback_str, error_trace)
        await self.loop.run_in_executor(None, console.print, error_trace)
        return error_msg

    async def on_command_error(self, ctx, error, force=False):
        if not force and hasattr(getattr(ctx, 'command', None), 'on_error'):
            return

        if isinstance(error, commands.CommandError) and not isinstance(
            error, commands.CommandInvokeError
        ):
            try:
                await ctx.reply(error)
            except Exception:
                await ctx.send(error)

            if isinstance(error, commands.UserInputError):
                await ctx.send_help(ctx.command)
        else:
            error_msg = await self.extract_error(error)
            if not isinstance(error, IHateThe3SecondsTimeout):
                await self.send_error(error_msg, ctx)

    async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
        error_msg = await self.extract_error(error)
        if interaction.response.is_done():
            interaction_reply = interaction.followup.send
        else:
            interaction_reply = interaction.response.send_message

        await self.send_error(error_msg, interaction_reply)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any):
        trace = get_traceback_exc()
        error_msg = get_traceback_str(trace)
        console.print(f'Ignoring exception in "{event_method}"', trace, sep='\n')
        await self.send_error(error_msg)

    async def on_member_join(self, member):
        if not WELCOME_MSG:
            return

        if member.bot and WELCOME_BOT:
            msg = WELCOME_BOT.format(member=member)
        else:
            msg = WELCOME_MSG.format(member=member)

        guild = member.guild
        if guild.system_channel is not None:
            embed = Embed(title=msg)
            await guild.system_channel.send(embed=embed)

    async def on_member_remove(self, member: Member):
        if not FAREWELL_MSG:
            return

        if member.bot:
            return

        guild = member.guild
        if guild.system_channel is not None:
            embed = Embed(title=FAREWELL_MSG.format(member=member))
            await guild.system_channel.send(embed=embed)

    async def on_ready(self):
        await self.sync_commands()
        log.info('Ready')

        while self.extension_errors:
            report_error = self.extension_errors.pop()
            await report_error

        # Cog hot reload
        if DEBUG:
            ext_path = Path(nanachan.extensions.__file__).parent
            async for changes in awatch(ext_path, watch_filter=PythonFilter()):
                for change in changes:
                    path = Path(change[1])
                    extension = path.stem

                    if any(
                        (
                            path.is_dir(),
                            extension.startswith('_'),
                            extension.startswith('.'),
                            extension in DISABLED_EXTENSIONS,
                        )
                    ):
                        continue

                    module_name = f'nanachan.extensions.{extension}'

                    try:
                        with suppress(ExtensionNotLoaded):
                            await self.unload_extension(module_name)
                            log.info(f"Extension '{module_name}' unloaded ({change[0].name})")

                        if change[0] != Change.deleted:
                            await self.load_extension(module_name)
                            log.info(f"Extension '{module_name}' loaded ({change[0].name})")
                    except ExtensionError as e:
                        log.exception(e)

                log.info('Reloading application commands...')
                await self.sync_commands()
                log.info('Finished reloading application commands')

    async def sync_commands(self):
        log.info('syncing global commands')
        await self.tree.sync()
        async for guild in self.fetch_guilds():
            log.info(f'syncing commands in {guild}')
            await self.tree.sync(guild=guild)

    async def invoke(self, ctx: MultiplexingContext):  # type: ignore # trust me bro
        try:
            if ctx.webhooked:
                ctx = await self.webhook_message(ctx)

            await ctx.wait()
            self.dispatch('user_message', ctx)

            if ctx.bananased:
                return

        except Exception as e:
            trace = get_traceback(e)
            msg = get_traceback_str(trace) + f'\n{ctx.message}'
            await self.send_error(msg)
            raise

        await super().invoke(ctx)

    async def webhook_message(
        self, ctx: MultiplexingContext, content: str | None = None, **kwargs
    ) -> MultiplexingContext:
        if content is None:
            content = ctx.message.content

        webhook = await ctx.get_user_webhook(**kwargs)
        sent = await webhook.send(content=content)

        sent.author = ctx.author
        sent.channel = ctx.channel
        sent = WebhookMessage(sent, webhook)

        delete = ctx.message.delete()
        if DEBUG:
            # we can have several bots deleting the same message
            delete = cast(Coroutine[Any, Any, Any], ignore(NotFound, delete))

        await delete

        new_ctx = await self.get_context(sent)
        return new_ctx

    @property
    def bot_id(self):
        assert self.user is not None
        return self.user.id

    def get_anas(self, guild: Guild):
        return guild.get_member(ANAS_ID)

    async def get_webhook(self, channel: TextChannel | ForumChannel):
        if isinstance(channel, Thread):
            assert channel.parent is not None
            channel = channel.parent

        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.token is not None:
                return webhook

        return await channel.create_webhook(name='bananas')

    @override
    async def add_cog(
        self,
        cog: commands.Cog,
        *,
        override: bool = False,
        guild: Snowflake | None = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
    ):
        if isinstance(cog, (Cog, NanaGroupCog)):
            if cog.__required_settings__ is not None and not cog.__required_settings__:
                log.warning(
                    f'{cog.__class__.__name__} is not configured properly and won’t be initialised'
                )
                return
        else:
            log.debug(f'{cog.__class__.__name__} is not an instance of {Cog.__name__}')

        await super().add_cog(cog, override=override, guild=guild, guilds=guilds)
        self._cogs[cog.qualified_name.casefold()] = cog

    @override
    def get_cog(self, name: str) -> commands.Cog | None:
        name = name.casefold()
        if name in self._cogs:
            return self._cogs[name]

        for key, cog in sorted(self._cogs.items(), key=get(0)):
            if all(c1 == c2 for c1, c2 in zip(name, key)):
                return cog

    async def register_reaction_listener(
        self, message_id: int, reaction_listener: ReactionListener
    ):
        if old_listener := self.reaction_listeners.get(message_id):
            reactions_old = list(old_listener.get_cls_handlers()['add'].keys())
            reactions_new = list(reaction_listener.get_cls_handlers()['add'].keys())
            if reactions_old != reactions_new:
                await self.reaction_listeners[message_id].unregister()

        self.reaction_listeners[message_id] = reaction_listener
        await reaction_listener.add_reactions()

    async def unregister_reaction_listener(self, message_id: int) -> None:
        if listener := self.reaction_listeners.pop(message_id, None):
            if not listener._done.done():
                listener.unregister()
            await listener.clear_reactions()

    async def _on_raw_reaction(
        self, payload: RawReactionActionEvent, action: Literal['add', 'remove']
    ):
        if reaction_listener := self.reaction_listeners.get(payload.message_id):
            await reaction_listener.on_reaction(payload, action)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self._on_raw_reaction(payload, 'add')

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self._on_raw_reaction(payload, 'remove')

    async def on_raw_message_delete(self, payload: RawReactionActionEvent):
        if listener := self.reaction_listeners.get(payload.message_id, None):
            listener.unregister()

    def get_nana_emoji(self, name: str) -> Emoji | None:
        if name == 'saladedefruits' and random.random() <= 0.05:
            name = 'slddfrts'

        for guild in self.guilds:
            if emoji := dutils.get(guild.emojis, name=name):
                return emoji

    def get_emoji_str(self, name: str) -> str:
        if emoji := self.get_nana_emoji(name):
            return str(emoji)
        else:
            return f':{name}:'

    def get_emojied_str(self, content: str) -> str:
        return EMOJI_REG.sub(lambda m: self.get_emoji_str(m.group(1)), content)

    @override
    async def get_context[T: Context[Bot]](
        self,
        message: Message | WebhookMessage | Interaction[Client],
        *,
        cls: type[T] = MultiplexingContext,
    ) -> T:
        return await super().get_context(message, cls=cls)  # type: ignore

    @override
    async def on_message(self, message: Message):
        if listeners := self.channel_listeners.get(message.channel.id):
            for listener in listeners.copy():
                try:
                    await listener.on_message(message)
                except UnregisterListener:
                    self.unregister_channel_listener(listener)

        await super().on_message(message)

    def register_channel_listener(self, channel_id: int, listener: ChannelListener):
        self.channel_listeners.setdefault(channel_id, set())
        self.channel_listeners[channel_id].add(listener)

    def unregister_channel_listener(self, listener: ChannelListener):
        self.channel_listeners[listener.channel.id].remove(listener)
