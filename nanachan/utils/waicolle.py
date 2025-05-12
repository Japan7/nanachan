import asyncio
import calendar
import itertools
import logging
import math
from collections import OrderedDict, defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from functools import partial
from itertools import batched
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import discord
import numpy as np
from discord.app_commands import Choice
from discord.components import SelectOption
from discord.ext import commands
from discord.ui import Button, Select
from yarl import URL

from nanachan.discord.bot import Bot
from nanachan.discord.helpers import Embed, UserType
from nanachan.discord.reactions import ReactionHandler, ReactionListener
from nanachan.discord.views import (
    LETTERS_EMOJIS,
    BaseConfirmationView,
    CompositeAutoNavigatorView,
    CompositeNavigatorView,
    CompositeView,
    ConfirmationView,
    LockedView,
    Pages,
    RefreshableButton,
    RefreshableSelect,
)
from nanachan.nanapi._client import Success
from nanachan.nanapi.client import Error, get_nanapi, success
from nanachan.nanapi.model import (
    BulkUpdateWaifusBody,
    CEdgeSelectFilterCharaResult,
    CharaSelectResult,
    MediaType,
    NewTradeBody,
    RollData,
    TradeSelectResult,
    WaicolleRank,
    WaifuSelectResult,
)
from nanachan.nanapi.model import Rank as _Rank
from nanachan.settings import NANAPI_PUBLIC_URL
from nanachan.utils.anilist import STAFF_GARBAGE
from nanachan.utils.misc import autocomplete_truncate

if TYPE_CHECKING:
    from nanachan.extensions.waicolle import WaifuCollection

logger = logging.getLogger(__name__)

WC_EMOJI = '👰‍♀️'
WC_COLOR = 0x956DA6

PER_PAGE_SELECTOR = 25

RNG = np.random.default_rng()


class WaifuDropReactionListener(ReactionListener):
    timeout = 30

    def __init__(self, cog: 'WaifuCollection', message: discord.Message):
        super().__init__(cog.bot, message)
        self.cog = cog
        self.users = set()
        self.queue = asyncio.Queue()
        self.on_add_reaction(self.drop)

    async def add_reactions(self):
        await super().add_reactions()
        logger.info(f'starting drop {self}')
        asyncio.get_running_loop().call_later(WaifuDropReactionListener.timeout, self.unregister)

    def unregister(self):
        logger.info(f'unregistering {self}')
        return super().unregister()

    @ReactionHandler.on_add_reaction(WC_EMOJI)
    async def drop(self, user: discord.User):
        if user not in self.users:
            logger.info(f'waifu drop: {user}')
            self.users.add(user)
            await self.queue.put(user)


