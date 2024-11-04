from __future__ import annotations

import asyncio
import itertools
import logging
import unicodedata
from dataclasses import asdict
from functools import partial
from inspect import signature
from itertools import batched, zip_longest
from math import ceil
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Iterable,
    Sequence,
    override,
)

import discord
from discord.components import SelectOption
from discord.enums import ButtonStyle
from discord.ui import Button, Item, Select, View

from nanachan.discord.helpers import Embed, EmbedField, UserType
from nanachan.discord.reactions import Pages
from nanachan.utils.misc import async_all

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot


logger = logging.getLogger(__name__)

LETTERS_EMOJIS = [
    unicodedata.lookup(f'REGIONAL INDICATOR SYMBOL LETTER {chr(letter)}')
    for letter in range(ord('A'),
                        ord('Z') + 1)
]


#########
# Views #
#########
class BaseView(View):

    def __init__(self, bot: Bot, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.bot = bot


class LockedView(BaseView):

    def __init__(self, bot: Bot, lock: UserType | None = None, timeout: float | None = None):
        super().__init__(bot, timeout=timeout)
        self.lock = lock.id if lock is not None else None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self.lock is None or interaction.user.id == self.lock


class BaseConfirmationView(BaseView):
    ACCEPT_EMOTE = 'FubukiGO'
    REFUSE_EMOTE = 'FubukiStop'

    def __init__(self,
                 bot: Bot,
                 timeout: float | None = None,
                 accept_custom_id: str | None = None,
                 refuse_custom_id: str | None = None):
        super().__init__(bot=bot, timeout=timeout)
        self.accept_bt = Button(emoji=self.bot.get_nana_emoji(self.ACCEPT_EMOTE),
                                style=ButtonStyle.green,
                                custom_id=accept_custom_id)
        self.accept_bt.callback = self.accept

        self.refuse_bt = Button(emoji=self.bot.get_nana_emoji(self.REFUSE_EMOTE),
                                style=ButtonStyle.red,
                                custom_id=refuse_custom_id)
        self.refuse_bt.callback = self.refuse

        self.add_item(self.accept_bt)
        self.add_item(self.refuse_bt)

    async def accept(self, interaction: discord.Interaction) -> None:
        raise RuntimeError("Not Implemented")  # can't use ABC, just be a good citizen

    async def refuse(self, interaction: discord.Interaction) -> None:
        raise RuntimeError("Not Implemented")  # can't use ABC, just be a good citizen


class ConfirmationView(BaseConfirmationView):

    def __init__(self,
                 bot: Bot,
                 yes_user: UserType | None = None,
                 no_user: UserType | None = None,
                 timeout: float | None = None,
                 delete_after: bool = False):
        super().__init__(bot=bot, timeout=timeout)
        self.yes_user = yes_user
        self.no_user = no_user
        self.confirmation: asyncio.Future = self.bot.loop.create_future()
        self.interaction: asyncio.Future = self.bot.loop.create_future()
        self.delete_after = delete_after

    async def accept(self, interaction: discord.Interaction):
        if self.yes_user is None or interaction.user == self.yes_user:
            await self._unregister(interaction)
            self.confirmation.set_result(True)
            self.interaction.set_result(interaction)

    async def refuse(self, interaction: discord.Interaction):
        no_lock = self.yes_user is None and self.no_user is None
        if no_lock or interaction.user in (self.yes_user, self.no_user):
            await self._unregister(interaction)
            self.confirmation.set_result(False)
            self.interaction.set_result(interaction)

    async def _unregister(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        self.stop()
        if self.delete_after:
            asyncio.create_task(interaction.delete_original_response())

    async def on_timeout(self):
        if not self.confirmation.done():
            self.confirmation.set_result(False)


##############
# Navigators #
##############
class Refreshable:
    refresh: Callable[[int], Coroutine[Any, Any, None]]


class RefreshableButton(Button, Refreshable):
    pass


class RefreshableSelect(Select, Refreshable):
    pass


class NavigatorView(BaseView):
    """View replacement for PaginatedMessage"""
    PREV_EMOJI = '⬅️'
    NEXT_EMOJI = '➡️'

    def __init__(self,
                 bot: Bot,
                 pages: Pages,
                 named_buttons: bool = False,
                 hide_jumper: bool = False,
                 timeout: float | None = None):
        super().__init__(bot, timeout=timeout)
        self.pages = pages
        self.displayed_page = 0

        self.named_buttons = named_buttons
        self.hide_jumper = hide_jumper

        self.prev_page_bt = RefreshableButton(emoji=self.PREV_EMOJI,
                                              style=ButtonStyle.grey,
                                              row=0)
        self.prev_page_bt.refresh = partial(self._nav_bt_refresh, self.prev_page_bt, -1)

        self.next_page_bt = RefreshableButton(emoji=self.NEXT_EMOJI,
                                              style=ButtonStyle.grey,
                                              row=0)
        self.next_page_bt.refresh = partial(self._nav_bt_refresh, self.next_page_bt, +1)

        self.jumper_select = RefreshableSelect(row=1)
        self.jumper_select.callback = self._jumper_callback
        self.jumper_select.refresh = self._jumper_refresh

        if len(self.pages) > 1:
            self.add_item(self.prev_page_bt)
            self.add_item(self.next_page_bt)

            if not self.hide_jumper:
                self.add_item(self.jumper_select)

    async def get_page(self, new_page: int) -> dict[str, Any]:
        return await self.pages.get_page(new_page)

    async def update_page(self, new_page: int, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.refresh_view(new_page)
        page = await self.get_page(new_page)
        if 'attachments' in page:
            for a in page['attachments']:
                a.reset()
        msg = await interaction.original_response()
        await msg.edit(**page, view=self)
        self.displayed_page = new_page

    async def refresh_view(self, new_page: int):
        for item in self.children:
            if isinstance(item, Refreshable):
                await item.refresh(new_page)

    async def _nav_bt_refresh(self, button: Button, inc: int, displayed_page: int):
        new_page = (displayed_page + inc) % len(self.pages)
        if self.named_buttons:
            next_name = await self.pages.get_name(new_page)
            if next_name is not None:
                button.label = next_name[:80]
        button.callback = partial(self.update_page, new_page)

    async def _jumper_refresh(self, displayed_page: int):
        jumper_min = max(0, displayed_page - 12)
        jumper_max = min(displayed_page + 12, len(self.pages) - 1)

        self.jumper_select.placeholder = (
            f"Jump between pages "
            f"#{jumper_min + self.pages.start_at} – #{jumper_max + self.pages.start_at}")

        jumper_range = range(jumper_min, jumper_max + 1)
        names = await asyncio.gather(*[self.pages.get_name(i) for i in jumper_range])

        options = []
        for i, name in zip(jumper_range, names):
            if name is not None:
                option = discord.SelectOption(label=name[:100],
                                              description=f"Page #{i + self.pages.start_at}",
                                              value=str(i))
            else:
                option = discord.SelectOption(label=f"Page #{i + self.pages.start_at}",
                                              value=str(i))
            options.append(option)

        self.jumper_select.options = options

    async def _jumper_callback(self, interaction: discord.Interaction):
        await self.update_page(int(self.jumper_select.values[0]), interaction)

    @classmethod
    async def create(cls,
                     bot: Bot,
                     send_function: Callable[..., Coroutine[Any, Any, Any]],
                     *,
                     pages: list[Any],
                     static_content: str | None = None,
                     start_at: int = 1,
                     prefetch_min_batch_size: int = 5,
                     prefetch_pages: int = 5,
                     **kwargs):

        pages_obj = Pages(pages,
                          static_content=static_content,
                          start_at=start_at,
                          prefetch_min_batch_size=prefetch_min_batch_size,
                          prefetch_pages=prefetch_pages)

        view = cls(bot, pages_obj, **kwargs)
        await view.refresh_view(0)

        page = await view.get_page(0)
        # FIXME:
        if 'attachments' in page and 'attachments' not in signature(send_function).parameters:
            page = page.copy()
            page['files'] = page.pop('attachments')

        logger.info(f"{view=}")
        sent: discord.Message | discord.WebhookMessage = await send_function(**page, view=view)

        return sent, view


class AutoNavigatorView(NavigatorView):
    """View replacement for PaginatedEmbed"""

    @classmethod
    def _split_pages(cls, description: str):
        curr_lines = ""
        split_description = description.strip().split('\n')

        for line in split_description:
            if len(curr_lines) + len(line) > 2048:
                yield curr_lines
                curr_lines = ""

            curr_lines += line + '\n'

        curr_lines = curr_lines.strip()
        if curr_lines:
            yield curr_lines

        if not description.strip():  # still create an embed if the description was empty
            yield None

    @classmethod
    def _create_pages(cls,
                      title: str | None = None,
                      description: str | None = None,
                      colour: int | discord.Colour | None = None,
                      color: int | discord.Colour | None = None,
                      url: str | None = None,
                      author_name: str | None = None,
                      author_url: str | None = None,
                      author_icon_url: str | None = None,
                      footer_text: str | None = None,
                      footer_icon_url: str | None = None,
                      image_url: str | None = None,
                      thumbnail_url: str | None = None,
                      fields: list[EmbedField] | None = None,
                      attachments: list[discord.File] | None = None,):
        if fields is None:
            fields = []

        if description is None:
            description = ""

        pages: list[dict[str, dict[str, Any]]] = []
        for page_desc, page_fields in zip_longest(cls._split_pages(description),
                                                  batched(fields, 24)):
            embed = Embed(title=title, description=page_desc, colour=colour, color=color, url=url)
            if author_name:
                embed.set_author(name=author_name, url=author_url, icon_url=author_icon_url)
            embed.set_footer(text=footer_text, icon_url=footer_icon_url)
            embed.set_image(url=image_url)
            embed.set_thumbnail(url=thumbnail_url)

            if page_fields is not None:
                for field in page_fields:
                    embed.add_field(**asdict(field))

            page: dict[str, Any] = dict(embed=embed)
            if attachments is not None:
                page['attachments'] = attachments
            pages.append(page)

        return pages

    @override
    @classmethod
    async def create(cls,
                     bot: Bot,
                     send_function: Callable[..., Coroutine[Any, Any, Any]],
                     *,
                     static_content: str | None = None,
                     start_at: int = 1,
                     prefetch_min_batch_size: int = 5,
                     prefetch_pages: int = 5,
                     title: str | None = None,
                     description: str | None = None,
                     colour: int | discord.Colour | None = None,
                     color: int | discord.Colour | None = None,
                     url: str | None = None,
                     author_name: str | None = None,
                     author_url: str | None = None,
                     author_icon_url: str | None = None,
                     footer_text: str | None = None,
                     footer_icon_url: str | None = None,
                     image_url: str | None = None,
                     thumbnail_url: str | None = None,
                     fields: list[EmbedField] | None = None,
                     attachments: list[discord.File] | None = None,
                     **kwargs):
        pages = cls._create_pages(title=title,
                                  description=description,
                                  colour=colour,
                                  color=color,
                                  url=url,
                                  author_name=author_name,
                                  author_url=author_url,
                                  author_icon_url=author_icon_url,
                                  footer_text=footer_text,
                                  footer_icon_url=footer_icon_url,
                                  image_url=image_url,
                                  thumbnail_url=thumbnail_url,
                                  fields=fields,
                                  attachments=attachments)
        return await super().create(bot,
                                    send_function,
                                    pages=pages,
                                    static_content=static_content,
                                    start_at=start_at,
                                    prefetch_min_batch_size=prefetch_min_batch_size,
                                    prefetch_pages=prefetch_pages,
                                    **kwargs)


##############
# Composites #
##############
def composite_init(composite, views: Sequence[View]):
    composite.views = views
    composite.view_stops = []
    composite.view_on_errors = []
    composite.view_on_timeouts = []
    composite_add_views(composite, views)


def composite_add_views(composite: BaseCompositeView, views: Iterable[View]):
    for view in views:
        composite.view_stops.append(view.stop)
        composite.view_on_errors.append(view.on_error)
        composite.view_on_timeouts.append(view.on_timeout)
        view.stop = composite.stop
        view.on_error = composite.on_error
        view.on_timeout = composite.on_timeout

        for item in view.children:
            composite.add_item(item)


def composite_stop(composite: BaseCompositeView):
    for view_stop in composite.view_stops:
        view_stop()


async def composite_on_error(composite: BaseCompositeView,
                             interaction: discord.Interaction,
                             error: Exception, item: Item):
    for view_on_error in composite.view_on_errors:
        await view_on_error(interaction, error, item)


async def composite_on_timeout(composite: BaseCompositeView):
    for view_on_timeout in composite.view_on_timeouts:
        await view_on_timeout()


async def composite_interaction_check(views: Iterable[View], interaction: discord.Interaction):
    return await async_all(await view.interaction_check(interaction) for view in views)


class BaseCompositeView(BaseView):
    views: Sequence[View]
    view_stops: list[Callable[[], None]]
    view_on_errors: list[Callable[[discord.Interaction, Exception, Item],
                                  Coroutine[Any, Any, None]]]
    view_on_timeouts: list[Callable[[], Coroutine[Any, Any, None]]]


class CompositeView(BaseCompositeView):

    def __init__(self, bot: Bot, *views, timeout: float | None = None):
        super().__init__(bot=bot, timeout=timeout)
        composite_init(self, views)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await composite_interaction_check(self.views, interaction)

    def stop(self):
        composite_stop(self)
        super().stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item):
        await composite_on_error(self, interaction, error, item)
        await super().on_error(interaction, error, item)

    async def on_timeout(self):
        await composite_on_timeout(self)
        await super().on_timeout()


class CompositeNavigatorView(NavigatorView, BaseCompositeView):

    def __init__(self,
                 bot: Bot,
                 *views,
                 pages: Pages,
                 named_buttons: bool = False,
                 hide_jumper: bool = False,
                 timeout: float | None = None):
        super().__init__(bot=bot,
                         pages=pages,
                         named_buttons=named_buttons,
                         hide_jumper=hide_jumper,
                         timeout=timeout)

        composite_init(self, views)

    async def interaction_check(self, interaction: discord.Interaction):
        return await composite_interaction_check(self.views, interaction)

    def stop(self):
        composite_stop(self)
        super().stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item):
        await composite_on_error(self, interaction, error, item)
        await super().on_error(interaction, error, item)

    async def on_timeout(self):
        await composite_on_timeout(self)
        await super().on_timeout()


class CompositeAutoNavigatorView(AutoNavigatorView, BaseCompositeView):

    def __init__(self,
                 bot: Bot,
                 *views,
                 pages: Pages,
                 named_buttons: bool = False,
                 hide_jumper: bool = False,
                 timeout: float | None = None):
        super().__init__(bot=bot,
                         pages=pages,
                         named_buttons=named_buttons,
                         hide_jumper=hide_jumper,
                         timeout=timeout)

        composite_init(self, views)

    async def interaction_check(self, interaction: discord.Interaction):
        return await composite_interaction_check(self.views, interaction)

    def stop(self):
        composite_stop(self)
        super().stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item):
        await composite_on_error(self, interaction, error, item)
        await super().on_error(interaction, error, item)

    async def on_timeout(self):
        await composite_on_timeout(self)
        await super().on_timeout()


