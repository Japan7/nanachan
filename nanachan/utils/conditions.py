from __future__ import annotations

import abc
import asyncio
import json
import logging
import random
import re
from contextlib import suppress
from dataclasses import asdict, dataclass
from enum import Enum, auto
from functools import cached_property
from typing import TYPE_CHECKING, Any, Type, cast

from discord.abc import Messageable
from discord.member import Member
from discord.user import User

from nanachan.redis.base import get_redis, make_redis_key
from nanachan.utils.misc import json_dumps

if TYPE_CHECKING:
    from nanachan.discord.helpers import MultiplexingContext
    from nanachan.extensions.waicolle import WaifuCollection

logger = logging.getLogger(__name__)


REDIS_KEY = make_redis_key('drop_conditions')


class ConditionStatus(Enum):
    REWARD = auto()
    FAIL = auto()
    IGNORE = auto()


class Conditions:
    def __init__(self, condition_classes: dict[str, Type[Condition]] | None = None):
        self.condition_classes: dict[str, Type[Condition]]
        if condition_classes is None:
            self.condition_classes = {}
        else:
            self.condition_classes = condition_classes.copy()

        self.active_conditions: list[Condition] = []
        self.ready = asyncio.Event()

    async def matching_conditions(self, ctx: MultiplexingContext):
        await self.ready.wait()
        for condition in self.active_conditions:
            try:
                cond_status = await condition.check(ctx)

                if cond_status in (ConditionStatus.REWARD, ConditionStatus.FAIL):
                    yield cond_status, condition

            except Exception as e:
                logger.exception(e)

    async def __call__(self, ctx: MultiplexingContext, waifu_cog: WaifuCollection):
        await self.ready.wait()
        async for cond_status, condition in self.matching_conditions(ctx):
            try:
                async with condition:
                    if cond_status is ConditionStatus.REWARD:
                        await condition.reward(ctx)
                    elif cond_status is ConditionStatus.FAIL:
                        await condition.fail(ctx)

                member = json_dumps(condition.serialize()).encode()
                redis = await get_redis()
                if redis is not None:
                    await redis.srem(REDIS_KEY, member)

            except Exception as e:
                logger.exception(e)

        for cls in self.condition_classes.values():
            try:
                if await cls.instanciation_condition(ctx, waifu_cog):
                    cond = await cls.instanciate(ctx, waifu_cog)
                    self.active_conditions.append(cond)

                    member = json_dumps(cond.serialize()).encode()
                    redis = await get_redis()
                    if redis is not None:
                        await redis.sadd(REDIS_KEY, member)

                    await cond.announce_rules(ctx, waifu_cog)
            except Exception as e:
                logger.exception(e)

    async def load_conditions(self, waifu_cog: WaifuCollection):
        redis = await get_redis()
        if redis is None:
            return

        for condition_arguments in await redis.smembers(REDIS_KEY):
            try:
                args = json.loads(condition_arguments)
                cond_cls = self.condition_classes[args['condition_name']]
                condition = await cond_cls.deserialize(waifu_cog=waifu_cog, **args)
                self.active_conditions.append(condition)
            except Exception as e:
                logger.exception(e)

        self.ready.set()

    def condition(self, condition_class: Type[Condition]):
        name = condition_class._condition_name
        self.condition_classes[name] = condition_class
        return condition_class


conditional_drop = Conditions()


class ConditionDisabled(Exception):
    pass


class Condition(abc.ABC):
    _condition_name: str

    def __init_subclass__(cls, name: str | None = None):
        cls._condition_name = cls.__name__ if name is None else name

    def serialize(self) -> dict[str, Any]:
        return {'condition_name': self._condition_name}

    @classmethod
    @abc.abstractmethod
    async def deserialize(cls, waifu_cog, **kwargs) -> Condition:
        pass

    def __init__(self, waifu_cog: WaifuCollection):
        self.waifu_cog = waifu_cog
        self.lock = asyncio.Lock()
        self.disabled = False

    async def __aenter__(self):
        await self.lock.acquire()
        if self.disabled:
            raise ConditionDisabled()

    async def __aexit__(self, *args):
        self.lock.release()
        await self.disable()

    @abc.abstractmethod
    async def announce_rules(self, ctx: MultiplexingContext, waifu_cog: WaifuCollection):
        pass

    @classmethod
    @abc.abstractmethod
    async def instanciate(cls, ctx: MultiplexingContext, waifu_cog: WaifuCollection) -> Condition:
        pass

    @classmethod
    @abc.abstractmethod
    async def instanciation_condition(
        cls, ctx: MultiplexingContext, waifu_cog: WaifuCollection
    ) -> bool:
        pass

    @abc.abstractmethod
    async def check(self, ctx: MultiplexingContext) -> ConditionStatus:
        pass

    @abc.abstractmethod
    async def reward(self, ctx: MultiplexingContext) -> None:
        pass

    @abc.abstractmethod
    async def fail(self, ctx: MultiplexingContext) -> None:
        pass

    async def disable(self):
        self.disabled = True