class WaifuSelectorView(CompositeNavigatorView):
    def __init__(
        self, bot: Bot, pages: Pages, waifus: list[WaifuSelectResult], lock: discord.User
    ):
        self.confirmation_view = ConfirmationView(bot, yes_user=lock, delete_after=True)
        self.confirmation_view.accept_bt.row = 3
        self.confirmation_view.refuse_bt.row = 3
        components = [self.confirmation_view, LockedView(bot, lock=lock)]
        super().__init__(bot, *components, pages=pages, timeout=300)

        self.waifus = waifus
        self.selected_per_page = {}

        self.waifu_select = RefreshableSelect(placeholder='Select characters')
        self.waifu_select.callback = self.select_callback
        self.waifu_select.refresh = self._chara_select_refresh  # type: ignore
        self.add_item(self.waifu_select)

        self.stared = False
        self.star_button = Button(emoji='*️⃣', row=3)
        self.star_button.callback = self.star_callback
        self.add_item(self.star_button)
        self.children.insert(-3, self.children.pop())

    @property
    def confirmation(self):
        return self.confirmation_view.confirmation

    async def _chara_select_refresh(self, displayed_page: int):
        displayed_waifus = self.waifus[
            PER_PAGE_SELECTOR * displayed_page : PER_PAGE_SELECTOR * (displayed_page + 1)
        ]

        async with asyncio.TaskGroup() as tg:
            chara_ids = [w.character.id_al for w in displayed_waifus]
            resp_task = tg.create_task(
                get_nanapi().anilist.anilist_get_charas(','.join(map(str, chara_ids)))
            )
            edge_tasks = [(cid, tg.create_task(WaifuHelper.get_edges(cid))) for cid in chara_ids]

        resp = await resp_task
        if not success(resp):
            raise RuntimeError(resp.result)

        charas = {c.id_al: c for c in resp.result}
        edges = {cid: await task for cid, task in edge_tasks}

        waifu_range = range(
            PER_PAGE_SELECTOR * displayed_page, PER_PAGE_SELECTOR * (displayed_page + 1)
        )

        options_tasks = []
        async with asyncio.TaskGroup() as tg:
            for waifu, i in zip(displayed_waifus, waifu_range):
                chara = charas[waifu.character.id_al]
                edge = edges[waifu.character.id_al]
                is_default = str(i) in self.selected_per_page.get(displayed_page, [])
                option = WaifuTextHelper(waifu, chara, edge).get_select_option(
                    i + 1, value=str(i), default=is_default
                )
                options_tasks.append(tg.create_task(option))

        options = [await opt for opt in options_tasks]

        self.waifu_select.options = options
        self.waifu_select.max_values = len(displayed_waifus)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.selected_per_page[self.displayed_page] = self.waifu_select.values

    async def star_callback(self, interaction: discord.Interaction):
        if not self.stared:
            for i, part in enumerate(batched(self.waifus, PER_PAGE_SELECTOR)):
                self.selected_per_page[i] = [
                    str(i * PER_PAGE_SELECTOR + j) for j in range(len(part))
                ]
        else:
            self.selected_per_page = {}
        self.stared = not self.stared
        await self._chara_select_refresh(self.displayed_page)
        await interaction.response.edit_message(view=self)

    @property
    def selected(self):
        return [
            self.waifus[int(cast(str, i))]
            for i in sorted(set(itertools.chain.from_iterable(self.selected_per_page.values())))
        ]


class RollSelectorView(CompositeView):
    def __init__(
        self,
        bot: Bot,
        yes_user: UserType,
        rolls: list[RollData],
        timeout: float | int | None = None,
    ):
        self.confirmation_view = ConfirmationView(
            bot, yes_user=yes_user, timeout=timeout, delete_after=True
        )
        views = [self.confirmation_view, LockedView(bot, lock=yes_user)]
        super().__init__(bot, *views)

        self.confirmation_view.accept_bt.disabled = True

        self.rolls = rolls

        self.options = [
            discord.SelectOption(
                emoji=LETTERS_EMOJIS[i],
                label=roll.name,
                description=f'{roll.price} moecoins',
                value=str(i),
            )
            for i, roll in enumerate(self.rolls)
        ]
        self.roll_select = Select(placeholder='Select roll option', options=self.options)
        self.roll_select.callback = self._select_callback
        self.add_item(self.roll_select)

    async def _select_callback(self, interaction: discord.Interaction):
        self.confirmation_view.accept_bt.disabled = len(self.roll_select.values) == 0
        for opt in self.options:
            opt.default = opt.value in self.roll_select.values
        await interaction.response.edit_message(view=self)

    @property
    def confirmation(self):
        return self.confirmation_view.confirmation

    @property
    def selected_roll(self) -> RollData:
        return self.rolls[int(self.roll_select.values[0])]


