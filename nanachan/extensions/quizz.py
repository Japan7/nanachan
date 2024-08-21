import asyncio
import io
import logging
import random
import re
import string
import unicodedata
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from importlib import resources
from typing import TYPE_CHECKING, cast
from uuid import UUID

import discord
import pysaucenao
from discord import Member, app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

import nanachan.resources
from nanachan.discord.application_commands import LegacyCommandContext
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import (
    Embed,
    MultiplexingContext,
    MultiplexingMessage,
    UserType,
    context_modifier,
    typing,
)
from nanachan.discord.views import ConfirmationView
from nanachan.extensions.waicolle import WaifuCollection
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    EndGameBody,
    NewGameBody,
    NewQuizzBody,
    QuizzStatus,
    SetGameBananedAnswerBody,
    SetQuizzAnswerBody,
)
from nanachan.settings import (
    ANIME_QUIZZ_CHANNEL,
    GLOBAL_COIN_MULTIPLIER,
    LOUIS_QUIZZ_CHANNEL,
    MANGA_QUIZZ_CHANNEL,
    PREFIX,
    SAUCENAO_API_KEY,
    RequiresQuizz,
)
from nanachan.utils.mime import is_image
from nanachan.utils.misc import get_session, to_producer

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

log = logging.getLogger(__name__)

COLOR_BANANA = 0xF6D68D

REWARD = 25


def romaji_regex(title: str):
    table = [
        ('aa', 'aa?'),
        ('ei', 'ei?'),
        ('ii', 'ii?'),
        ('ou', 'ou?'),
        ('oo', 'oo?'),
        ('uu', 'uu?'),
        (r'\bo\b', 'w?o'),
        ('wo', 'w?o'),
        (r'\bwa\b', '[wh]a'),
        ('he', 'h?e'),
        ('mu', 'mu?'),
        (r'\?\?', '?'),
    ]
    for i, j in table:
        title = re.sub(i, j, title)
    return title


def fuzzy_jp_match(reference: str, answer: str):
    """Black magic, I don't remember how it worked"""
    reference = re.sub(r'\(\d+\)', '', reference)
    reference = reference.translate(str.maketrans('', '', string.punctuation))
    reference = reference.casefold()
    reference = unicodedata.normalize('NFKD', reference)
    reference = reference.encode('ascii', 'ignore').decode()

    reference_reg = romaji_regex(reference)
    reference_reg = reference_reg.replace(' ', '')

    answer = answer.translate(str.maketrans('', '', string.punctuation + ' '))
    answer = answer.casefold()
    answer = unicodedata.normalize('NFKD', answer)
    answer = answer.encode('ascii', 'ignore').decode()

    return bool(re.search(reference_reg, answer))


