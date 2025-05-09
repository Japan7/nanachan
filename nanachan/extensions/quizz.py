import asyncio
import io
import random
import re
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from uuid import UUID

import discord
from discord import Member, app_commands
from discord.app_commands.tree import ALL_GUILDS
from discord.ext import commands

from nanachan.discord.application_commands import LegacyCommandContext, NanaGroup, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import (
    Embed,
    MultiplexingContext,
    MultiplexingMessage,
    context_modifier,
)
from nanachan.discord.views import ConfirmationView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    EndGameBody,
    NewGameBody,
    SetGameBananedAnswerBody,
)
from nanachan.settings import (
    ANIME_QUIZZ_CHANNEL,
    LOUIS_QUIZZ_CHANNEL,
    MANGA_QUIZZ_CHANNEL,
    PREFIX,
    RequiresQuizz,
)
from nanachan.utils.misc import get_session
from nanachan.utils.quizz import COLOR_BANANA, AnimeMangaQuizz, LouisQuizz, QuizzBase


class Quizz(Cog, required_settings=RequiresQuizz):
    """Ask questions and get hints for quizzes"""

    emoji = '🃏'

    slash_quizz = NanaGroup(
        name='quizz',
        guild_ids=[ALL_GUILDS],
        description='Quizz guild commands',
    )
    slash_quizz_answer = app_commands.Group(
        name='answer',
        parent=slash_quizz,
        description='Quizz answer commands',
    )
    slash_quizz_stock = app_commands.Group(
        name='stock',
        parent=slash_quizz,
        description='Quizz stock commands',
    )

    image_prog = re.compile(rf'{re.escape(PREFIX)}ima+ge')

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.quizz_cls: dict[int, QuizzBase] = {
            ANIME_QUIZZ_CHANNEL: AnimeMangaQuizz(self.bot, ANIME_QUIZZ_CHANNEL),
            MANGA_QUIZZ_CHANNEL: AnimeMangaQuizz(self.bot, MANGA_QUIZZ_CHANNEL),
            LOUIS_QUIZZ_CHANNEL: LouisQuizz(self.bot, LOUIS_QUIZZ_CHANNEL),
        }
        self.locks = defaultdict(asyncio.Lock)
        context_modifier(self.image_ctx)

    async def image_ctx(self, ctx):
        if self.image_prog.match(ctx.message.stripped_content) is not None:
            ctx.command = self.image

    @slash_quizz.command()
    @legacy_command(ephemeral=True)
    async def start(
        self,
        ctx: LegacyCommandContext,
        question: str | None,
        attachment: discord.Attachment | None = None,
        answer: str | None = None,
    ):
        """Start a new game"""
        if ctx.channel.id not in self.quizz_cls:
            raise commands.CommandError('Not in a quizz channel')
        cls = self.quizz_cls[ctx.channel.id]
        quizz_id = await cls.create_quizz(ctx.author, question, attachment)
        await cls.set_answer(quizz_id, answer)
        await self.start_game(quizz_id)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    async def start_game(self, quizz_id: UUID):
        resp = await get_nanapi().quizz.quizz_get_quizz(quizz_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        channel_id = quizz.channel_id
        async with self.locks[channel_id]:
            resp = await get_nanapi().quizz.quizz_get_current_game(channel_id)
            if not success(resp):
                match resp.code:
                    case 404:
                        pass
                    case _:
                        raise RuntimeError(resp.result)
            else:
                raise commands.CommandError('There is a pending quizz')

            channel = self.bot.get_text_channel(channel_id)
            assert channel is not None
            cls = self.quizz_cls[channel_id]

            last_game = None
            with suppress(discord.HTTPException):
                resp = await get_nanapi().quizz.quizz_get_last_game(channel_id)
                if not success(resp):
                    match resp.code:
                        case 404:
                            pass
                        case _:
                            raise RuntimeError(resp.result)
                else:
                    last_game_res = resp.result
                    m_id = last_game_res.message_id
                    last_game = await channel.fetch_message(m_id)
                    await last_game.unpin()

            author = self.bot.get_user(quizz.author.discord_id)

            file = None
            if not quizz.is_image and quizz.url is not None:
                async with get_session().get(quizz.url) as resp:
                    buffer = io.BytesIO(await resp.read())
                file = discord.File(buffer, quizz.url.split('/')[-1])

            kwargs = {}
            if file is not None:
                kwargs['file'] = file
            if last_game is not None:
                kwargs['reference'] = last_game

            new_game_msg = await channel.send(
                content='unknown' if author is None else author.mention,
                allowed_mentions=discord.AllowedMentions(replied_user=False),
                **kwargs,
            )

            await new_game_msg.pin()

            body = NewGameBody(
                message_id=new_game_msg.id,
                answer_bananed='🍌' * len(quizz.answer) if quizz.answer is not None else None,
                quizz_id=quizz_id,
            )

            resp = await get_nanapi().quizz.quizz_new_game(body)
            if not success(resp):
                raise RuntimeError(resp.result)
            game = resp.result

            await new_game_msg.edit(embed=await cls.get_embed(game.id))

    async def end_game(self, message: discord.Message | MultiplexingMessage):
        channel = message.channel
        async with self.locks[channel.id]:
            resp = await get_nanapi().quizz.quizz_get_current_game(channel.id)
            if not success(resp):
                raise RuntimeError(resp.result)
            game = resp.result
            if game is None:
                raise commands.CommandError('No quiz started')

            resp = await get_nanapi().quizz.quizz_end_game(
                game.id,
                EndGameBody(
                    winner_discord_id=message.author.id,
                    winner_discord_username=str(message.author),
                ),
            )
            if not success(resp):
                raise RuntimeError(resp.result)
            game = resp.result

            cls = self.quizz_cls[channel.id]
            embed = await cls.get_embed(game.id)

            game_msg = await channel.fetch_message(game.message_id)
            await game_msg.edit(embed=embed)

            with suppress(Exception):
                emoji = self.bot.get_nana_emoji('FubukiGO')
                assert emoji is not None
                await message.add_reaction(emoji)

            await cls.post_end(game.id, message)

    @slash_quizz.command()
    @legacy_command()
    async def hint(self, ctx: LegacyCommandContext):
        """Turn quizz into hangman game"""
        resp = await get_nanapi().quizz.quizz_get_current_game(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No quiz started')
                case _:
                    raise RuntimeError(resp.result)
        game = resp.result

        if game.quizz.answer is None:
            raise commands.CommandError('No answer found')

        game_msg = await ctx.fetch_message(game.message_id)

        answer: list[str] = list(game.quizz.answer.casefold())
        answer_bananed: list[str] = (
            list(game.answer_bananed) if game.answer_bananed else ['🍌'] * len(answer)
        )

        max_unbananed = len(answer) // 2
        cooldown = (24 * 60 * 60) / max_unbananed

        unbananed = 0
        for letter_og, letter_bananed in zip(answer, answer_bananed):
            if letter_og == letter_bananed:
                unbananed += 1

        elapsed_time = (ctx.message.created_at - game.started_at).total_seconds()
        theorical_unbananed_atm = min(int(elapsed_time // cooldown), max_unbananed)
        to_unbanane_now = theorical_unbananed_atm - unbananed

        for _ in range(to_unbanane_now):
            r = random.choice([i for i, c in enumerate(answer_bananed) if c == '🍌'])
            answer_bananed[r] = answer[r]

        # New embed for reply
        unbananed += to_unbanane_now
        remaining_cd = (1 + unbananed - theorical_unbananed_atm) * cooldown - (
            elapsed_time % cooldown
        )
        remaining_time = datetime.fromtimestamp(remaining_cd)
        if to_unbanane_now > 0:
            text = f'{to_unbanane_now} 🍌 eaten! '
            if unbananed < max_unbananed:
                text += f'Next 🍌 lunch in {remaining_time.strftime("%Hh%Mm%Ss")}'
            elif unbananed == max_unbananed:
                text += 'I am now full of 🍌'
            else:
                text += '🍌 addiction'
        else:
            if unbananed < max_unbananed:
                text = f'Next 🍌 lunch in {remaining_time.strftime("%Hh%Mm%Ss")}'
            else:
                text = 'I am full of 🍌'

        answer_bananed_str = ''.join(answer_bananed)
        embed = Embed(title=text, description=f'`{answer_bananed_str}`', colour=COLOR_BANANA)
        embed.set_footer(text=f'{unbananed}/{max_unbananed} 🍌 eaten ({len(answer)} in total)')
        await ctx.reply(embed=embed)

        # Update quizz embed and db value
        if to_unbanane_now > 0:
            resp = await get_nanapi().quizz.quizz_set_game_bananed_answer(
                game.id, SetGameBananedAnswerBody(answer_bananed=answer_bananed_str)
            )
            if not success(resp):
                raise RuntimeError(resp.result)

            cls = self.quizz_cls[game.quizz.channel_id]
            embed = await cls.get_embed(game.id)
            await game_msg.edit(embed=embed)

    @slash_quizz_answer.command(name='get')
    @legacy_command(ephemeral=True)
    async def get_answer(self, ctx: LegacyCommandContext):
        """Get current quizz answer (author only)"""
        resp = await get_nanapi().quizz.quizz_get_current_game(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No quiz started')
                case _:
                    raise RuntimeError(resp.result)
        game = resp.result

        assert isinstance(ctx.author, Member)
        if not (
            ctx.channel.permissions_for(ctx.author).administrator
            or ctx.author.id == game.quizz.author.discord_id
        ):
            raise commands.CommandError('Not the author or an admin')

        embed = Embed(
            title='Current answer', description=f'`{game.quizz.answer}`', colour=COLOR_BANANA
        )
        await ctx.reply(embed=embed)

    @slash_quizz_answer.command(name='set')
    @legacy_command(ephemeral=True)
    async def set_answer(self, ctx: LegacyCommandContext, answer: str | None):
        """Set (or remove) current quizz answer (author only)"""
        resp = await get_nanapi().quizz.quizz_get_current_game(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No quiz started')
                case _:
                    raise RuntimeError(resp.result)
        game = resp.result

        assert isinstance(ctx.author, Member)
        if not (
            ctx.channel.permissions_for(ctx.author).administrator
            or ctx.author.id == game.quizz.author.discord_id
        ):
            raise commands.CommandError('Not the author or an admin')

        cls = self.quizz_cls[game.quizz.channel_id]
        answer_set = await cls.set_answer(quizz_id=game.quizz.id, answer=answer)
        resp = await get_nanapi().quizz.quizz_set_game_bananed_answer(
            game.id,
            SetGameBananedAnswerBody(
                answer_bananed='🍌' * len(answer_set) if answer_set is not None else None
            ),
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        game_msg = await ctx.fetch_message(game.message_id)
        embed = await cls.get_embed(game.id)
        await game_msg.edit(embed=embed)
        await ctx.reply('Answer removed' if answer_set is None else f'Answer set to {answer_set}')

    @slash_quizz_stock.command(name='start')
    @legacy_command(ephemeral=True)
    async def stock_start(self, ctx: LegacyCommandContext):
        """Start a new game with a quizz from stock"""
        resp = await get_nanapi().quizz.quizz_get_oldest_quizz(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No stock found for this channel')
                case _:
                    raise RuntimeError(resp.result)
        quizz = resp.result
        await self.start_game(quizz.id)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    @slash_quizz_stock.command(name='add')
    @legacy_command(ephemeral=True)
    async def stock_add(
        self,
        ctx: LegacyCommandContext,
        question: str | None,
        attachment: discord.Attachment | None = None,
        answer: str | None = None,
    ):
        """Add quizz in stock for the current channel"""
        if ctx.channel.id not in self.quizz_cls:
            raise commands.CommandError('Not in a quizz channel')
        cls = self.quizz_cls[ctx.channel.id]
        quizz_id = await cls.create_quizz(ctx.author, question, attachment)
        await cls.set_answer(quizz_id, answer)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    @commands.command()
    async def image(self, ctx: commands.Context):
        nb = ctx.message.content.split(' ')[0].count('a')
        await AnimeMangaQuizz.imaaage(ctx.message, nb)

    @commands.guild_only()
    @commands.command()
    async def kininarimasu(self, ctx: commands.Context):
        """Watashi... KININARIMASU"""
        await LouisQuizz.kininarimasu(ctx.channel)

    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if ctx.author.bot:
            return

        if ctx.channel.id not in self.quizz_cls:
            return

        resp = await get_nanapi().quizz.quizz_get_current_game(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    return
                case _:
                    raise RuntimeError(resp.result)
        game = resp.result
        if game is not None and game.quizz.answer is not None:
            cls = self.quizz_cls[game.quizz.channel_id]
            casefolded = ctx.message.clean_content.casefold()
            if (casefolded == game.quizz.answer.casefold()) or (
                await cls.fuzzy_validation(game.quizz.answer, casefolded)
            ):
                await self.end_game(ctx.message)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.channel_id in self.quizz_cls:
            resp = await get_nanapi().quizz.quizz_delete_game(payload.message_id)
            if not success(resp):
                raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return

        if payload.channel_id not in self.quizz_cls:
            return

        if payload.emoji.name == 'FubukiGO':
            resp = await get_nanapi().quizz.quizz_get_current_game(payload.channel_id)
            if not success(resp):
                match resp.code:
                    case 404:
                        return
                    case _:
                        raise RuntimeError(resp.result)
            game = resp.result
            if game is None:
                return

            channel = self.bot.get_text_channel(payload.channel_id)
            assert channel is not None
            message = await channel.fetch_message(payload.message_id)

            view = ConfirmationView(self.bot, payload.member)
            msg = await message.reply(
                f'{payload.member.mention} Should I end the quizz?',
                view=view,
                allowed_mentions=discord.AllowedMentions(replied_user=False),
            )

            if await view.confirmation:
                await self.end_game(message)

            await msg.delete()


def context_menu_end(cog: Quizz):
    @app_commands.context_menu(name='Quizz answer')
    async def msg_cmd_end(interaction: discord.Interaction[Bot], message: discord.Message):
        ctx = await LegacyCommandContext.from_interaction(interaction)
        await ctx.defer(ephemeral=True)
        await cog.end_game(message)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    return msg_cmd_end


async def setup(bot: Bot):
    cog = Quizz(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(context_menu_end(cog))
