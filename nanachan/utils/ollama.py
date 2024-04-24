from collections.abc import AsyncIterator
from typing import Literal, overload

from ollama import AsyncClient, ChatResponse, GenerateResponse, Message

from nanachan.settings import OLLAMA_HOST, OLLAMA_MODEL


class OllamaClient(AsyncClient):
    SYSTEM_PROMPT = """
    You are a Discord bot for the Japan7 club.
    You like Japanese culture, anime, music and games.
    You are also knowledgeable about technical stuff, including programming and Linux.
    Your replies are short and to the point.
    """

    def __init__(self, host: str | None = OLLAMA_HOST, **kwargs) -> None:
        super().__init__(host, **kwargs)

    @overload
    async def generate_typed(
        self,
        prompt: str,
        *,
        stream: Literal[False],
        system: str = SYSTEM_PROMPT,
    ) -> GenerateResponse: ...

    @overload
    async def generate_typed(
        self,
        prompt: str,
        *,
        stream: Literal[True],
        system: str = SYSTEM_PROMPT,
    ) -> AsyncIterator[GenerateResponse]: ...

    async def generate_typed(
        self,
        prompt: str,
        *,
        stream: bool,
        system: str = SYSTEM_PROMPT,
    ):
        resp = await self.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            stream=stream,
            system=system,
        )
        return resp

    @overload
    async def chat_typed(
        self,
        messages: list[Message],
        *,
        stream: Literal[False],
        system: str = SYSTEM_PROMPT,
    ) -> ChatResponse: ...

    @overload
    async def chat_typed(
        self,
        messages: list[Message],
        *,
        stream: Literal[True],
        system: str = SYSTEM_PROMPT,
    ) -> AsyncIterator[ChatResponse]: ...

    async def chat_typed(
        self,
        messages: list[Message],
        *,
        stream: bool,
        system: str = SYSTEM_PROMPT,
    ):
        if system:
            messages = [Message(role='system', content=system)] + messages
        resp = await self.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=stream,
        )
        return resp
