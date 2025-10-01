import asyncio
import bisect
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from importlib import resources
from operator import attrgetter
from random import choice
from typing import MutableSequence, Optional, Union

import discord
import parsedatetime.parsedatetime as pdt
from discord import (
    AllowedMentions,
    File,
    Guild,
    Interaction,
    Member,
    Message,
    NotFound,
    PartialEmoji,
    PrivacyLevel,
    Reaction,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
    app_commands,
)
from discord.abc import Messageable
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import MISSING
from pydantic_ai import Agent

import nanachan.resources
from nanachan.discord.application_commands import (
    LegacyCommandContext,
    handle_command_errors,
    legacy_command,
    nana_command,
)
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import ChannelListener, Embed, MultiplexingMessage, getEmojiStr
from nanachan.discord.views import AutoNavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    NewReminderBody,
    ReminderInsertSelectResult,
    ReminderSelectAllResult,
)
from nanachan.settings import AI_LOW_LATENCY_MODEL, SLASH_PREFIX, TZ, RequiresAI
from nanachan.utils.ai import get_model
from nanachan.utils.misc import get_session, saucenao_lookup, tldr_get_page

logger = logging.getLogger(__name__)


class MovingChannel(ChannelListener):
    async def on_message(self, message):
        if not message.author.bot:
            await message.delete()


