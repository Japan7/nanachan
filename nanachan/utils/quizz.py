import asyncio
import io
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
import numpy as np
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from pydantic_ai import RunContext

import nanachan.resources
from nanachan.discord.bot import Bot
from nanachan.discord.helpers import Embed, MultiplexingMessage, UserType
from nanachan.extensions.waicolle import WaifuCollection
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import NewQuizzBody, QuizzStatus
from nanachan.settings import (
    AI_FLAGSHIP_MODEL,
    GLOBAL_COIN_MULTIPLIER,
    PREFIX,
    SAUCENAO_API_KEY,
    RequiresAI,
)
from nanachan.utils.ai import Agent, get_model
from nanachan.utils.misc import saucenao_lookup, to_producer

if TYPE_CHECKING:
    from discord.abc import MessageableChannel

COLOR_BANANA = 0xF6D68D

_RNG = np.random.default_rng()


@dataclass
class RunDeps:
    question: str | None
    answer: str | None


class QuizzBase(ABC):
    HINTS_COUNT = 5
    REWARD = 100

    agent = Agent(deps_type=RunDeps)

    @agent.instructions
    @staticmethod
    def instructions(run_ctx: RunContext[RunDeps]) -> str:
        prompt: list[str] = []
        if question := run_ctx.deps.question:
            prompt.append(f'The quizz question is: {question}')
        if answer := run_ctx.deps.answer:
            prompt.append(f'The quizz answer is: {answer}')
        return '\n'.join(prompt)

    def __init__(self, bot: Bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id

    @abstractmethod
    async def create_quizz(
        self,
        author: UserType,
        question: str | None,
        attachment: discord.Attachment | None,
        answer: str | None,
    ) -> UUID: ...

    @classmethod
    async def generate_hints(cls, question: str | None, answer: str) -> list[str] | None:
        return (
            await QuizzBase.generate_ai_hints(question, answer)
            if RequiresAI.configured
            else QuizzBase.generate_banana_hints(answer)
        )

    @classmethod
    async def generate_ai_hints(cls, question: str | None, answer: str) -> list[str] | None:
        assert AI_FLAGSHIP_MODEL
        run = await cls.agent.run(
            f'Create {cls.HINTS_COUNT} hints for the quiz answer, each offering gradually more '
            f'assistance.\n'
            f'Be careful not to disclose the answer directly, or offer any translation of it.',
            output_type=list[str],
            model=get_model(AI_FLAGSHIP_MODEL),
            deps=RunDeps(question, answer),
        )
        hints = run.output
        if len(hints) == cls.HINTS_COUNT:
            return hints

    @classmethod
    def generate_banana_hints(cls, answer: str) -> list[str] | None:
        max_hints = len(answer) // 2
        if max_hints == 0:
            return
        hint_interval = cls.HINTS_COUNT // max_hints
        hints = []
        hint = ['🍌'] * len(answer)
        for i in range(cls.HINTS_COUNT):
            if (i + 1) % hint_interval == 0:
                # Find indices where hint is still banana and choose one
                banana_mask = np.array([c == '🍌' for c in hint])
                banana_indices = np.where(banana_mask)[0]
                r = _RNG.choice(banana_indices)
                hint[r] = answer[r]
            hints.append(''.join(hint))
        return hints

    async def get_embed(self, game_id: UUID) -> Embed:
        resp = await get_nanapi().quizz.quizz_get_game(game_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        game = resp.result
        channel = self.bot.get_channel(self.channel_id)
        assert isinstance(channel, discord.TextChannel)
        author = channel.guild.get_member(int(game.quizz.author.discord_id))

        description = game.quizz.question or ''
        if game.quizz.attachment_url:
            description = f'{description}\n{game.quizz.attachment_url}'.strip()

        if author is not None:
            embed = Embed(colour=author.color, description=description)
            embed.set_author(name=author, icon_url=author.display_avatar)
        else:
            embed = Embed(description=description)

        embed.set_footer(text=f'[{game_id}] #{channel} — {game.status.capitalize()}')

        if (answer := game.quizz.answer) is not None:
            displayed_answer = (
                answer.replace('`', "'")
                if game.status is QuizzStatus.ENDED
                else '🍌' * len(answer)
            )
            embed.add_field(name='Answer', value=f'||`{displayed_answer}`||')

        if game.status is QuizzStatus.ENDED and game.winner is not None:
            winner = self.bot.get_user(int(game.winner.discord_id))
            assert winner is not None
            embed.add_field(name='Solved by', value=f'{winner.mention}')

        embed.set_image(url=game.quizz.attachment_url)

        return embed

    @classmethod
    async def try_validate(cls, question: str | None, answer: str | None, submission: str) -> bool:
        return False

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        resp = await get_nanapi().quizz.quizz_get_game(game_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        game = resp.result
        game_msg = await message.channel.fetch_message(int(game.message_id))

        if message.author.id == int(game.quizz.author.discord_id):
            return

        elapsed_time = (message.created_at - game_msg.created_at).total_seconds()

        author_nb = round(self.REWARD * elapsed_time / (24 * 3600))
        author_nb = min(author_nb, self.REWARD)
        answer_nb = self.REWARD - author_nb

        waifu_cog = cast(WaifuCollection, self.bot.get_cog(WaifuCollection.__cog_name__))

        quizz_author = self.bot.get_user(int(game.quizz.author.discord_id))
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
        answer: str | None,
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
        if answer is None and SAUCENAO_API_KEY is not None:
            answer = await self.saucenao(url)
        hints = await self.generate_hints(question, answer) if answer is not None else None
        body = NewQuizzBody(
            channel_id=str(self.channel_id),
            attachment_url=url,
            answer=answer,
            hints=hints,
            author_discord_id=str(author.id),
            author_discord_username=str(author),
        )
        resp = await get_nanapi().quizz.quizz_new_quizz(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        quizz = resp.result
        return quizz.id

    @staticmethod
    async def saucenao(attachment_url: str) -> str | None:
        resp = await saucenao_lookup(attachment_url, priority=[21, 37])
        for sauce in resp:
            if sauce.similarity > 60 and sauce.mal_id is not None:
                return sauce.title

    @classmethod
    async def try_validate(cls, question: str | None, answer: str | None, submission: str):
        fuzzy = (
            await asyncio.to_thread(cls.fuzzy_jp_match, answer, submission)
            if answer is not None
            else False
        )
        return fuzzy or await super().try_validate(question, answer, submission)

    @staticmethod
    def fuzzy_jp_match(reference: str, answer: str) -> bool:
        """Black magic, I don't remember how it worked"""
        reference = re.sub(r'\(\d+\)', '', reference)
        reference = reference.translate(str.maketrans('', '', string.punctuation))
        reference = reference.casefold()
        reference = unicodedata.normalize('NFKD', reference)
        reference = reference.encode('ascii', 'ignore').decode()

        reference_reg = AnimeMangaQuizz.romaji_regex(reference)
        reference_reg = reference_reg.replace(' ', '')

        answer = answer.translate(str.maketrans('', '', string.punctuation + ' '))
        answer = answer.casefold()
        answer = unicodedata.normalize('NFKD', answer)
        answer = answer.encode('ascii', 'ignore').decode()

        return bool(re.search(reference_reg, answer))

    @staticmethod
    def romaji_regex(title: str) -> str:
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

    async def post_end(self, game_id: UUID, message: discord.Message | MultiplexingMessage):
        await super().post_end(game_id, message)
        nb = _RNG.integers(1, 13)
        reply = await message.reply(f'{PREFIX}im{nb * "a"}ge {message.author.mention}')
        await self.imaaage(reply, nb)

    @staticmethod
    async def imaaage(message: discord.Message | MultiplexingMessage, nb: int = 1):
        with Image.open(
            resources.open_binary(nanachan.resources, f'image{_RNG.integers(1, 4):02}.jpg')
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
        answer: str | None,
    ):
        url = (await to_producer(attachment.url))['url'] if attachment is not None else None
        hints = await self.generate_hints(question, answer) if answer is not None else None
        body = NewQuizzBody(
            channel_id=str(self.channel_id),
            question=question,
            attachment_url=url,
            answer=answer,
            hints=hints,
            author_discord_id=str(author.id),
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

    @staticmethod
    async def kininarimasu(channel: 'MessageableChannel'):
        with resources.path(nanachan.resources, f'hyouka{_RNG.integers(1, 8):02}.gif') as path:
            await channel.send(file=discord.File(path))