class RollResultsView(CompositeNavigatorView):
    def __init__(
        self,
        bot: Bot,
        pages: Pages,
        cog: 'WaifuCollection',
        user: discord.User,
        waifus: list[WaifuSelectResult],
    ):
        pages.pages.insert(0, self._page_zero())
        pages.start_at = 0
        super().__init__(bot, pages=pages, hide_jumper=True)

        self.cog = cog
        self.user = user
        self.waifus = waifus

        self.lock_button = RefreshableButton(emoji='🔒', style=discord.ButtonStyle.green, row=0)
        self.lock_button.callback = self._lock_callback
        self.lock_button.refresh = self._lock_refresh

        self.trade_button = Button(emoji='🔀', style=discord.ButtonStyle.blurple, row=0)
        self.trade_button.callback = self._trade_callback

        self.remove_item(self.next_page_bt)
        self.add_item(self.lock_button)
        self.add_item(self.trade_button)
        self.add_item(self.next_page_bt)

    async def _page_zero(self):
        embed = Embed(
            title=f'{WC_EMOJI} Waifu Collection',
            description=f'Click {self.NEXT_EMOJI} to reveal',
            color=WC_COLOR,
        )
        embed.set_author(name=self.user, icon_url=self.user.display_avatar.url)
        return {'embed': embed}

    async def _lock_refresh(self, page: int):
        self.lock_button.disabled = page == 0

    async def _lock_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        waifu_id = self.waifus[self.displayed_page - 1].id
        resp = await get_nanapi().waicolle.waicolle_get_waifus(str(waifu_id))
        if not success(resp):
            raise RuntimeError(resp.result)
        waifu = resp.result[0]

        if any(
            [
                interaction.user.id != int(waifu.owner.user.discord_id),
                waifu.trade_locked,
                waifu.blooded,
            ]
        ):
            await interaction.followup.send(
                'Cannot lock this waifu (not yours, in trade, or blooded)',
                ephemeral=True,
            )
            return

        if self.cog.trade_lock[interaction.user.id].locked():
            await interaction.followup.send(
                f'**{interaction.user}** has a pending trade/reroll/lock/unlock/ascend.',
                ephemeral=True,
            )
            return

        async with self.cog.trade_lock[interaction.user.id]:
            body = BulkUpdateWaifusBody(
                ids=[str(self.waifus[self.displayed_page - 1].id)],
                locked=True,
            )
            resp = await get_nanapi().waicolle.waicolle_bulk_update_waifus(body)
            if not success(resp):
                raise RuntimeError(resp.result)

            await interaction.followup.send(
                f'Locked {self.bot.get_emoji_str("FubukiGO")}', ephemeral=True
            )

    async def _trade_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.cog.trade_lock_context(interaction.user, self.user):
                await interaction.followup.send(f'**{interaction.user}** wants to trade')

                resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
                    ','.join(str(w.id) for w in self.waifus)
                )
                if not success(resp1):
                    raise RuntimeError(resp1.result)
                available = [
                    w
                    for w in resp1.result
                    if all(
                        [
                            int(w.owner.user.discord_id) == self.user.id,
                            not w.locked,
                            not w.trade_locked,
                            not w.blooded,
                            not w.disabled,
                        ]
                    )
                ]

                resp2 = await get_nanapi().waicolle.waicolle_get_waifus(
                    discord_id=str(interaction.user.id), locked=0, trade_locked=0, blooded=0
                )
                if not success(resp2):
                    match resp2.code:
                        case 404:
                            raise commands.CommandError(
                                f'**{interaction.user}** is not a player '
                                f'{self.bot.get_emoji_str("saladedefruits")}'
                            )
                        case _:
                            raise RuntimeError(resp2.result)
                player_waifus = resp2.result

                chousen_player_coro = self._waifus_selector(
                    interaction, player_waifus, 'offer', interaction.user
                )
                chousen_other_coro = self._waifus_selector(
                    interaction, available, 'receive', self.user
                )
                chousen_player, chousen_other = await asyncio.gather(
                    chousen_player_coro, chousen_other_coro
                )
                if chousen_player is None or chousen_other is None:
                    return

                trade_waifus = OrderedDict(
                    [
                        (interaction.user.id, [w.id for w in chousen_player]),
                        (self.user.id, [w.id for w in chousen_other]),
                    ]
                )
                trade = await TradeHelper.create(self.cog, trade_waifus)
                try:
                    await trade.send(interaction.followup.send)
                except Exception:
                    await trade.release()
                    raise
        except commands.CommandError as e:
            await interaction.followup.send(str(e))

    async def _waifus_selector(
        self,
        interaction: discord.Interaction,
        waifus: list[WaifuSelectResult],
        action: str,
        owner: discord.User | discord.Member,
        skip_empty: bool = True,
    ) -> list[WaifuSelectResult] | None:
        if skip_empty and len(waifus) == 0:
            await interaction.followup.send('*Empty list, skipping selection*', ephemeral=True)
            return []

        pages = [
            self.cog._waifu_selector_page(owner, group, len(waifus))
            for group in batched(waifus, PER_PAGE_SELECTOR)
        ]

        content = f'{interaction.user.mention}\nSelect the characters you want to **{action}**.'

        _, view = await WaifuSelectorView.create(
            self.bot,
            partial(interaction.followup.send, ephemeral=True),
            pages=pages,
            waifus=waifus,
            lock=interaction.user,
            static_content=content,
        )

        if not await view.confirmation:
            raise commands.CommandError('Trade aborted')

        return view.selected