#############
# Selectors #
#############
class ChoiceView(BaseView):
    """View replacement for Choice"""

    def __init__(self, bot: Bot, elements: list, callback: Callable, timeout: float | None = None):
        super().__init__(bot, timeout=timeout)
        self.elements = elements
        self.callback = callback

        self.choice_select = Select(options=[
            SelectOption(emoji=LETTERS_EMOJIS[i], label=str(e)[:100], value=str(i))
            for i, e in enumerate(self.elements[:25])
        ])
        self.choice_select.callback = self._choice_select_callback
        self.add_item(self.choice_select)

    async def _choice_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if len(self.choice_select.values) > 0:
            await interaction.delete_original_response()
            await self.callback(self.elements[int(self.choice_select.values[0])])


class StringSelectorView(CompositeNavigatorView):
    PER_PAGE_SELECTOR = 25

    def __init__(self,
                 bot: Bot,
                 pages: Pages,
                 strings: list[str],
                 kind: str,
                 lock: UserType,
                 timeout: float | None = None):
        self.confirmation_view = ConfirmationView(bot, yes_user=lock)
        components = [self.confirmation_view, LockedView(bot, lock=lock)]

        super().__init__(bot, *components, pages=pages, timeout=timeout)

        self.strings = strings
        self.selected_per_page = {}

        self.string_select = RefreshableSelect(placeholder=f'Select {kind}')
        self.string_select.callback = self.select_callback
        self.string_select.refresh = self._string_select_refresh
        self.add_item(self.string_select)

    @property
    def confirmation(self):
        return self.confirmation_view.confirmation

    async def _string_select_refresh(self, displayed_page: int):
        displayed_strings = self.strings[StringSelectorView.PER_PAGE_SELECTOR *
                                         displayed_page:StringSelectorView.PER_PAGE_SELECTOR *
                                         (displayed_page + 1)]

        string_range = range(StringSelectorView.PER_PAGE_SELECTOR * displayed_page,
                             StringSelectorView.PER_PAGE_SELECTOR * (displayed_page + 1))
        options = []
        for string, i in zip(displayed_strings, string_range):
            is_default = str(i) in self.selected_per_page.get(displayed_page, [])
            option = SelectOption(label=string[:100], description=f'#{i+1}', default=is_default)
            options.append(option)

        self.string_select.options = options
        self.string_select.max_values = len(displayed_strings)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected_per_page[self.displayed_page] = self.string_select.values

    @property
    def selected(self):
        return [
            string for string in itertools.chain.from_iterable(self.selected_per_page.values())
        ]

    @classmethod
    async def create(cls,
                     bot: Bot,
                     send_function: Callable,
                     *,
                     strings: list[Any],
                     kind: str,
                     owner: UserType,
                     capitalize: bool = True,
                     static_content: str | None = None,
                     start_at: int = 1,
                     prefetch_min_batch_size: int = 5,
                     prefetch_pages: int = 5,
                     **kwargs):

        pages = []
        for i_pages in range(ceil(len(strings) / StringSelectorView.PER_PAGE_SELECTOR)):
            embed = Embed(
                title=f'{kind.capitalize() if capitalize else kind} list',
                description='\n'.join(
                    strings[i_pages * StringSelectorView.PER_PAGE_SELECTOR:(i_pages + 1) *
                            StringSelectorView.PER_PAGE_SELECTOR]))
            embed.set_author(name=owner, icon_url=owner.display_avatar.url)
            pages.append({'embed': embed})

        pages_obj = Pages(pages,
                          static_content=static_content,
                          start_at=start_at,
                          prefetch_min_batch_size=prefetch_min_batch_size,
                          prefetch_pages=prefetch_pages)

        view = cls(bot, pages_obj, strings=strings, kind=kind, lock=owner, **kwargs)
        await view.refresh_view(0)

        page = await view.get_page(0)
        # FIXME:
        if 'attachments' in page and 'attachments' not in signature(send_function).parameters:
            page = page.copy()
            page['files'] = page.pop('attachments')
        sent: discord.Message | discord.WebhookMessage = await send_function(**page, view=view)

        return sent, view
