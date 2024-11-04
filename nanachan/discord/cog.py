from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

from discord.ext import commands as cmd

from nanachan.settings import SLASH_PREFIX

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot
    from nanachan.utils.settings import RequiredSettings


class CogMeta(cmd.CogMeta):

    def __new__(
        cls,
        *args,
        group_name: str | None = None,
        required_settings: RequiredSettings | None = None,
        **kwargs,
    ):
        name, bases, attrs = args
        if group_name is not None:
            kwargs['group_name'] = SLASH_PREFIX + group_name

        attrs['__required_settings__'] = required_settings
        return super().__new__(cls, name, bases, attrs, **kwargs)


class CogDescriptionMixin:

    @property
    def _cog_description(self):
        return self.__doc__


class CogGetCogMixin:
    __cog_name__: str

    @classmethod
    def get_cog(cls, bot: Bot) -> Self | None:
        return cast(Self | None, bot.get_cog(cls.__cog_name__))


class Cog(cmd.Cog, CogDescriptionMixin, CogGetCogMixin, metaclass=CogMeta):
    __required_settings__: RequiredSettings | None
    emoji: str

    def __init__(self, bot: Bot):
        self.bot = bot


class NanaGroupCog(cmd.GroupCog, CogDescriptionMixin, CogGetCogMixin, metaclass=CogMeta):
    __required_settings__: RequiredSettings | None