class TradeConfirmationView(BaseConfirmationView):
    def __init__(self, bot: Bot, trade: 'TradeHelper'):
        super().__init__(
            bot,
            accept_custom_id=f'waifu_trade_accept_{trade.id}',
            refuse_custom_id=f'waifu_trade_refuse_{trade.id}',
        )
        self.trade = trade

    async def accept(self, interaction: discord.Interaction):
        if (interaction.user.id == self.trade.offeree.id) or (
            self.trade.can_author_accept and (interaction.user.id == self.trade.author.id)
        ):
            await self.trade.complete(interaction)

    async def refuse(self, interaction: discord.Interaction):
        if interaction.user.id in (self.trade.author.id, self.trade.offeree.id):
            await self.trade.abort(interaction)


class TradeOfferView(CompositeAutoNavigatorView):
    def __init__(self, bot: Bot, pages, trade: 'TradeHelper'):
        confirmation_view = TradeConfirmationView(bot, trade)
        super().__init__(bot, confirmation_view, pages=pages)


@dataclass
class WaifuOwnershipTypes:
    context_char: str
    simple: int = 0
    ascended: int = 0
    double_ascended: int = 0

    @property
    def count(self):
        return self.simple + self.ascended + self.double_ascended

    def __bool__(self):
        return self.count > 0

    def __str__(self):
        out = f'{self.context_char}'
        if self.count == 1 and self.simple == 1:
            return out

        out += ' ('

        if self.double_ascended > 1:
            out += f'**{self.double_ascended}**'
        if self.double_ascended > 0:
            out += '🌟'

            if self.ascended or self.simple:
                out += '+'

        if self.ascended > 1:
            out += f'**{self.ascended}**'
        if self.ascended > 0:
            out += '⭐'

            if self.simple:
                out += '+'

        if self.simple and self.count > 1:
            out += f'**{self.simple}**'

        out += ')'
        return out


@dataclass
class WaifuOwnership:
    unlocked: WaifuOwnershipTypes = field(default_factory=partial(WaifuOwnershipTypes, '🔓'))
    locked: WaifuOwnershipTypes = field(default_factory=partial(WaifuOwnershipTypes, '🔒'))
    in_trade: WaifuOwnershipTypes = field(default_factory=partial(WaifuOwnershipTypes, '🔀'))


