import asyncio
import io
import logging
import random
import re
import string
import unicodedata
from abc import ABC, abstractmethod
from contextlib import suppress
from importlib import resources
from typing import TYPE_CHECKING, cast
from uuid import UUID

import discord
import pysaucenao
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

import nanachan.resources
from nanachan.discord.bot import Bot
from nanachan.discord.helpers import (
    Embed,
    MultiplexingMessage,
    UserType,
)
from nanachan.extensions.waicolle import WaifuCollection
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    NewQuizzBody,
    QuizzStatus,
    SetQuizzAnswerBody,
)
from nanachan.settings import (
    GLOBAL_COIN_MULTIPLIER,
    PREFIX,
    SAUCENAO_API_KEY,
)
from nanachan.utils.mime import is_image
from nanachan.utils.misc import to_producer

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

logger = logging.getLogger(__name__)

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

    async def _parse_media(
        self, message: discord.Message, force_image: bool = False
    ) -> tuple[str | None, str]:
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
                'Message does not contain an image nor an image message ID'
            )

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
                f'*Waiting for {author.mention} to provide answer in DM (120s).*\n'
                '*Do not send any proposition until the embed is created and pinned!*',
                mention_author=False,
            )
            desc = (
                f'Send `{PREFIX}quizz setanswer` '
                f'in `#{str(channel)}` if you need to change it afterwards.'
            )
        else:
            desc = (
                f'Send `{PREFIX}quizz stock setanswer {quizz_id}` '
                'here if you need to change it afterwards.'
            )

        ask_embed = Embed(
            title='Please provide quizz answer in the next 120s.',
            description='If you do not want to give the answer, send `skip` now.\n\n' + desc,
            colour=COLOR_BANANA,
        )

        with suppress(Exception):
            await author.send(embed=ask_embed)

        try:
            answer = await self.bot.wait_for(
                'user_message',
                check=lambda m: m.author == author and m.channel == author.dm_channel,
                timeout=120,
            )
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
                    SetQuizzAnswerBody(
                        answer=answer.clean_content.replace('`', "'"),
                        answer_source='Provided answer',
                    ),
                )
                if not success(resp):
                    raise RuntimeError(resp.result)
            else:
                if not private:
                    await channel.send(
                        f'*{author.mention} chose to not give the answer.*',
                        mention_author=False,
                        delete_after=5,
                    )
                resp = await get_nanapi().quizz.quizz_set_quizz_answer(
                    quizz_id, SetQuizzAnswerBody(answer=None, answer_source=None)
                )
                if not success(resp):
                    raise RuntimeError(resp.result)

        if wait_msg is not None:
            await wait_msg.delete()

    async def set_answer(self, quizz_id: UUID, author: UserType, private: bool = False):
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
            embed = Embed(colour=author.color, description=game.quizz.description)
            embed.set_author(name=author, icon_url=author.display_avatar)
        else:
            embed = Embed(description=game.quizz.description)

        embed.set_footer(text=f'[{game_id}] #{channel} — {game.status.capitalize()}')

        if game.quizz.answer is not None:
            answer = (
                game.answer_bananed if game.status is not QuizzStatus.ENDED else game.quizz.answer
            )
            embed.add_field(name=game.quizz.answer_source, value=f'||`{answer}`||')

        if game.winner is not None:
            winner = self.bot.get_user(game.winner.discord_id)
            assert winner is not None
            embed.add_field(name='Solved by', value=f'{winner.mention}')

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

        waifu_cog = cast(WaifuCollection, self.bot.get_cog(WaifuCollection.__cog_name__))

        quizz_author = self.bot.get_user(game.quizz.author.discord_id)
        if quizz_author is not None:
            await waifu_cog.reward_coins(
                quizz_author, max(5, author_nb) * GLOBAL_COIN_MULTIPLIER, 'Quizz author'
            )
        await waifu_cog.reward_coins(
            message.author, max(5, answer_nb) * GLOBAL_COIN_MULTIPLIER, 'Quizz answer'
        )