@dataclass(frozen=True)
class Word:
    regex_str: str
    rule: str
    action: str

    @cached_property
    def regex(self):
        return re.compile(self.regex_str, re.IGNORECASE)

    @classmethod
    def simple(cls, word: str):
        return cls(rf'\b{word}\b', f"says '{word}'", f"said '{word}'")

    @classmethod
    def singular(cls, word: str):
        return cls(rf'\b{word}s?\b', f"says '{word}'", f"said '{word}'")


UNLIMITED_DROP_WORKS = 'I am the Bone of my Roll Steel is my Body and Fire is my Blood. I have created over a Thousand moecoins, Unknown to Death, Nor known to Life. Have withstood Pain to create many Collages Yet those Hands will never hold Mai Waifu. So, as I Pray-- Unlimited Drop Works'  # noqa: E501


@conditional_drop.condition
class StringCondition(Condition):
    instances_lock = asyncio.Lock()
    available_instances = 18
    words = [
        Word(r'NAAA+M', 'prays to the God of Waicolle', 'prayed to the God of Waicolle'),
        Word('a(ya){5}(ya)*', 'says ayaya like Bao would', 'said ayaya like Bao would'),
        Word.simple('cringe'),
        Word(r'copium', 'inhales copium', 'inhaled copium'),
        Word.simple('Jeanjean'),
        Word.singular('pizza'),
        Word.singular('situation'),
        Word.simple('peepoShake'),
        Word.simple('Linux'),
        Word.singular('stream'),
        Word.simple('anas'),
        Word(
            UNLIMITED_DROP_WORKS.replace(' ', r'\s'),
            'invokes the Unlimited Drop Works',
            'invoked the Unlimited Drop Works',
        ),
        Word.simple('NamHappy'),
        Word(re.escape('?'), "says '?'", "said '?'"),
        Word(re.escape('.'), "says '.'", "said '.'"),
        Word(r':\w*oof:', 'uses a oof emote', 'used a oof emote'),
        Word.simple('du coup'),
        Word.simple('en vrai'),
        Word.singular('drop'),
        Word.simple('well'),
        Word(r'\bmonkey\b|🐒', "says 'monkey'", "said 'monkey'"),
        Word(r':(?:deadinside|(?:nana|eilene)ded):', 'is dead', 'is dead'),
        Word(r':\w*clap\w*:|👏', 'claps', 'clapped'),
        Word.simple('yuniiZOOM'),
        Word.simple('OkayuSad'),
        Word.simple('pepeLoser'),
        Word.simple('hype'),
        Word.simple('1'),
        Word.singular('edge'),
        Word.singular('genre'),
        Word(r'proj(?:o|ection)', 'talks about a projection', 'talked about a projection'),
        Word.simple('mahjong'),
        Word(r'kara(?:\b|oke)', 'talks about a karaoke', 'talked about a karaoke'),
        Word.simple('quizz'),
        Word(r'g[iî]te|🏚️|house_abandoned', "says 'gîte'", "said 'gîte'"),
        Word.simple('nice'),
        Word.singular('waifu'),
        Word(r'curry', "says 'curry'", "said 'curry'"),
        Word.simple('Kek'),
        Word.singular('pied'),
        Word('loli', 'says the forbidden word', 'said the forbidden word'),
        Word.simple('AMQ'),
        Word.simple('Odrian'),
        Word.simple('45minutes'),
        Word(r':(?:poggies|Crab(?:heart|agarre)):', 'summons a Crab', 'summoned a mighty Crab'),
        Word.singular('ascend'),
        Word.simple('statistiquement'),
        Word.simple('littéralement'),
        Word.simple('n7'),
        Word(r'\bmp\b', "says 'MP'", "said 'MP'"),
        Word(r'b[eé]bou', "says 'bébou'", "said 'bébou'"),
        Word.simple('RetourneParDomien'),
        Word(r'herbe', 'touches grass', 'touched grass'),
        Word.singular('flemme'),
        Word.singular('moecoin'),
        Word(r':(?:saladedefruits|slddfrts):', 'orders an ice cream', 'ordered an ice cream'),
        Word.simple('terrible'),
        Word.simple('Umineko'),
        Word.simple('Xenoblade'),
        Word.simple("Don't."),
        Word.singular('rousse'),
        Word.simple('lewd'),
        Word.simple('bad'),
        Word.simple('escalade'),
        Word(r'\brats*\b|surmulot', "says 'rat'", "said 'rat'"),
        Word(r'race_car|raced|🏎', 'gets raced', 'got raced'),
        Word(r'\bsus\w*\b|among us|amogus', 'is sus', 'was sus'),
        Word(r'sub(?:\b|way)', 'talks about a sub', 'talked about a sub'),
        Word.simple('Milgram'),
        Word.simple('NamFist'),
        Word.simple('Symphogear'),
        Word(r'jo(gogo|dodo)', 'claps with one hand', 'clapped with one hand'),
        Word(r':\w*sip:', 'drinks a tasty beverage', 'drank a tasty beverage'),
        Word(
            r'\b(?:'
            r'(?:Open)?(?<!j\')AI|IA|ML|(?:Chat)?GPT|Mistral|'
            r'LLa?MA?\d?|Copilot|Gemini|Bing Chat|'
            r'(?:Py)?Torch|Tensor(?:Flow)?|TF|NVIDIA|CUDA|'
            r'aller [àa] la salle'
            r')\b',
            'talks about AI',
            'talked about AI',
        ),
    ]

    def __init__(self, waifu_cog: WaifuCollection, user: User | Member, word: Word):
        super().__init__(waifu_cog)
        self.user = user
        self.word = word
        with suppress(ValueError):
            self.__class__.words.remove(word)
        self.__class__.available_instances -= 1

    def serialize(self) -> dict[str, Any]:
        obj = super().serialize()
        obj['user_id'] = self.user.id
        obj['word'] = asdict(self.word)
        return obj

    @classmethod
    async def deserialize(
        cls, waifu_cog: WaifuCollection, *, user_id: int, word: dict[str, str], **kwargs
    ) -> StringCondition:
        user = waifu_cog.bot.get_user(user_id)
        if user is None:
            user = await waifu_cog.bot.fetch_user(user_id)

        word_dc = Word(**word)
        return cls(user=user, word=word_dc, waifu_cog=waifu_cog)

    async def announce_rules(self, ctx: MultiplexingContext, waifu_cog: WaifuCollection):
        await self.user.send(self.rules)

    @property
    def rules(self):
        return (
            f'**[WaiColle]** If another player {self.word.rule} you get 1 drop.\n'
            '(If you say it yourself you lose the drop)'
        )

    @classmethod
    async def instanciation_condition(cls, ctx, *args, **kwargs) -> bool:
        return random.random() < 1 / 250 and cls.available_instances > 0

    @classmethod
    async def instanciate(cls, ctx: MultiplexingContext, waifu_cog: WaifuCollection):
        async with cls.instances_lock:
            if cls.words:
                i = random.randrange(len(cls.words))
                w = cls.words[i]
                return cls(user=ctx.author, word=w, waifu_cog=waifu_cog)
            else:
                raise RuntimeError('No more conditional words available')

    async def check(self, ctx: MultiplexingContext):
        if self.disabled:
            return ConditionStatus.IGNORE

        if self.word.regex.search(ctx.message.clean_content):
            if ctx.author.id == self.user.id:
                return ConditionStatus.FAIL
            return ConditionStatus.REWARD

        return ConditionStatus.IGNORE

    async def disable(self):
        await super().disable()
        self.__class__.words.append(self.word)  # readd word to word pool

    async def send_reward(self, ctx: MultiplexingContext, nb: int):
        bot_room = self.waifu_cog.bot.get_bot_room()
        bot_room = cast(Messageable, bot_room)
        await bot_room.send(f'**{ctx.author}** {self.word.action}', embed=ctx.message.quote_embed)
        await self.waifu_cog._drop(
            self.user,
            f'Conditional drop: {ctx.author} {self.word.action}',
            nb=nb,
            pool_player=ctx.author,
            rollop_reason='conditional',
        )
        self.__class__.available_instances += 1

    async def fail(self, ctx: MultiplexingContext):
        with suppress(Exception):
            await ctx.author.send(f'You {self.word.action}.\nYou lost the drop.')
        await self.send_reward(ctx, 0)

    async def reward(self, ctx: MultiplexingContext):
        await self.send_reward(ctx, 1)