async def chara_embed(bot: Bot, chara: CharaSelectResult) -> Embed:
    title = STAFF_GARBAGE.sub(' ', chara.name_user_preferred)
    if chara.name_native is not None:
        title += f' ({chara.name_native})'

    rank = await RankHelper.get(chara.rank)
    embed = Embed(title=title, url=chara.site_url, color=rank.color)
    embed.set_author(
        name='AniList',
        url='https://anilist.co/',
        icon_url='https://anilist.co/img/icons/msapplication-icon-144x144.png',
    )
    embed.set_thumbnail(url=chara.image_large)

    embed.add_field(name='Favourites', value=f'{chara.favourites} [**{chara.rank.name}**]')

    birth = None
    if chara.date_of_birth_month is not None:
        birth = calendar.month_name[chara.date_of_birth_month]
        if chara.date_of_birth_day is not None:
            birth += f' {chara.date_of_birth_day}'
    if birth is not None:
        embed.add_field(name='Birthday', value=birth)

    if chara.age is not None:
        embed.add_field(name='Age', value=chara.age)

    if (gender := chara.fuzzy_gender) is not None:
        embed.add_field(name='Gender', value=gender, inline=False)

    resp1 = await get_nanapi().anilist.anilist_get_chara_chara_edges(chara.id_al)
    if not success(resp1):
        raise RuntimeError(resp1.result)
    edges = resp1.result
    edges.sort(key=lambda edge: edge.character_role == 'BACKGROUND')

    animes = []
    mangas = []
    seiyuu = None
    for edge in edges:
        if edge.media.type == MediaType.ANIME:
            animes.append(edge.media.title_user_preferred)
            if seiyuu is None and len(edge.voice_actors) > 0:
                seiyuu_obj = edge.voice_actors[0]
                seiyuu = seiyuu_obj.name_user_preferred
                if seiyuu_obj.name_native is not None:
                    seiyuu = f'{seiyuu} ({seiyuu_obj.name_native})'

                seiyuu = STAFF_GARBAGE.sub(' ', seiyuu)
        else:
            mangas.append(edge.media.title_user_preferred)

    if seiyuu is not None:
        embed.add_field(name='Character Voice', value=seiyuu, inline=False)

    if len(animes) > 0:
        embed.add_field(name='Animeography Top 5', value=' • '.join(animes[:5]), inline=False)
    if len(mangas) > 0:
        embed.add_field(name='Mangaography Top 5', value=' • '.join(mangas[:5]), inline=False)

    resp2 = await get_nanapi().waicolle.waicolle_get_waifus(chara_id_al=chara.id_al)
    if not success(resp2):
        raise RuntimeError(resp2.result)
    waifus = resp2.result

    players_waifus = filter(
        lambda w: (int(w.owner.user.discord_id) != bot.bot_id) and not w.frozen and not w.blooded,
        waifus,
    )

    owners = defaultdict[int, WaifuOwnership](WaifuOwnership)

    for waifu in players_waifus:
        owner = owners[int(waifu.owner.user.discord_id)]
        if waifu.trade_locked:
            ownership = owner.in_trade
        elif waifu.locked:
            ownership = owner.locked
        else:
            ownership = owner.unlocked

        if waifu.level == 0:
            ownership.simple += 1
        if waifu.level == 1:
            ownership.ascended += 1
        if waifu.level > 1:
            ownership.double_ascended += 1

    text = []
    for id, entry in owners.items():
        subtext = str(bot.get_user(id))
        if entry.locked:
            subtext += f' {entry.locked}'
        if entry.unlocked:
            subtext += f' {entry.unlocked}'
        if entry.in_trade:
            subtext += f' {entry.in_trade}'

        if subtext:
            text.append(subtext)

    frozen_waifus = filter(
        lambda w: w.frozen and not w.locked and not w.blooded,
        waifus,
    )

    frozen = WaifuOwnershipTypes('🧊')
    for frozen_waifu in frozen_waifus:
        if frozen_waifu.level == 0:
            frozen.simple += 1
        if frozen_waifu.level == 1:
            frozen.ascended += 1
        if frozen_waifu.level > 1:
            frozen.double_ascended += 1

    if frozen.count:
        text.append(str(frozen))

    nanaed_waifus = filter(
        lambda w: int(w.owner.user.discord_id) == bot.bot_id and not w.blooded,
        waifus,
    )

    nanaed = WaifuOwnershipTypes('🌈')
    for nanaed_waifu in nanaed_waifus:
        if nanaed_waifu.level == 0:
            nanaed.simple += 1
        if nanaed_waifu.level == 1:
            nanaed.ascended += 1
        if nanaed_waifu.level > 1:
            nanaed.double_ascended += 1

    if nanaed.count:
        text.append(str(nanaed))

    blooded_waifus = filter(
        lambda w: w.blooded and not w.frozen,
        waifus,
    )

    blooded = WaifuOwnershipTypes('🩸')
    for blooded_waifu in blooded_waifus:
        if blooded_waifu.level == 0:
            blooded.simple += 1
        if blooded_waifu.level == 1:
            blooded.ascended += 1
        if blooded_waifu.level > 1:
            blooded.double_ascended += 1

    if blooded.count:
        text.append(str(blooded))

    if text:
        embed.add_field(
            name='Owned by', value=' • '.join(sorted(text, key=str.casefold)), inline=False
        )

    resp3 = await get_nanapi().waicolle.waicolle_get_players(chara_id_al=chara.id_al)
    if not success(resp3):
        raise RuntimeError(resp3.result)
    trackers = resp3.result

    members = set(
        str(bot.get_user(int(tracker.user.discord_id)))
        for tracker in trackers
        if tracker.frozen_at is None
    )
    members = list(members)
    if members:
        embed.add_field(
            name='In tracking list of',
            value=' • '.join(sorted(members, key=str.casefold)),
            inline=False,
        )

    embed.set_footer(
        text=f'ID {chara.id_al} • Costs {rank.blood_price} • Worth {rank.blood_shards}'
    )

    return embed


