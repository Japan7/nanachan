import asyncio
import io
import logging
import random
import re
import string
import unicodedata
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from importlib import resources
from typing import TYPE_CHECKING, cast
from uuid import UUID

import discord
import pysaucenao
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pydantic_ai import Agent, RunContext

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
    AI_FAST_MODEL,
    GLOBAL_COIN_MULTIPLIER,
    PREFIX,
    SAUCENAO_API_KEY,
    RequiresAI,
)
from nanachan.utils.ai import get_model
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


@dataclass
class QuizzRunDeps:
    question: str | None
    answer: str | None


agent = Agent(deps_type=QuizzRunDeps)


@agent.system_prompt
def system_prompt(ctx: RunContext[QuizzRunDeps]) -> str:
    prompt: list[str] = []
    if (question := ctx.deps.question) is not None:
        prompt.append(f'The quizz question is: {question}.')
    if (answer := ctx.deps.answer) is not None:
        prompt.append(f'The quizz answer is: {answer}.')
    return '\n'.join(prompt)


class QuizzBase(ABC):
    def __init__(self, bot: Bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id

    @abstractmethod
    async def create_quizz(
        self,
        author: UserType,
        question: str | None,
        attachment: discord.Attachment | None,
    ) -> UUID:
        pass

    async def set_answer(
        self,
        quizz_id: UUID,
        answer: str | None,
        source: str | None = None,
    ) -> str | None:
        resp = await get_nanapi().quizz.quizz_set_quizz_answer(
            quizz_id,
            SetQuizzAnswerBody(
                answer=answer,
                answer_source=source if source is not None else 'Provided answer',
            )
            if answer is not None
            else SetQuizzAnswerBody(),
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        return answer

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

    async def try_validate(
        self,
        question: str | None,
        answer: str | None,
        submission: str,
    ) -> bool:
        if RequiresAI.configured and (question is not None or submission is not None):
            assert AI_FAST_MODEL
            run = await agent.run(
                f'Tell whether the following submission matches the answer: {submission}',
                output_type=bool,
                model=get_model(AI_FAST_MODEL),
                deps=QuizzRunDeps(question, answer),
            )
            return run.output
        else:
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
    async def create_quizz(
        self,
        author: UserType,
        question: str | None,
        attachment: discord.Attachment | None,
    ):
        if (
            attachment is None
            or attachment.content_type is None
            or not attachment.content_type.startswith('image/')
        ):
            raise commands.CommandError(
                'Message does not contain an image nor an image message ID'
            )
        url = (await to_producer(attachment.url))['url']
        body = NewQuizzBody(
            channel_id=self.channel_id,
            description='',
            url=url,
            is_image=True,
            author_discord_id=author.id,
            author_discord_username=str(author),
        )
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    async def set_answer(self, quizz_id: UUID, answer: str | None, source: str | None = None):
        if answer is None:
            try:
                answer = await self.saucenao(quizz_id)
                source = 'SauceNAO'
            except Exception as e:
                logger.exception(e)
        return await super().set_answer(quizz_id, answer, source)

    async def saucenao(self, quizz_id: UUID):
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

        if selected_sauce is None:
            raise commands.CommandError('No SauceNAO result')

        assert selected_sauce.title is not None
        return selected_sauce.title.replace('`', "'")

    async def try_validate(
        self, question: str | None, answer: str | None, submission: str
    ) -> bool:
        fuzzy = (
            await asyncio.to_thread(fuzzy_jp_match, answer, submission)
            if answer is not None
            else False
        )
        return fuzzy or await super().try_validate(question, answer, submission)

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        nb = random.randint(1, 12)
        reply = await message.reply(f'{PREFIX}im{nb * "a"}ge {message.author.mention}')
        await self.imaaage(reply, nb)

    @classmethod
    async def imaaage(cls, message: discord.Message | MultiplexingMessage, nb: int = 1):
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


class LouisQuizz(QuizzBase):
    async def create_quizz(
        self,
        author: UserType,
        question: str | None,
        attachment: discord.Attachment | None,
    ):
        url = (await to_producer(attachment.url))['url'] if attachment is not None else None
        body = NewQuizzBody(
            channel_id=self.channel_id,
            description=question if question is not None else '',
            url=url,
            is_image=False,
            author_discord_id=author.id,
            author_discord_username=str(author),
        )
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        await message.reply(f'{PREFIX}kininarimasu {message.author.mention}')
        await self.kininarimasu(message.channel)

    @classmethod
    async def kininarimasu(cls, channel: 'MessageableChannel'):
        with resources.path(nanachan.resources, f'hyouka{random.randint(1, 7):02}.gif') as path:
            await channel.send(file=discord.File(path))