class AnimeMangaQuizz(QuizzBase):
    async def create_quizz(self, message: discord.Message):
        url, content = await self._parse_media(message, force_image=True)
        body = NewQuizzBody(
            channel_id=self.channel_id,
            description=content,
            url=url,
            is_image=True,
            author_discord_id=message.author.id,
            author_discord_username=str(message.author),
        )
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

        saucenao = pysaucenao.SauceNao(
            min_similarity=60, priority=[21, 37], api_key=SAUCENAO_API_KEY
        )
        selected_sauce = None
        try:
            assert quizz.url is not None
            sauces = await saucenao.from_url(quizz.url)
        except Exception as e:
            logger.exception(e)
            raise e

        for sauce in sauces:
            if sauce.title is not None and isinstance(
                sauce, (pysaucenao.AnimeSource, pysaucenao.MangaSource)
            ):
                selected_sauce = sauce
                break

        if selected_sauce is not None:
            if not private:
                await channel.send(
                    f'*SauceNAO returned a result with {selected_sauce.similarity}% similarity.*',
                    delete_after=5,
                )
                desc = (
                    f'\n\nSend `{PREFIX}quizz setanswer` '
                    f'in `#{str(channel)}` if you want to manually set it.'
                )
            else:
                desc = (
                    f'\n\nSend `{PREFIX}stock setanswer {quizz_id}` '
                    'here if you want to manually set it.'
                )

            assert selected_sauce.title is not None
            sauce = selected_sauce.title.replace('`', "'")
            embed = Embed(
                title='SauceNAO result',
                description='`' + sauce + f'`\n({selected_sauce.similarity}% similarity)' + desc,
                colour=COLOR_BANANA,
            )
            await author.send(embed=embed)

            resp = await get_nanapi().quizz.quizz_set_quizz_answer(
                quizz_id, SetQuizzAnswerBody(answer=sauce, answer_source='SauceNAO')
            )
            if not success(resp):
                raise RuntimeError(resp.result)
        else:
            raise commands.CommandError('No SauceNAO result')

    @classmethod
    async def _image(cls, message: discord.Message | MultiplexingMessage, nb: int = 1):
        with Image.open(
            resources.open_binary(nanachan.resources, f'image{random.randint(1, 3):02}.jpg')
        ) as image:
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
                draw.text(
                    (632, 620),
                    f'IM{A}GE',
                    fill='white',
                    stroke_fill='black',
                    stroke_width=10,
                    anchor='ms',
                    font=font,
                )
                with io.BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await message.channel.send(
                        file=discord.File(fp=image_binary, filename='IMAGE.png')
                    )

    async def set_answer(self, quizz_id: UUID, author: UserType, private: bool = False):
        try:
            await self._saucenao(quizz_id, author, private)
        except Exception as e:
            logger.exception(e)
            await super().set_answer(quizz_id, author, private)

    async def fuzzy_validation(self, answer: str, submission: str) -> bool:
        return await asyncio.to_thread(fuzzy_jp_match, answer, submission)

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        nb = random.randint(1, 12)
        reply = await message.reply(f'{PREFIX}im{nb * "a"}ge {message.author.mention}')
        await self._image(reply, nb)


class LouisQuizz(QuizzBase):
    async def create_quizz(self, message: discord.Message):
        url, content = await self._parse_media(message)
        body = NewQuizzBody(
            channel_id=self.channel_id,
            description=content,
            url=url,
            is_image=False,
            author_discord_id=message.author.id,
            author_discord_username=str(message.author),
        )
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    @classmethod
    async def _kininarimasu(cls, channel: 'MessageableChannel'):
        with resources.path(nanachan.resources, f'hyouka{random.randint(1, 7):02}.gif') as path:
            await channel.send(file=discord.File(path))

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        await message.reply(f'{PREFIX}kininarimasu {message.author.mention}')
        await self._kininarimasu(message.channel)