async def chara_page(bot: Bot, chara: CharaSelectResult) -> dict[str, Embed]:
    embed = await chara_embed(bot, chara)
    return dict(embed=embed)


def chara_autocomplete(id_al_as_value: bool = False):
    async def autocomplete(interaction: discord.Interaction, current: str):
        resp = await get_nanapi().anilist.anilist_chara_name_autocomplete(current)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        choices: list[Choice[str]] = []
        for r in results:
            native = f' ({r.name_native})' if r.name_native else ''
            choice = Choice(
                name=autocomplete_truncate(f'{r.name_user_preferred}{native}'),
                value=(
                    str(r.id_al)
                    if id_al_as_value
                    else autocomplete_truncate(r.name_user_preferred)
                ),
            )
            choices.append(choice)

        return choices

    return autocomplete


def collection_autocomplete():
    async def autocomplete(interaction: discord.Interaction, current: str):
        bot = interaction.client
        resp = await get_nanapi().waicolle.waicolle_collection_name_autocomplete(current)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        return [
            Choice(
                name=autocomplete_truncate(f'{r.name} ({bot.get_user(int(r.author_discord_id))})'),
                value=str(r.id),
            )
            for r in results
        ]

    return autocomplete


@dataclass
class WaifuHelper:
    waifu: WaifuSelectResult
    chara: CharaSelectResult

    @property
    def id(self):
        return self.chara.id_al

    @property
    def name(self) -> str:
        if self.waifu.custom_name is not None:
            name = self.waifu.custom_name
        else:
            name = self.chara.name_user_preferred

        return STAFF_GARBAGE.sub(' ', name)

    async def get_rank(self):
        return await RankHelper.get(self.chara.rank)

    async def get_str(self, padding: int = 0) -> str:
        edges = await self.get_edges(self.chara.id_al)
        return await WaifuTextHelper(self.waifu, self.chara, edges).get_str(padding)

    async def get_select_option(self, nb: int, **kwargs) -> SelectOption:
        edges = await self.get_edges(self.chara.id_al)
        return await WaifuTextHelper(self.waifu, self.chara, edges).get_select_option(nb, **kwargs)

    @staticmethod
    async def get_edges(chara_id: int):
        resp = await get_nanapi().anilist.anilist_get_chara_chara_edges(chara_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        edges = resp.result
        edges.sort(key=lambda edge: edge.character_role == 'BACKGROUND')
        return edges


@dataclass
class WaifuTextHelper(WaifuHelper):
    edges: list[CEdgeSelectFilterCharaResult]

    @property
    def modifiers(self) -> str:
        mods = ''
        if self.waifu.trade_locked:
            mods += '🔀'
        if self.waifu.frozen:
            mods += '🧊'
        if self.waifu.locked:
            mods += '🔒'
        if self.waifu.level == 1:
            mods += '⭐'
        if self.waifu.level > 1:
            mods += '🌟'
        if self.waifu.nanaed:
            mods += '🌈'
        return mods

    async def get_str(self, padding: int = 0) -> str:
        title = self.edges[0].media.title_user_preferred.strip()

        seiyuu = self.main_seiyuu(self.edges)

        if padding:
            space = f'`{" " * (padding + 1)}` '
        else:
            space = ''

        modifiers = self.modifiers
        if modifiers:
            modifiers = ' ' + modifiers

        rank = self.chara.rank.name
        return (
            f'[**{rank}**]{modifiers} **[{self.name}]({self.chara.site_url})**{seiyuu}\n'
            f'{space}*{title}*'
        )

    async def get_select_option(self, nb: int, **kwargs) -> SelectOption:
        title = self.edges[0].media.title_user_preferred.strip()

        seiyuu = self.main_seiyuu(self.edges)

        modifiers = self.modifiers
        if modifiers:
            modifiers = ' ' + modifiers

        label = f'[{self.chara.rank.name}]{modifiers} {self.name}{seiyuu}'
        desc = f'#{nb} • {title}'

        rank = await self.get_rank()
        return SelectOption(emoji=rank.emoji, label=label[:100], description=desc[:100], **kwargs)

    @staticmethod
    def main_seiyuu(edges: list[CEdgeSelectFilterCharaResult]):
        seiyuu = ''
        for edge in edges:
            if len(edge.voice_actors) > 0:
                seiyuu_obj = edge.voice_actors[0]
                seiyuu = seiyuu_obj.name_user_preferred
                seiyuu = STAFF_GARBAGE.sub(' ', seiyuu)
                seiyuu = f' (CV: {seiyuu})'
                break
        return seiyuu


class RankHelper:
    ranks: dict[str, _Rank] | None = None

    @classmethod
    async def get(cls, wc_rank: WaicolleRank):
        if cls.ranks is None:
            resp = await get_nanapi().waicolle.waicolle_get_ranks()
            if not success(resp):
                raise RuntimeError(resp.result)
            cls.ranks = {r.wc_rank: r for r in resp.result}
        return cls.ranks[wc_rank]


class TradeHelper:
    def __init__(
        self,
        cog: 'WaifuCollection',
        trade_data: TradeSelectResult,
        can_author_accept: bool = False,
        author_silent: bool = False,
        offeree_silent: bool = False,
    ):
        self.cog = cog
        self.trade_data = trade_data
        self.can_author_accept = can_author_accept
        self.author_silent = author_silent
        self.offeree_silent = offeree_silent

    @property
    def id(self) -> UUID:
        return self.trade_data.id

    @property
    def bot(self) -> Bot:
        return self.cog.bot

    @property
    def author(self) -> discord.User:
        player = self.bot.get_user(int(self.trade_data.author.user.discord_id))
        if player is None:
            player = self.bot.get_user(self.bot.bot_id)
            assert player
        return player

    @property
    def offeree(self) -> discord.User:
        player = self.bot.get_user(int(self.trade_data.offeree.user.discord_id))
        if player is None:
            player = self.bot.get_user(self.bot.bot_id)
            assert player
        return player

    async def send(
        self,
        replyable: Callable[..., Coroutine[Any, Any, Any]],
    ):
        """
        Sends a trade message with the replyable function.
        """
        desc = ''
        tot_ids_al = []
        for user, (waifus, blood_shards) in zip(
            (self.author, self.offeree),
            (
                (self.trade_data.offered, self.trade_data.blood_shards),
                (self.trade_data.received, None),
            ),
        ):
            desc += f'**From {user}**\n'

            suppl = ''
            if blood_shards:
                suppl += f'{blood_shards} :drop_of_blood:'
            if len(waifus) > 0:
                ids_al = [w.character.id_al for w in waifus]
                tot_ids_al += ids_al

                ids_al_set = set(ids_al)
                ids_al_str = ','.join(str(i) for i in ids_al_set)

                async with asyncio.TaskGroup() as tg:
                    resp_task = tg.create_task(
                        get_nanapi().anilist.anilist_get_charas(ids_al=ids_al_str)
                    )
                    edge_tasks = [
                        (cid, tg.create_task(WaifuHelper.get_edges(cid))) for cid in ids_al
                    ]

                resp3 = await resp_task
                if not success(resp3):
                    raise RuntimeError(resp3.result)

                charas = {c.id_al: c for c in resp3.result}
                edges = {cid: await task for cid, task in edge_tasks}

                padding = int(math.log10(len(waifus)) + 1)

                text_tasks = []
                async with asyncio.TaskGroup() as tg:
                    for waifu_data in waifus:
                        waifu = WaifuTextHelper(
                            cast(WaifuSelectResult, waifu_data),
                            charas[waifu_data.character.id_al],
                            edges[waifu_data.character.id_al],
                        )
                        text_tasks.append(tg.create_task(waifu.get_str(padding=padding)))

                text = []
                for i, waifu_str in enumerate(text_tasks):
                    text.append(f'`{i + 1:{padding}}.` {await waifu_str}')

                suppl += '\n'.join(text)

            if suppl:
                desc += suppl
            else:
                desc += f'Nothing. {self.bot.get_emoji_str("saladedefruits")}'

            desc += '\n\n'

        content = (
            f'{self.offeree.mention}\n'
            f'**Trade offer from {self.author.mention}**\n'
            f'You can accept by reacting with '
            f'{self.bot.get_emoji_str(ConfirmationView.ACCEPT_EMOTE)}'
        )

        thumbnail_url = None
        if len(tot_ids_al) > 0:
            ids_al_str = ','.join(map(str, tot_ids_al))
            url = URL(f'{NANAPI_PUBLIC_URL}/anilist/charas/collages').with_query(ids_al=ids_al_str)
            if len(str(url)) <= 2048:
                thumbnail_url = str(url)

        offer, _ = await TradeOfferView.create(
            self.bot,
            replyable,
            static_content=content,
            title='Trade offer',
            description=desc,
            color=WC_COLOR,
            author_name=str(self.author),
            author_icon_url=self.author.display_avatar.url,
            thumbnail_url=thumbnail_url,
            footer_text=f'ID {self.id}',
            trade=self,
        )

    async def unregister(self, interaction: discord.Interaction):
        await interaction.response.defer()
        assert interaction.message is not None
        await interaction.message.edit(view=None)

    async def abort(self, interaction: discord.Interaction):
        try:
            content = f'{self.author.mention} {self.offeree.mention}\nTrade aborted'
            await self.unregister(interaction)
            await interaction.followup.send(content)
        finally:
            await self.release()

    async def complete(self, interaction: discord.Interaction):
        await self.unregister(interaction)
        resp = await get_nanapi().waicolle.waicolle_commit_trade(self.id)
        match resp:
            case Error(code=409):
                await self.release()
                await interaction.followup.send(
                    f'{self.author.mention} {self.offeree.mention}\n'
                    'Trade aborted: resources unavailable'
                )
                return
            case Error():
                raise RuntimeError(str(resp))
            case Success():
                result = resp.result

                await self.cog.drop_alert(
                    self.author,
                    result.received,
                    'Trade',
                    interaction.followup,
                    spoiler=False,
                    silent=self.author_silent,
                )
                await self.cog.drop_alert(
                    self.offeree,
                    result.offered,
                    'Trade',
                    interaction.followup,
                    spoiler=False,
                    silent=self.offeree_silent,
                )

    async def release(self):
        resp = await get_nanapi().waicolle.waicolle_cancel_trade(self.id)
        if not success(resp):
            raise RuntimeError(resp.result)

    @classmethod
    async def create(cls, cog: 'WaifuCollection', trade_waifus: OrderedDict[int, list[UUID]]):
        (author_id, author_waifus), (offeree_id, offeree_waifus) = trade_waifus.items()
        body = NewTradeBody(
            author_discord_id=str(author_id),
            received_ids=list(map(str, offeree_waifus)),
            offeree_discord_id=str(offeree_id),
            offered_ids=list(map(str, author_waifus)),
        )
        resp = await get_nanapi().waicolle.waicolle_new_trade(body)
        if not success(resp):
            raise RuntimeError(resp.result)
        trade_data = resp.result
        helper = cls(cog, trade_data)
        return helper
