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
from discord.ext import commands

from nanachan.discord.application_commands import LegacyCommandContext
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import (
    Embed,
    MultiplexingContext,
    MultiplexingMessage,
    context_modifier,
    typing,
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

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.quizz_cls: dict[int, QuizzBase] = {
            ANIME_QUIZZ_CHANNEL: AnimeMangaQuizz(self.bot, ANIME_QUIZZ_CHANNEL),
            MANGA_QUIZZ_CHANNEL: AnimeMangaQuizz(self.bot, MANGA_QUIZZ_CHANNEL),
            LOUIS_QUIZZ_CHANNEL: LouisQuizz(self.bot, LOUIS_QUIZZ_CHANNEL),
        }
        self.locks = defaultdict(asyncio.Lock)
        context_modifier(self.image_ctx)
        context_modifier(self.image_quizz_post)

    image_prog = re.compile(rf'{re.escape(PREFIX)}ima+ge')

    async def image_ctx(self, ctx):
        if self.image_prog.match(ctx.message.stripped_content) is not None:
            ctx.command = self.image

    async def image_quizz_post(self, ctx: MultiplexingContext):
        if ctx.author.bot:
            return

        if ctx.command is not None:
            return

    @commands.group(aliases=['quiz'])
    async def quizz(self, ctx: commands.Context):
        """Quizz subcommands"""
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument('Missing subcommand')
        if ctx.channel.id not in self.quizz_cls:
            return

    async def _start_quizz(self, quizz_id: UUID):
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
            if not quizz.is_image and quizz.hikaried:
                assert quizz.url is not None
                async with get_session().get(quizz.url) as resp:
                    buffer = io.BytesIO(await resp.read())
                file = discord.File(buffer, quizz.url.split('/')[-1])

            kwargs = {}
            if file is not None:
                kwargs['file'] = file
            if last_game is not None:
                kwargs['reference'] = last_game

            new_quizz_msg = await channel.send(
                content='unknown' if author is None else author.mention,
                allowed_mentions=discord.AllowedMentions(replied_user=False),
                **kwargs,
            )

            await new_quizz_msg.pin()

            body = NewGameBody(
                message_id=new_quizz_msg.id,
                answer_bananed='🍌' * len(quizz.answer) if quizz.answer is not None else None,
                quizz_id=quizz_id,
            )

            resp = await get_nanapi().quizz.quizz_new_game(body)
            if not success(resp):
                raise RuntimeError(resp.result)
            game = resp.result

            await new_quizz_msg.edit(embed=await cls.get_embed(game.id))

    async def _start(self, message: discord.Message):
        cls = self.quizz_cls[message.channel.id]
        quizz_id = await cls.create_quizz(message)
        await cls.set_answer(quizz_id, message.author)
        await self._start_quizz(quizz_id)
        await message.delete()

    @commands.guild_only()
    @quizz.command()
    @typing
    async def start(self, ctx: commands.Context, message: discord.Message):
        """Start a new quizz"""
        await self._start(message)
        await ctx.message.delete()

    async def _end(self, message: discord.Message | MultiplexingMessage):
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

            quizz_msg = await channel.fetch_message(game.message_id)
            await quizz_msg.edit(embed=embed)

            with suppress(Exception):
                emoji = self.bot.get_nana_emoji('FubukiGO')
                assert emoji is not None
                await message.add_reaction(emoji)

            await cls.post_end(game.id, message)

    @commands.guild_only()
    @quizz.command()
    async def end(self, ctx: commands.Context, message: discord.Message):
        """End a quizz"""
        await self._end(message)
        await ctx.message.delete()

    @commands.guild_only()
    @quizz.command(aliases=['indice'])
    async def hint(self, ctx: commands.Context):
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

        quizz_msg = await ctx.fetch_message(game.message_id)

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
        await ctx.send(
            content=ctx.author.mention, embed=embed, reference=quizz_msg, mention_author=False
        )

        await ctx.message.delete()

        # Update quizz embed and db value
        if to_unbanane_now > 0:
            resp = await get_nanapi().quizz.quizz_set_game_bananed_answer(
                game.id, SetGameBananedAnswerBody(answer_bananed=answer_bananed_str)
            )
            if not success(resp):
                raise RuntimeError(resp.result)

            cls = self.quizz_cls[game.quizz.channel_id]
            embed = await cls.get_embed(game.id)
            await quizz_msg.edit(embed=embed)

    @commands.guild_only()
    @quizz.command()
    async def getanswer(self, ctx: commands.Context):
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
        await ctx.author.send(embed=embed)
        await ctx.message.delete()

    @commands.guild_only()
    @quizz.command()
    async def setanswer(self, ctx: commands.Context):
        """Set current quizz answer manually (author only)"""
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
        await cls._set_answer_dm(game.quizz.id, private=True, author=ctx.author)
        quizz_msg = await ctx.fetch_message(game.message_id)
        embed = await cls.get_embed(game.id)
        await quizz_msg.edit(embed=embed)

    @quizz.group()
    async def stock(self, ctx: commands.Context):
        """Quizz DB utilities, some subcommands are only showing in DM"""
        if ctx.invoked_subcommand is None:
            await self.random_stock(ctx)

    async def random_stock(self, ctx: commands.Context):
        resp = await get_nanapi().quizz.quizz_get_oldest_quizz(ctx.channel.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No stock found for this channel')
                case _:
                    raise RuntimeError(resp.result)
        quizz = resp.result
        await self._start_quizz(quizz.id)
        await ctx.message.delete()

    @commands.has_permissions(administrator=True)
    @stock.command()
    async def delete(self, ctx: commands.Context, id: str):
        """Delete quizz entry by id (admins only)"""
        uuid = UUID(id)
        resp = await get_nanapi().quizz.quizz_delete_quizz(uuid)
        if not success(resp):
            raise RuntimeError(resp.result)
        await ctx.message.add_reaction('🍌')

    @commands.dm_only()
    @stock.command(name='getanswer')
    async def getanswer_stock(self, ctx: commands.Context, id: str):
        """Get stock quizz answer (author only if not ended)"""
        uuid = UUID(id)
        resp = await get_nanapi().quizz.quizz_get_quizz(uuid)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No quiz started')
                case _:
                    raise RuntimeError(resp.result)
        quizz = resp.result
        embed = Embed(title=f'[{id}] Answer', description=f'`{quizz.answer}`', colour=COLOR_BANANA)
        await ctx.author.send(embed=embed)

    @commands.dm_only()
    @stock.command(name='setanswer')
    async def setanswer_stock(self, ctx: commands.Context, id: str):
        """Set stock quizz answer manually if not already started (author only)"""
        uuid = UUID(id)
        resp = await get_nanapi().quizz.quizz_get_quizz(uuid)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('No quiz started')
                case _:
                    raise RuntimeError(resp.result)
        quizz = resp.result
        cls = self.quizz_cls[quizz.channel_id]
        await cls._set_answer_dm(quizz.id, private=True, author=ctx.author)

    @commands.dm_only()
    @stock.command()
    async def anime(self, ctx: commands.Context):
        """Add anime quizz in stock (DM only)"""
        cls = self.quizz_cls[ANIME_QUIZZ_CHANNEL]
        quizz_id = await cls.create_quizz(ctx.message)
        await cls.set_answer(quizz_id, ctx.author, private=True)

    @commands.dm_only()
    @stock.command()
    async def manga(self, ctx: commands.Context):
        """Add manga quizz in stock (DM only)"""
        cls = self.quizz_cls[MANGA_QUIZZ_CHANNEL]
        quizz_id = await cls.create_quizz(ctx.message)
        await cls.set_answer(quizz_id, ctx.author, private=True)

    @commands.dm_only()
    @stock.command()
    async def louis(self, ctx: commands.Context):
        """Add louis quizz in stock (DM only)"""
        cls = self.quizz_cls[LOUIS_QUIZZ_CHANNEL]
        quizz_id = await cls.create_quizz(ctx.message)
        await cls.set_answer(quizz_id, ctx.author, private=True)

    @commands.command()
    async def image(self, ctx: commands.Context):
        nb = ctx.message.content.split(' ')[0].count('a')
        await AnimeMangaQuizz._image(ctx.message, nb)

    @commands.guild_only()
    @commands.command()
    async def kininarimasu(self, ctx: commands.Context):
        """Watashi... KININARIMASU"""
        await LouisQuizz._kininarimasu(ctx.channel)

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
                await self._end(ctx.message)

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
                await self._end(message)

            await msg.delete()


def context_menu_start(cog: Quizz):
    @app_commands.context_menu(name='Quizz start')
    async def msg_cmd_start(interaction: discord.Interaction[Bot], message: discord.Message):
        ctx = await LegacyCommandContext.from_interaction(interaction)
        await ctx.defer(ephemeral=True)
        await cog._start(message)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    return msg_cmd_start


def context_menu_end(cog: Quizz):
    @app_commands.context_menu(name='Quizz end')
    async def msg_cmd_end(interaction: discord.Interaction[Bot], message: discord.Message):
        ctx = await LegacyCommandContext.from_interaction(interaction)
        await ctx.defer(ephemeral=True)
        await cog._end(message)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    return msg_cmd_end


async def setup(bot: Bot):
    cog = Quizz(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(context_menu_start(cog))
    bot.tree.add_command(context_menu_end(cog))
