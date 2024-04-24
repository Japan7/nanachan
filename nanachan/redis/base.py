import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

import backoff
import orjson
from redis import asyncio as aioredis

from nanachan.settings import REDIS_HOST, REDIS_KWARGS, REDIS_PORT, TOKEN
from nanachan.utils.misc import print_exc

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | bool | None = False


@backoff.on_exception(backoff.expo, Exception, max_time=3600*12)
async def get_redis() -> aioredis.Redis | None:
    global _redis

    if _redis is False:
        if REDIS_HOST is not None:
            pool = aioredis.BlockingConnectionPool(host=REDIS_HOST,
                                                   port=REDIS_PORT)
            _redis = await aioredis.Redis(connection_pool=pool, **REDIS_KWARGS)
        else:
            logger.info(
                "Redis is not set up, cache won't persist between restarts")
            _redis = None

    return cast(aioredis.Redis | None, _redis)


token_hash = hashlib.sha256(TOKEN.encode()).hexdigest()

redis_queue: asyncio.Queue | None = None
redis_queue_lock = asyncio.Lock()


def make_redis_key(key: str):
    return f"{token_hash}_{key}"


def redis_submit(coro):
    global redis_queue

    if redis_queue is None:
        redis_queue = asyncio.Queue()
        for _ in range(10):
            asyncio.create_task(redis_loop())

    fut = asyncio.get_running_loop().create_future()
    redis_queue.put_nowait((fut, coro))
    return fut


async def redis_loop():
    while redis_queue is not None:
        future, coro = await redis_queue.get()
        future.set_result(await coro)


SubKeyType = str | int | None


class BaseRedis[T](ABC):
    key: str
    values: dict[SubKeyType, bytes | None]

    def __init__(self, key: str, global_key: bool = False):
        if global_key:
            self.key = key
        else:
            self.key = make_redis_key(key)
        self.values = defaultdict(lambda: None)

    async def get(self, sub_key: SubKeyType = None) -> T | None:
        key = self.key if sub_key is None else f"{self.key}:{sub_key}"

        if self.values[sub_key] is None:
            redis = await get_redis()
            if redis is not None:
                try:
                    async with asyncio.timeout(5):
                        return self._decode(await redis.get(key))
                except Exception:
                    print_exc()
                    return

        return self._decode(self.values[sub_key])

    async def set(self,
                  value: T,
                  sub_key: SubKeyType = None,
                  expire: int | None = None,
                  **kwargs):
        key = self.key if sub_key is None else f"{self.key}:{sub_key}"

        if expire is not None:
            kwargs['ex'] = expire

        encoded_value = self.encode(value)
        self.values[sub_key] = encoded_value

        redis = await get_redis()

        if redis is not None:
            asyncio.get_running_loop().create_task(
                redis.set(key, encoded_value, **kwargs)
            )

    async def expire_at(self, when: datetime, sub_key: SubKeyType = None):
        key = self.key if sub_key is None else f"{self.key}:{sub_key}"
        redis = await get_redis()

        if redis is None:
            return
        await redis.expireat(key, when)

    async def delete(self, sub_key: SubKeyType = None):
        key = self.key if sub_key is None else f"{self.key}:{sub_key}"
        redis = await get_redis()

        del self.values[sub_key]
        if redis is not None:
            await redis.delete(key)

    async def get_all(self):
        # TODO: make it work when redis disconnect ig
        redis = await get_redis()

        if redis is not None:
            keys = [s.decode() for s in await redis.keys(f"{self.key}:*")]
            for key in keys:
                *_, sub_key = key.rpartition(":")
                yield sub_key, await self.get(sub_key)

    @abstractmethod
    def encode(self, value: T) -> bytes:
        pass

    def _decode(self, value: bytes | None) -> T | None:
        if value is None:
            return value

        return self.decode(value)

    @abstractmethod
    def decode(self, value: bytes) -> T:
        pass


class _StringValueMixin:

    def encode(self, value: str) -> bytes:
        return value.encode()

    def decode(self, value: bytes) -> str:
        return value.decode()


class StringValue(_StringValueMixin, BaseRedis[str]):
    pass


class _IntegerLikeValue(BaseRedis[int]):
    BYTEORDER = 'big'

    def __init__(self,
                 key: str,
                 int_bytes: int = 4,
                 signed: bool = True,
                 **kwargs):
        super().__init__(key, **kwargs)
        self.int_bytes = int_bytes
        self.signed = signed

    def encode(self, value: int) -> bytes:
        return value.to_bytes(self.int_bytes,
                              byteorder=self.BYTEORDER,
                              signed=self.signed)

    def decode(self, value: bytes) -> int:
        return int.from_bytes(value,
                              byteorder=self.BYTEORDER,
                              signed=self.signed)


class IntegerValue(_IntegerLikeValue):
    pass


class TruncatedFloatValue(_IntegerLikeValue):

    def encode(self, value: float | int) -> bytes:
        return super().encode(int(value))


class FloatValue(BaseRedis[float]):

    def encode(self, value: float) -> bytes:
        return str(value).encode()

    def decode(self, value: bytes) -> float:
        return float(value.decode())


class BooleanValue(BaseRedis[bool]):

    def __init__(self, key: str, default: bool = False, **kwargs):
        super().__init__(key, **kwargs)
        self.default = default

    def encode(self, value: bool) -> bytes:
        return int(value).to_bytes()

    def decode(self, value: bytes) -> bool:
        return bool(int.from_bytes(value))

    def _decode(self, value: bytes | None):
        if value is None:
            return self.default

        return super()._decode(value)


class JSONValue(BaseRedis[Any]):

    def __init__(self, key: str, global_key: bool = False, **orjson_kwargs):
        super().__init__(key, global_key)
        self.orjson_kwargs = orjson_kwargs

    def encode(self, value: Any) -> bytes:
        return orjson.dumps(value, **self.orjson_kwargs)

    def decode(self, value: bytes) -> Any:
        return orjson.loads(value)