class BasicCommands(Cog, name='Basic Commands'):
    """Commands that we have no idea were to put"""

    emoji = '🗨'

    quote_emoji = b'\xf0\x9f\x94\x97'.decode()

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.to_be_quoted_messages: dict[int, Message] = {}  # {user_id: (channel_id, message_id)}
        self.reminders_processor_task = None
        self.reminders_processor_task_sleep = None
        self.reminders: MutableSequence[ReminderSelectAllResult | ReminderInsertSelectResult] = []
        self.agent = Agent()

    @Cog.listener()
    async def on_ready(self):
        resp = await get_nanapi().reminder.reminder_get_reminders()
        if not success(resp):
            raise RuntimeError(resp.result)
        reminders = resp.result
        logger.info(f'reminders:{len(reminders)} reminders enqueued')
        self.reminders = sorted(reminders, key=attrgetter('timestamp'))

        if not self.reminders_processor_task:
            self.reminders_processor_task_done = False
            self.reminders_processor_task = asyncio.create_task(self.reminders_processor())

    async def cog_unload(self):
        self.reminders_processor_task_done = True
        if self.reminders_processor_task_sleep:
            self.reminders_processor_task_sleep.cancel()

    async def _reminders_processor(self):
        now = datetime.now(tz=TZ)
        sleep_time = 7200

        if not self.reminders:
            logger.info('no reminders to process')

        elif self.reminders[0].timestamp <= now:
            past_reminder = self.reminders.pop(0)
            channel = self.bot.get_channel_type(int(past_reminder.channel_id), Messageable)
            if channel is None:
                channel = self.bot.get_bot_room()

            reminder_message = f'<@{past_reminder.user.discord_id}>! Just a reminder!'
            if past_reminder.message:
                reminder_message += f' {past_reminder.message}!'
            await channel.send(reminder_message)
            resp = await get_nanapi().reminder.reminder_delete_reminder(past_reminder.id)
            if not success(resp):
                raise RuntimeError(resp.result)
            sleep_time = 0

        else:
            time_to_reminder = (self.reminders[0].timestamp - now).total_seconds()
            sleep_time = min(time_to_reminder, sleep_time)

        logger.info(f'reminder:wait for {sleep_time}s')
        self.reminders_processor_task_sleep = asyncio.create_task(asyncio.sleep(sleep_time))
        try:
            await self.reminders_processor_task_sleep
        except asyncio.CancelledError:
            pass

    async def reminders_processor(self):
        while not self.reminders_processor_task_done:
            try:
                await self._reminders_processor()
            except Exception as e:
                logger.exception(e)

    async def _get_embed_for_quote(self, ctx):
        pinned_message = MultiplexingMessage(self.to_be_quoted_messages[ctx.author.id])
        return pinned_message.quote_embed

    @nana_command(name='quote', description='Quote a previously selected message')
    async def slash_quote(self, interaction: Interaction[Bot]):
        ctx = await Context.from_interaction(interaction)
        try:
            embed = await self._get_embed_for_quote(ctx)
            await ctx.send(embed=embed)
            del self.to_be_quoted_messages[ctx.author.id]
        except KeyError:
            await ctx.send('You must link a message first (by right clicking)')
        except NotFound:
            await ctx.send('The quoted message has been deleted')

    @nana_command(description='Pay respect')
    @app_commands.guild_only()
    @app_commands.describe(what='What to put your respect on')
    @legacy_command()
    async def respect(self, ctx: LegacyCommandContext, *, what: str | None = None):
        if what is None:
            content = 'Press F to pay respect'
        else:
            content = f'Put some respect for {what}'

        message = await ctx.send(content)
        await message.add_reaction(b'\xf0\x9f\x87\xab'.decode())

    @nana_command()
    @app_commands.guild_only()
    @app_commands.describe(message='message to send')
    async def say(self, interaction: Interaction[Bot], message: str = '42'):
        """Make me say something for you"""
        await interaction.response.defer(ephemeral=True)
        ctx = await Context.from_interaction(interaction)

        await ctx.channel.send(message, allowed_mentions=AllowedMentions.none())
        await interaction.followup.send(content='Message sent succesfully', ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        user = self.bot.get_user(payload.user_id)
        assert user is not None
        if user.bot:
            return

        emoji = payload.emoji
        if str(emoji) == self.quote_emoji:
            channel = self.bot.get_channel(payload.channel_id)
            assert isinstance(channel, TextChannel | Thread | VoiceChannel)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(emoji, user)
            self.to_be_quoted_messages[user.id] = message

    @nana_command(description='HASHIRE SORI YO KAZE NO YOU NI TSUKIMIHARA WO')
    @app_commands.guild_only()
    async def padoru(self, interaction: Interaction[Bot]):
        with resources.path(
            nanachan.resources, choice(['padoru.png', 'padoru_blush.png'])
        ) as path:
            await interaction.response.send_message(file=File(path))

    @commands.has_permissions(manage_messages=True)
    @commands.command(usage='<destination> <start_msg> [end_msg] [members]')
    async def move(
        self, ctx, destination: TextChannel, start_msg: Message, end_msg: Optional[Message] = None
    ):
        """Move entire connversations to another text channel

        It will move all messages from @mentions (everybody if unspecified), after the provided
        start_msg **included**, up to end_msg **included**, to #destination.
        If end_msg_id is omitted, moves all the messages from start_msg to the latest message.
        """
        if ctx.channel == destination:
            raise commands.CommandError("You can't move messages to the same channel.")

        async with ctx.channel.typing():
            webhook = await self.bot.get_webhook(destination)
            start_id = discord.Object(start_msg.id - 1)
            if end_msg is not None:
                end_id = discord.Object(end_msg.id + 1)
            else:
                end_id = ctx.message

            mentions = ctx.message.mentions

            async with ctx.channel.typing():
                async with destination.typing():
                    with MovingChannel(self.bot, destination):
                        async for message in ctx.channel.history(
                            limit=None, after=start_id, before=end_id, oldest_first=True
                        ):
                            if not mentions or (message.author in mentions):
                                try:
                                    content = message.content
                                except Exception:
                                    content = MISSING
                                try:
                                    file = await message.attachments[0].to_file()
                                except Exception:
                                    file = MISSING

                                if isinstance(destination, Thread):
                                    thread = destination
                                else:
                                    thread = MISSING

                                self.bot.loop.create_task(message.delete())
                                await webhook.send(
                                    content=content,
                                    embeds=message.embeds,
                                    file=file,
                                    username=message.author.display_name,
                                    avatar_url=message.author.display_avatar.url,
                                    wait=True,
                                    thread=thread,
                                )

                await ctx.message.delete()

    @nana_command()
    @app_commands.guild_only()
    async def janken(
        self,
        interaction: Interaction[Bot],
        player1: discord.User,
        player2: discord.User | discord.Member | None = None,
    ):
        """Start a janken game between two members."""
        ctx = await Context.from_interaction(interaction)
        if player2 is None:
            player2 = ctx.author

        assert player2 is not None

        await ctx.send('Janken started! *Please check your DMs now!*')

        shapes = ('✊', '✋', '✌️')
        embed = Embed(description='Choose your side!')

        async def get_choice(player: User | Member):
            message = await player.send(embed=embed)
            for shape in shapes:
                await message.add_reaction(shape)

            def check(reaction: Reaction, user: Member | User):
                return (
                    reaction.message == message
                    and user == player
                    and str(reaction.emoji) in shapes
                )

            reaction, _ = await self.bot.wait_for('reaction_add', timeout=30, check=check)
            return reaction

        try:
            choices = await asyncio.gather(get_choice(player1), get_choice(player2))
            resp = (
                '\n'.join(
                    f'{player} chose {choice}'
                    for player, choice in zip([player1, player2], choices)
                )
                + '\n\n'
            )

            choice1, choice2 = map(shapes.index, map(str, choices))

            if choice1 == choice2:
                resp += f"**It's a tie! {getEmojiStr(ctx, 'amoesip')}**"
            elif (choice1 - choice2) in (-1, 2):
                resp += f'**{player2.mention} won! {getEmojiStr(ctx, "chousen")}**'
            elif (choice1 - choice2) in (1, -2):
                resp += f'**{player1.mention} won! {getEmojiStr(ctx, "chousen")}**'

        except asyncio.TimeoutError:
            emoji = getEmojiStr(ctx, 'ChrisDespair')
            resp = f'janken is cancelled {emoji}'

        await ctx.send(resp)

    @commands.command(aliases=['url', 'avatar', 'pfp', 'pp'])
    async def link(
        self, ctx: commands.Context, user_or_emoji: User | PartialEmoji | Guild | None = None
    ):
        """Get one user avatar/guild icon or custom emoji link."""
        if isinstance(user_or_emoji, Guild):
            assert user_or_emoji.icon is not None
            await ctx.reply(user_or_emoji.icon.url)
        elif isinstance(user_or_emoji, PartialEmoji):
            await ctx.reply(user_or_emoji.url)
        else:
            await ctx.reply((user_or_emoji or ctx.author).display_avatar.url)

    @commands.has_permissions(manage_emojis=True)
    @commands.command(name='import')
    async def emoji_import(
        self, ctx: commands.Context, emoji: Union[PartialEmoji, str], name: str | None = None
    ):
        """Import a custom emoji."""
        if isinstance(emoji, PartialEmoji):
            image = await emoji.read()
            name = name or emoji.name
        else:
            if name is None:
                raise commands.CommandError('Name is required.')
            async with get_session().get(emoji) as resp:
                image = await resp.read()

        try:
            assert ctx.guild is not None
            imported = await ctx.guild.create_custom_emoji(name=name, image=image)
            await ctx.reply(str(imported))
        except Exception:
            raise commands.CommandError('Only JPEG, PNG, and GIF are supported.')

    @nana_command(name='tldr', description='Show the tl;dr page of a terminal command')
    @legacy_command()
    async def tldr(self, ctx: LegacyCommandContext, command_name: str):
        page = await tldr_get_page(command_name)
        if page:
            embed = Embed(title=command_name, description=page)
            await ctx.reply(embed=embed)
        else:
            raise commands.CommandError(f'No tl;dr page found for {command_name}.')

    @nana_command(description='Make me remind you something in the future')
    @app_commands.guild_only()
    @app_commands.describe(time='Reminder time', message='Reminder description')
    async def remindme(self, interaction: Interaction, time: str, message: str):
        cal = pdt.Calendar()
        try:
            holdTime = cal.parse(time, datetime.now(TZ))
        except (ValueError, OverflowError):
            # year too long
            holdTime = cal.parse('9999-12-31')
        if holdTime[1] == 0:
            # parsing failed
            await interaction.response.send_message(
                f'Could not parse "{time}" as a valid time', ephemeral=True
            )
            return

        dt = datetime(*(holdTime[0])[:6], tzinfo=TZ)
        assert interaction.channel_id is not None
        resp = await get_nanapi().reminder.reminder_new_reminder(
            NewReminderBody(
                discord_id=str(interaction.user.id),
                discord_username=str(interaction.user),
                channel_id=str(interaction.channel_id),
                message=message,
                timestamp=dt,
            )
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        reminder = resp.result
        bisect.insort(self.reminders, reminder, key=attrgetter('timestamp'))
        if self.reminders_processor_task_sleep:
            self.reminders_processor_task_sleep.cancel()

        await interaction.response.send_message(
            f'Reminder "{message}" set for {dt}', ephemeral=True
        )

    @commands.has_permissions(administrator=True)
    @commands.command()
    async def prune(self, ctx: commands.Context, amount: int):
        """Prune messages from a channel."""
        assert isinstance(ctx.channel, TextChannel | VoiceChannel | Thread)
        await ctx.channel.purge(limit=amount)
        await ctx.send(f'{amount} messages pruned.')

    @nana_command()
    @app_commands.guild_only()
    async def now(self, interaction: Interaction, name: str, description: str | None = None):
        """Start an online event now"""
        assert interaction.channel is not None
        guild = interaction.channel.guild
        assert guild is not None

        member = await guild.fetch_member(interaction.user.id)
        if member.voice is None:
            await interaction.response.send_message(
                'You must be in a voice channel to start an event.'
            )
            return

        voice_ch = member.voice.channel
        assert voice_ch is not None

        event = await guild.create_scheduled_event(
            name=name,
            channel=voice_ch,
            start_time=discord.utils.utcnow() + timedelta(hours=1),
            description=description or '',
            privacy_level=PrivacyLevel.guild_only,
        )

        try:
            await event.start(reason='/now')
            await interaction.response.send_message(
                f'[*{event.name}*]({event.url}) started in {voice_ch.mention}.'
            )
        except Exception:
            await event.delete()
            raise

    @nana_command()
    @app_commands.guild_only()
    async def active_threads(self, interaction: Interaction):
        assert interaction.guild
        await interaction.response.defer()
        all_user_threads = [
            t
            for t in await interaction.guild.active_threads()
            if isinstance(t.parent, TextChannel) and t.owner and not t.owner.bot
        ]
        all_summary = await asyncio.gather(*[self.get_thread_summary(t) for t in all_user_threads])
        all_summary_dict = {t.id: summary for t, summary in all_summary}
        per_chan = defaultdict[TextChannel, list[Thread]](list)
        for t in all_user_threads:
            assert isinstance(t.parent, TextChannel)
            per_chan[t.parent].append(t)
        embed = Embed(title='Active threads')
        for chan, threads in sorted(per_chan.items(), key=lambda x: x[0].position):
            values = []
            for t in sorted(threads, key=lambda x: x.created_at or 0, reverse=True):
                values.append(f'`├─` {t.mention} {all_summary_dict.get(t.id, "")}')
            if values:
                embed.add_field(name=chan.mention, value='\n'.join(values), inline=False)
        await interaction.followup.send(embed=embed)

    async def get_thread_summary(self, thread: Thread) -> tuple[Thread, str]:
        if not RequiresAI.configured:
            return thread, ''
        assert AI_LOW_LATENCY_MODEL
        channel = await thread._state.http.get_channel(thread.id)  # pyright: ignore[reportPrivateUsage]
        messages = await thread._state.http.logs_from(thread.id, limit=50)  # pyright: ignore[reportPrivateUsage]
        resp = await self.agent.run(
            [
                'Given this channel informations and the last 50 messages, '
                'give a very short summary in a single sentence of what this thread is about.',
                json.dumps(channel, default=str),
                json.dumps(messages, default=str),
            ],
            model=get_model(AI_LOW_LATENCY_MODEL),
        )
        return thread, resp.output.replace('\n', ' ').strip()


def message_quote(cog: BasicCommands):
    @app_commands.context_menu(name='Quote')
    async def message_quote_menu(interaction: Interaction, message: Message):
        cog.to_be_quoted_messages[interaction.user.id] = message
        await interaction.response.send_message(
            f'Message selected, use `/{SLASH_PREFIX}quote` to quote it somewhere else',
            ephemeral=True,
        )

    return message_quote_menu


@app_commands.context_menu(name='SauceNAO')
@app_commands.guild_only
@handle_command_errors
async def cmd_saucenao(interaction: Interaction[Bot], message: Message):
    """Get the SauceNAO results of an image or message"""
    await interaction.response.defer(thinking=True)

    if message.attachments:
        url = message.attachments[0].url
    else:
        if search := re.search(r'https://[^ ]+', message.clean_content):
            url = search.group(0)
        else:
            raise commands.CommandError('No link found')

    try:
        resp = await saucenao_lookup(url)
    except Exception as e:
        raise commands.CommandError(str(e))

    sauces = [str(sauce) for sauce in resp if sauce.similarity > 50]

    if not sauces:
        raise commands.CommandError('No sauce found')

    ctx = await Context.from_interaction(interaction)
    await AutoNavigatorView.create(
        ctx.bot,
        interaction.followup.send,
        title='SauceNAO results',
        description='\n\n'.join(sauces),
        thumbnail_url=resp[0].thumbnail,
    )


@app_commands.context_menu(name='Avatar link')
async def user_get_avatar(interaction: Interaction, member: Member):
    await interaction.response.send_message(member.display_avatar.url)


async def setup(bot: Bot) -> None:
    cog = BasicCommands(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(message_quote(cog))
    bot.tree.add_command(cmd_saucenao)
    bot.tree.add_command(user_get_avatar)
