from __future__ import annotations

from typing import Self, cast

from discord.ext import commands as cmd

from nanachan.discord.bot import Bot
from nanachan.settings import SLASH_PREFIX


class CogMeta(cmd.CogMeta):

    def __new__(cls, *args, group_name: str | None = None, **kwargs):
        if group_name is not None:
            kwargs['group_name'] = SLASH_PREFIX + group_name

        return super().__new__(cls, *args, **kwargs)


class CogDescriptionMixin:

    @property
    def _cog_description(self):
        return self.__doc__


class CogGetCogMixin:
    __cog_name__: str

    @classmethod
    def get_cog(cls, bot: Bot) -> Self | None:
        return cast(cls | None, bot.get_cog(cls.__cog_name__))


class Cog(cmd.Cog, CogDescriptionMixin, CogGetCogMixin, metaclass=CogMeta):
    emoji: str

    def __init__(self, bot: Bot):
        self.bot = bot


class NanaGroupCog(cmd.GroupCog, CogDescriptionMixin, CogGetCogMixin, metaclass=CogMeta):
    pass