class QuizzBase(ABC):

    def __init__(self, bot: Bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id

    async def _parse_media(self,
                           message: discord.Message,
                           force_image: bool = False) -> tuple[str | None, str]:
        url = None
        content = message.content
        image_check = False

        if len(message.attachments) > 0:
            url = message.attachments[0].url
            url = (await to_producer(url))['url']
            image_check = await is_image(url)
        elif content is not None:
            url_match = re.search(r'https://[^ ]+', content)
            if url_match is not None:
                url = url_match.group(0)
                image_check = await is_image(url)
                if image_check:
                    url = (await to_producer(url))['url']
                    content = re.sub(r'(https://[^ ]+) ?', '', content)

        if force_image and not image_check:
            raise commands.CommandError(
                'Message does not contain an image nor an image message ID')

        return url, content

    @abstractmethod
    async def create_quizz(self, message: discord.Message) -> UUID:
        pass

    async def _set_answer_dm(self, quizz_id: UUID, author: UserType, private: bool):
        channel = self.bot.get_text_channel(self.channel_id)
        assert channel is not None

        wait_msg = None
        if not private:
            wait_msg = await channel.send(
                f"*Waiting for {author.mention} to provide answer in DM (120s).*\n"
                "*Do not send any proposition until the embed is created and pinned!*",
                mention_author=False)
            desc = (
                f"Send `{PREFIX}quizz setanswer` "
                f"in `#{str(channel)}` if you need to change it afterwards.")
        else:
            desc = (f"Send `{PREFIX}quizz stock setanswer {quizz_id}` "
                    "here if you need to change it afterwards.")

        ask_embed = Embed(
            title='Please provide quizz answer in the next 120s.',
            description='If you do not want to give the answer, send `skip` now.\n\n' +
            desc,
            colour=COLOR_BANANA)

        with suppress(Exception):
            await author.send(embed=ask_embed)

        try:
            answer = await self.bot.wait_for(
                'user_message',
                check=lambda m: m.author == author and m.channel == author.dm_channel,
                timeout=120)
            answer = answer.message
        except asyncio.TimeoutError:
            if not private:
                await channel.send('*Timeout.*', delete_after=5)
            with suppress(Exception):
                await author.send('Timeout.')
        else:
            await answer.add_reaction('🍌')
            if answer.content != 'skip':
                resp = await get_nanapi().quizz.quizz_set_quizz_answer(
                    quizz_id,
                    SetQuizzAnswerBody(answer=answer.clean_content.replace(
                        '`', "'"), answer_source='Provided answer'))
                if not success(resp):
                    raise RuntimeError(resp.result)
            else:
                if not private:
                    await channel.send(
                        f"*{author.mention} chose to not give the answer.*",
                        mention_author=False,
                        delete_after=5)
                resp = await get_nanapi().quizz.quizz_set_quizz_answer(
                    quizz_id, SetQuizzAnswerBody(answer=None,
                                                 answer_source=None))
                if not success(resp):
                    raise RuntimeError(resp.result)

        if wait_msg is not None:
            await wait_msg.delete()

    async def set_answer(self,
                         quizz_id: UUID,
                         author: UserType,
                         private: bool = False):
        await self._set_answer_dm(quizz_id, author, private)

    async def get_embed(self, game_id: UUID):
        resp = await get_nanapi().quizz.quizz_get_game(game_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        game = resp.result
        channel = self.bot.get_channel(self.channel_id)
        assert isinstance(channel, discord.TextChannel)
        author = channel.guild.get_member(game.quizz.author.discord_id)

        if author is not None:
            embed = Embed(colour=author.color,
                          description=game.quizz.description)
            embed.set_author(name=author, icon_url=author.display_avatar)
        else:
            embed = Embed(description=game.quizz.description)

        embed.set_footer(
            text=f"[{game_id}] #{channel} — {game.status.capitalize()}")

        if game.quizz.answer is not None:
            answer = (game.answer_bananed if game.status
                      is not QuizzStatus.ENDED else game.quizz.answer)
            embed.add_field(name=game.quizz.answer_source,
                            value=f"||`{answer}`||")

        if game.winner is not None:
            winner = self.bot.get_user(game.winner.discord_id)
            assert winner is not None
            embed.add_field(name='Solved by', value=f"{winner.mention}")

        if game.quizz.is_image:
            embed.set_image(url=game.quizz.url)

        return embed

    async def fuzzy_validation(self, answer: str, submission: str) -> bool:
        return False

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        resp = await get_nanapi().quizz.quizz_get_game(game_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        game = resp.result
        game_msg = await message.channel.fetch_message(game.message_id)

        if message.author.id == game.quizz.author.discord_id:
            return

        time = (message.created_at - game_msg.created_at).total_seconds()

        author_nb = round(REWARD * time / (24 * 3600))
        author_nb = min(author_nb, REWARD)
        answer_nb = REWARD - author_nb

        waifu_cog = cast(WaifuCollection,
                         self.bot.get_cog(WaifuCollection.__cog_name__))

        quizz_author = self.bot.get_user(game.quizz.author.discord_id)
        if quizz_author is not None:
            await waifu_cog.reward_coins(quizz_author, max(5, author_nb) * GLOBAL_COIN_MULTIPLIER,
                                         'Quizz author')
        await waifu_cog.reward_coins(message.author, max(5, answer_nb) * GLOBAL_COIN_MULTIPLIER,
                                     'Quizz answer')


class AnimeMangaQuizz(QuizzBase):

    async def create_quizz(self, message: discord.Message):
        url, content = await self._parse_media(message, force_image=True)
        body = NewQuizzBody(channel_id=self.channel_id,
                            description=content,
                            url=url,
                            is_image=True,
                            author_discord_id=message.author.id,
                            author_discord_username=str(message.author))
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    async def _saucenao(self, quizz_id: UUID, author: UserType, private: bool):
        resp = await get_nanapi().quizz.quizz_get_quizz(quizz_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        channel = self.bot.get_text_channel(self.channel_id)
        assert channel is not None

        if SAUCENAO_API_KEY is None:
            raise commands.CommandError('SauceNAO is not set up')

        saucenao = pysaucenao.SauceNao(min_similarity=60,
                                       priority=[21, 37],
                                       api_key=SAUCENAO_API_KEY)
        selected_sauce = None
        try:
            assert quizz.url is not None
            sauces = await saucenao.from_url(quizz.url)
        except Exception as e:
            log.exception(e)
            raise e

        for sauce in sauces:
            if sauce.title is not None and isinstance(
                    sauce, (pysaucenao.AnimeSource, pysaucenao.MangaSource)):
                selected_sauce = sauce
                break

        if selected_sauce is not None:
            if not private:
                await channel.send(
                    f"*SauceNAO returned a result with {selected_sauce.similarity}% similarity.*",
                    delete_after=5)
                desc = (f"\n\nSend `{PREFIX}quizz setanswer` "
                        f"in `#{str(channel)}` if you want to manually set it.")
            else:
                desc = (f"\n\nSend `{PREFIX}stock setanswer {quizz_id}` "
                        "here if you want to manually set it.")

            assert selected_sauce.title is not None
            sauce = selected_sauce.title.replace('`', "'")
            embed = Embed(title='SauceNAO result',
                          description='`' + sauce +
                          f"`\n({selected_sauce.similarity}% similarity)" +
                          desc,
                          colour=COLOR_BANANA)
            await author.send(embed=embed)

            resp = await get_nanapi().quizz.quizz_set_quizz_answer(
                quizz_id,
                SetQuizzAnswerBody(answer=sauce, answer_source='SauceNAO'))
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            raise commands.CommandError('No SauceNAO result')

    @classmethod
    async def _image(cls, message: discord.Message | MultiplexingMessage, nb: int = 1):
        with Image.open(
                resources.open_binary(
                    nanachan.resources, f"image{random.randint(1,3):02}.jpg")) as image:
            with io.BytesIO() as pp_binary, suppress(IndexError):
                mention = message.mentions[0]
                asset = mention.display_avatar.with_format('png')
                await asset.save(pp_binary)
                with Image.open(pp_binary, formats=['PNG']) as pp:
                    pp = pp.resize(size=(200, 200))
                    try:
                        image.paste(pp, (1013, 50), pp)
                    except ValueError:
                        image.paste(pp, (1013, 50))
            draw = ImageDraw.Draw(image)
            font_res = resources.open_binary(nanachan.resources, 'Anton-Regular.ttf')
            with font_res:
                font = ImageFont.truetype(font_res, size=150)
                A = nb * 'A'
                draw.text((632, 620),
                          f"IM{A}GE",
                          fill='white',
                          stroke_fill='black',
                          stroke_width=10,
                          anchor='ms',
                          font=font)
                with io.BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await message.channel.send(
                        file=discord.File(
                            fp=image_binary, filename='IMAGE.png')
                    )

    async def set_answer(self,
                         quizz_id: UUID,
                         author: UserType,
                         private: bool = False):
        try:
            await self._saucenao(quizz_id, author, private)
        except Exception as e:
            log.exception(e)
            await super().set_answer(quizz_id, author, private)

    async def fuzzy_validation(self, answer: str, submission: str) -> bool:
        return await asyncio.to_thread(fuzzy_jp_match, answer, submission)

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        nb = random.randint(1, 12)
        reply = await message.reply(
            f"{PREFIX}im{nb*'a'}ge {message.author.mention}")
        await self._image(reply, nb)


class LouisQuizz(QuizzBase):

    async def create_quizz(self, message: discord.Message):
        url, content = await self._parse_media(message)
        body = NewQuizzBody(channel_id=self.channel_id,
                            description=content,
                            url=url,
                            is_image=False,
                            author_discord_id=message.author.id,
                            author_discord_username=str(message.author))
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    @classmethod
    async def _kininarimasu(cls, channel: 'MessageableChannel'):
        with resources.path(nanachan.resources, f"hyouka{random.randint(1,7):02}.gif") as path:
            await channel.send(file=discord.File(path))

    async def post_end(self, game_id: UUID,
                       message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        await message.reply(f"{PREFIX}kininarimasu {message.author.mention}")
        await self._kininarimasu(message.channel)


@RequiresQuizz
class Quizz(Cog):
    """ Ask questions and get hints for quizzes """
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
                raise commands.CommandError("There is a pending quizz")

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
                content="unknown" if author is None else author.mention,
                allowed_mentions=discord.AllowedMentions(replied_user=False),
                **kwargs
            )

            await new_quizz_msg.pin()

            body = NewGameBody(
                message_id=new_quizz_msg.id,
                answer_bananed='🍌' *
                len(quizz.answer) if quizz.answer is not None else None,
                quizz_id=quizz_id
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
                game.id, EndGameBody(winner_discord_id=message.author.id,
                                     winner_discord_username=str(message.author)))
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
        answer_bananed: list[str] = (list(game.answer_bananed)
                                     if game.answer_bananed else ['🍌'] * len(answer))

        max_unbananed = len(answer) // 2
        cooldown = (24 * 60 * 60) / max_unbananed

        unbananed = 0
        for letter_og, letter_bananed in zip(answer, answer_bananed):
            if letter_og == letter_bananed:
                unbananed += 1

        elapsed_time = (ctx.message.created_at -
                        game.started_at).total_seconds()
        theorical_unbananed_atm = min(int(elapsed_time // cooldown),
                                      max_unbananed)
        to_unbanane_now = theorical_unbananed_atm - unbananed

        for _ in range(to_unbanane_now):
            r = random.choice(
                [i for i, c in enumerate(answer_bananed) if c == '🍌'])
            answer_bananed[r] = answer[r]

        # New embed for reply
        unbananed += to_unbanane_now
        remaining_cd = (1 + unbananed - theorical_unbananed_atm) * cooldown - (
            elapsed_time % cooldown)
        remaining_time = datetime.fromtimestamp(remaining_cd)
        if to_unbanane_now > 0:
            text = f"{to_unbanane_now} 🍌 eaten! "
            if unbananed < max_unbananed:
                text += f"Next 🍌 lunch in {remaining_time.strftime('%Hh%Mm%Ss')}"
            elif unbananed == max_unbananed:
                text += 'I am now full of 🍌'
            else:
                text += '🍌 addiction'
        else:
            if unbananed < max_unbananed:
                text = f"Next 🍌 lunch in {remaining_time.strftime('%Hh%Mm%Ss')}"
            else:
                text = 'I am full of 🍌'

        answer_bananed_str = ''.join(answer_bananed)
        embed = Embed(title=text,
                      description=f"`{answer_bananed_str}`",
                      colour=COLOR_BANANA)
        embed.set_footer(
            text=f"{unbananed}/{max_unbananed} 🍌 eaten ({len(answer)} in total)"
        )
        await ctx.send(content=ctx.author.mention,
                       embed=embed,
                       reference=quizz_msg,
                       mention_author=False)

        await ctx.message.delete()

        # Update quizz embed and db value
        if to_unbanane_now > 0:
            resp = await get_nanapi().quizz.quizz_set_game_bananed_answer(
                game.id,
                SetGameBananedAnswerBody(answer_bananed=answer_bananed_str))
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
        if not (ctx.channel.permissions_for(ctx.author).administrator or
                ctx.author.id == game.quizz.author.discord_id):
            raise commands.CommandError('Not the author or an admin')

        embed = Embed(title='Current answer',
                      description=f"`{game.quizz.answer}`",
                      colour=COLOR_BANANA)
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
        if not (ctx.channel.permissions_for(ctx.author).administrator or
                ctx.author.id == game.quizz.author.discord_id):
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
                    raise commands.CommandError(
                        'No stock found for this channel')
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
        embed = Embed(title=f"[{id}] Answer",
                      description=f"`{quizz.answer}`",
                      colour=COLOR_BANANA)
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
                    await cls.fuzzy_validation(game.quizz.answer, casefolded)):
                await self._end(ctx.message)

    @Cog.listener()
    async def on_raw_message_delete(self,
                                    payload: discord.RawMessageDeleteEvent):
        if payload.channel_id in self.quizz_cls:
            resp = await get_nanapi().quizz.quizz_delete_game(payload.message_id)
            if not success(resp):
                raise RuntimeError(resp.result)

    @Cog.listener()
    async def on_raw_reaction_add(self,
                                  payload: discord.RawReactionActionEvent):
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
                f"{payload.member.mention} Should I end the quizz?",
                view=view,
                allowed_mentions=discord.AllowedMentions(replied_user=False))

            if await view.confirmation:
                await self._end(message)

            await msg.delete()


def context_menu_start(cog: Quizz):

    @app_commands.context_menu(name='Quizz start')
    async def msg_cmd_start(interaction: discord.Interaction,
                            message: discord.Message):
        ctx = await LegacyCommandContext.from_interaction(interaction)
        await ctx.defer(ephemeral=True)
        await cog._start(message)
        await ctx.reply(ctx.bot.get_emoji_str('FubukiGO'))

    return msg_cmd_start


def context_menu_end(cog: Quizz):

    @app_commands.context_menu(name='Quizz end')
    async def msg_cmd_end(interaction: discord.Interaction,
                          message: discord.Message):
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
