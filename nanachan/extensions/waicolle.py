import asyncio
import base64
import bisect
import logging
import math
from collections import OrderedDict, defaultdict
from collections.abc import Coroutine, Iterable
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from enum import Enum
from functools import partial
from itertools import batched, zip_longest
from operator import getitem, itemgetter
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import UUID

import discord
from discord import AllowedMentions, Interaction, app_commands
from discord.app_commands.commands import Check
from discord.app_commands.tree import ALL_GUILDS
from discord.enums import ButtonStyle
from discord.ext import commands, tasks
from discord.ui import Button
from discord.utils import utcnow
from yarl import URL

from nanachan.discord.application_commands import (
    LegacyCommandContext,
    NanaGroup,
    handle_command_errors,
    legacy_command,
)
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import (
    Embed,
    EmbedField,
    Members,
    MultiplexingContext,
    UserType,
    get_option,
)
from nanachan.discord.views import AutoNavigatorView, LockedView, NavigatorView, StringSelectorView
from nanachan.nanapi.client import Error, Success, get_nanapi, success
from nanachan.nanapi.model import (
    AddPlayerCoinsBody,
    BulkUpdateWaifusBody,
    CustomizeWaifuBody,
    DonatePlayerCoinsBody,
    NewCollectionBody,
    NewCouponBody,
    NewLootBody,
    NewOfferingBody,
    PlayerCollectionStatsResult,
    PlayerMediaStatsResult,
    PlayerStaffStatsResult,
    ReorderWaifuBody,
    RerollBody,
    RollData,
    UpsertPlayerBody,
    WaifuSelectResult,
)
from nanachan.redis.waifu import next_drop, user_latest_message
from nanachan.settings import (
    BOT_ROOM_ID,
    BUREAU_ROLE_ID,
    DROP_RATE,
    GLOBAL_COIN_MULTIPLIER,
    NANAPI_PUBLIC_URL,
    TZ,
    WC_ROLE,
    WC_WEB,
    RequiresWaicolle,
    is_spam,
)
from nanachan.utils.anilist import (
    PER_PAGE,
    autocomplete_cast,
    media_autocomplete,
    staff_autocomplete,
)
from nanachan.utils.conditions import conditional_drop
from nanachan.utils.misc import print_exc, run_coro
from nanachan.utils.waicolle import (
    PER_PAGE_SELECTOR,
    RNG,
    WC_COLOR,
    WC_EMOJI,
    RankHelper,
    RollResultsView,
    RollSelectorView,
    TradeConfirmationView,
    TradeHelper,
    WaifuDropReactionListener,
    WaifuHelper,
    WaifuOwnership,
    WaifuSelectorView,
    WaifuTextHelper,
    chara_autocomplete,
    chara_page,
    collection_autocomplete,
)

if TYPE_CHECKING:
    from nanachan.extensions.profiles import Profiles

logger = logging.getLogger(__name__)


class Checks:
    __discord_app_commands_checks__: list[Check]

    def __init__(self):
        __discord_app_commands_checks__ = []  # noqa: F841


def is_admin_or_bureau(interaction: discord.Interaction):
    checks = Checks()
    app_commands.checks.has_permissions(administrator=True)(checks)
    app_commands.checks.has_role(BUREAU_ROLE_ID)(checks)
    return any(
        check_failure_suppress(check)(interaction)
        for check in checks.__discord_app_commands_checks__
    )


def check_failure_suppress(check: Check) -> Check:
    def wrapper(interaction):
        try:
            return check(interaction)
        except (commands.CheckFailure, app_commands.CheckFailure):
            return False

    return wrapper


class WaifuCollection(Cog, name='WaiColle ~Waifu Collection~', required_settings=RequiresWaicolle):
    """The best gacha game ever made"""

    emoji = WC_EMOJI

    slash_waifu = NanaGroup(
        name='waifu', guild_ids=[ALL_GUILDS], description='WaiColle guild commands'
    )

    slash_waifu_global = NanaGroup(name='waifu', description='WaiColle global commands')

    slash_waifu_utils = app_commands.Group(
        name='utils', parent=slash_waifu_global, description='WaiColle utils'
    )

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.alert_lock = asyncio.Lock()
        self.speed = 1
        self.next_drop: dict[int, int | float] = {}
        self.drp_lock: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.accounted_messages: dict[int, int] = defaultdict(int)
        self.ignored_messages: dict[int, int] = defaultdict(int)
        self.start_time: float = utcnow().timestamp()
        self.trade_lock: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.purge_task.start()

    async def cog_unload(self):
        self.purge_task.cancel()

    @Cog.listener()
    async def on_ready(self):
        assert self.bot.user is not None
        resp1 = await get_nanapi().waicolle.waicolle_upsert_player(
            self.bot.user.id,
            UpsertPlayerBody(discord_username=str(self.bot.user), game_mode='ALL'),
        )
        if not success(resp1):
            raise RuntimeError(resp1.result)

        profile_cog = cast('Profiles | None', self.bot.get_cog('Profiles'))
        assert profile_cog is not None
        profile_cog.registrars['Waifu Collection'] = self.register

        asyncio.create_task(conditional_drop.load_conditions(self))

        resp2 = await get_nanapi().waicolle.waicolle_trade_index()
        if not success(resp2):
            raise RuntimeError(resp2.result)
        trades = resp2.result
        for trade in trades:
            # TODO: should be a TradeOfferView
            self.bot.add_view(TradeConfirmationView(self.bot, TradeHelper(self, trade)))
        logger.info('trades ready')

    @tasks.loop(hours=24)
    async def purge_task(self):
        await self.bot.wait_until_ready()
        assert self.bot.user is not None
        await get_nanapi().waicolle.waicolle_blood_expired_waifus(self.bot.user.id)

    @commands.group()
    async def waifu(self, ctx: commands.Context):
        """WaiColle subcommands"""
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument(self.bot.get_emoji_str('pepeLoser'))

    ############
    # Register #
    ############

    PLAYER_MERGE_GAME_MODE = Literal['WAIFU', 'HUSBANDO', 'ALL']

    async def register(self, interaction: discord.Interaction):
        """Register as a new player or change game mode"""
        view = LockedView(self.bot, interaction.user)

        button = Button(emoji='👰‍♀️', label='Waifu (female, non-binary)', style=ButtonStyle.green)
        button.callback = partial(self._register_mode, 'WAIFU')
        view.add_item(button)

        button = Button(emoji='👰‍♂️', label='Husbando (male, non-binary)', style=ButtonStyle.red)
        button.callback = partial(self._register_mode, 'HUSBANDO')
        view.add_item(button)

        button = Button(emoji='👰', label='All (no filter)', style=ButtonStyle.blurple)
        button.callback = partial(self._register_mode, 'ALL')
        view.add_item(button)

        await interaction.response.edit_message(view=None)

        await interaction.followup.send(
            content=f'{interaction.user.mention}\nSelect your game mode', view=view
        )

    async def _register_mode(self, mode: PLAYER_MERGE_GAME_MODE, interaction: discord.Interaction):
        body = UpsertPlayerBody(discord_username=str(interaction.user), game_mode=mode)
        resp1 = await get_nanapi().waicolle.waicolle_upsert_player(interaction.user.id, body)
        if not success(resp1):
            raise RuntimeError(resp1.result)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        assert WC_ROLE is not None
        wc_role = interaction.guild.get_role(WC_ROLE)
        assert wc_role is not None
        await interaction.user.add_roles(wc_role)

        await interaction.response.edit_message(view=None)
        await interaction.followup.send(content=self.bot.get_emoji_str('FubukiGO'))

        resp2 = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=interaction.user.id, as_og=1
        )
        if not success(resp2):
            raise RuntimeError(resp2.result)
        waifus = resp2.result
        if len(waifus) == 0:
            assert isinstance(interaction.channel, discord.TextChannel)
            async with interaction.channel.typing():
                resp3 = await get_nanapi().waicolle.waicolle_player_roll(
                    interaction.user.id, nb=10, reason='register'
                )
                if not success(resp3):
                    raise RuntimeError(resp3.result)
                assert resp3.code == 201
                waifus = resp3.result
                await self.drop_alert(
                    interaction.user, waifus, 'Register', messageable=interaction.followup
                )

    @slash_waifu_utils.command()
    @app_commands.check(is_admin_or_bureau)
    @legacy_command()
    async def freeze(self, ctx: LegacyCommandContext, member: discord.User):
        """Freeze player"""
        resp = await get_nanapi().waicolle.waicolle_freeze_player(member.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp.result)
        await ctx.reply(
            f'Player {member.mention} frozen',
            allowed_mentions=discord.AllowedMentions(users=False),
        )

    ############
    # Moecoins #
    ############

    @slash_waifu_global.command()
    @legacy_command()
    async def coins(
        self, ctx: LegacyCommandContext, member: discord.User | discord.Member | None = None
    ):
        """wow how moe much cute so waifu"""
        if member is None:
            member = ctx.author

        resp = await get_nanapi().waicolle.waicolle_get_player(member.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp.result)
        player = resp.result

        moecoin = self.bot.get_emoji_str('moecoin')
        await ctx.reply(
            f'{member.mention} has **{player.moecoins}** {moecoin} '
            f'and **{player.blood_shards}** :drop_of_blood:! ' + self.bot.get_emoji_str('hype'),
            allowed_mentions=discord.AllowedMentions(users=False),
        )

    @slash_waifu.command()
    @legacy_command()
    async def donate(self, ctx: LegacyCommandContext, nb: int, other_member: discord.User):
        """Donate moecoins"""
        body = DonatePlayerCoinsBody(moecoins=nb)
        resp = await get_nanapi().waicolle.waicolle_donate_player_coins(
            ctx.author.id, other_member.id, body
        )
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('One of the players does not exist')
                case 409:
                    raise commands.CommandError('Not enough moecoins')
                case _:
                    raise RuntimeError(resp.result)

        await ctx.reply(
            f'{other_member.mention} '
            f'You received **{nb}** {self.bot.get_emoji_str("moecoin")} '
            f'from {ctx.author.mention}! '
            f'{self.bot.get_emoji_str("hype")}'
        )

    @slash_waifu_utils.command()
    @app_commands.check(is_admin_or_bureau)
    @legacy_command()
    async def reward(self, ctx: LegacyCommandContext, nb: int, member: discord.User):
        """Reward (or punish) any player wallet"""
        body = AddPlayerCoinsBody(moecoins=nb)
        resp = await get_nanapi().waicolle.waicolle_add_player_coins(member.id, body)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError('Player does not exist')
                case 409:
                    raise commands.CommandError('Not enough moecoins')
                case _:
                    raise RuntimeError(resp.result)

        if nb >= 0:
            await ctx.reply(
                f'{member.mention} '
                f'You received **{nb}** {self.bot.get_emoji_str("moecoin")}! '
                f'{self.bot.get_emoji_str("hype")}'
            )
        else:
            await ctx.reply(
                f'{member.mention} '
                f'You lost **{-nb}** {self.bot.get_emoji_str("moecoin")}... '
                f'{self.bot.get_emoji_str("amoesip")}'
            )

    ##########
    # Search #
    ##########

    @slash_waifu_global.command()
    @app_commands.autocomplete(search=chara_autocomplete())
    @legacy_command()
    async def search(self, ctx: LegacyCommandContext, search: str):
        """Search a character on AniList"""
        resp = await get_nanapi().anilist.anilist_chara_search(search)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result

        if len(results) == 0:
            raise commands.CommandError('No results found')

        pages = [chara_page(self.bot, chara) for chara in results]
        await NavigatorView.create(self.bot, ctx.reply, pages=pages)

    ########
    # Drop #
    ########
    @slash_waifu.command()
    @app_commands.check(is_admin_or_bureau)
    @legacy_command()
    async def drop(
        self,
        ctx: LegacyCommandContext,
        nb: app_commands.Range[int, 0, None],
        members: Members | None = None,
    ):
        """Drop characters to players attending an event"""
        async with ctx.typing():
            if members is None:
                assert isinstance(ctx.author, discord.Member)
                if ctx.author.voice is not None:
                    assert ctx.author.voice.channel is not None
                    members = ctx.author.voice.channel.members
                else:
                    raise commands.CommandError('You must be in a voice channel or list members')

            members = [m for m in set(members) if not m.bot]

            await ctx.reply(
                f'Event drop for **{"**, **".join(str(m) for m in members)}**! '
                f'{self.bot.get_emoji_str("hype")}'
            )

            for member in members:
                asyncio.create_task(
                    self._drop(member, 'Event drop', replyable=ctx, nb=nb, rollop_reason='event')
                )

    async def _drop(
        self,
        member: UserType,
        reason: str,
        replyable: (LegacyCommandContext | discord.TextChannel | None) = None,
        roll_id: str | None = None,
        coupon_code: str | None = None,
        nb: int | None = 1,
        pool_player: UserType | None = None,
        rollop_reason: str | None = None,
    ):
        if member.bot:
            return

        if pool_player is None:
            pool_player = member

        if replyable is None:
            replyable = self.bot.get_bot_room()

        assert replyable is not None

        async with replyable.typing():
            resp = await get_nanapi().waicolle.waicolle_player_roll(
                member.id,
                roll_id=roll_id,
                coupon_code=coupon_code,
                nb=nb,
                pool_discord_id=pool_player.id,
                reason=rollop_reason,
            )

            match resp:
                case Error(code=404 | 409):
                    await replyable.send(
                        f'{member} {resp.result.detail} {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case Error():
                    raise RuntimeError(resp.result)
                case Success(code=204):
                    await replyable.send(f'{member} is frozen 🧊')
                case Success():
                    if coupon_code:
                        await replyable.send(self.bot.get_emoji_str('FubukiGO'))

                    waifus = resp.result
                    await self.drop_alert(member, waifus, reason, messageable=replyable)

    async def drop_alert(
        self,
        user: UserType,
        waifus: list[WaifuSelectResult],
        reason: str,
        messageable: discord.abc.Messageable | discord.Webhook | None = None,
        spoiler: bool = True,
        silent: bool = False,
    ):
        pages = []
        nb = len(waifus)

        resp = await get_nanapi().anilist.anilist_get_charas(
            ids_al=','.join(str(w.character.id_al) for w in waifus)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        charas = {c.id_al: c for c in resp.result}

        for waifu in waifus:
            pages.append(chara_page(self.bot, charas[waifu.character.id_al]))

        content = (
            f'{user.mention}'
            f' [**{reason}**] You received **{nb}** '
            f'character{"s" if nb > 1 else ""}! '
            f'{self.bot.get_emoji_str("hype" if nb else "saladedefruits")}'
        )

        summary_pages = self.list_paginator(user, waifus, title='Summary', spoiler=spoiler)

        allowed_mentions = discord.AllowedMentions(users=not silent)

        async with self.alert_lock:
            if messageable is not None:
                resp, _ = await NavigatorView.create(
                    self.bot,
                    partial(messageable.send, allowed_mentions=allowed_mentions),
                    pages=summary_pages,
                    static_content=content,
                )
            else:
                bot_room = self.bot.get_bot_room()
                resp, _ = await NavigatorView.create(
                    self.bot,
                    partial(bot_room.send, allowed_mentions=allowed_mentions),
                    pages=summary_pages,
                    static_content=content,
                )
            if nb > 0:
                await RollResultsView.create(
                    self.bot,
                    partial(resp.reply, allowed_mentions=allowed_mentions),
                    cog=self,
                    user=user,
                    waifus=waifus,
                    pages=pages,
                    static_content=user.mention,
                    prefetch_min_batch_size=25,
                )

    ########
    # List #
    ########

    class ListChoice(Enum):
        full = 'full'
        locked = 'locked'
        unlocked = 'unlocked'
        ascended = 'ascended'
        edged = 'edged'

    @slash_waifu_global.command(name='list')
    @legacy_command()
    async def slash_list(
        self,
        ctx: LegacyCommandContext,
        filter: ListChoice,
        member: discord.User | discord.Member | None = None,
    ):
        """List a player owned characters"""
        if member is None:
            member = ctx.author

        kwargs = dict(blooded=0)
        if filter is self.ListChoice.full:
            pass
        elif filter is self.ListChoice.unlocked:
            kwargs['locked'] = 0
        elif filter is self.ListChoice.locked:
            kwargs['locked'] = 1
        elif filter is self.ListChoice.ascended:
            kwargs['ascended'] = 1
        elif filter is self.ListChoice.edged:
            kwargs['edged'] = 1
        else:
            raise RuntimeError('How did you get there?')

        resp = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=member.id, client_id=None, ids=None, **kwargs
        )
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp.result)
        waifus = resp.result

        if len(waifus) == 0:
            raise commands.CommandError(
                f'**{member}** has no **{filter.value}** character'
                f'{self.bot.get_emoji_str("saladedefruits")}'
            )

        title = f'{filter.name.capitalize()} character list'

        pages = self.list_paginator(member, waifus, title=title)
        await NavigatorView.create(self.bot, ctx.reply, pages=pages)

    def list_paginator(
        self,
        owner: UserType | discord.Guild,
        waifus: list[WaifuSelectResult],
        title: str = 'Character list',
        spoiler: bool = False,
        custom_lines: Iterable[str] | None = None,
    ) -> list[Coroutine]:
        total = len(waifus)
        if total == 0:
            return [self._list_page(0, [], owner, title, spoiler, 0)]

        if custom_lines is None:
            custom_lines = []

        pages = []
        partition = partial(batched, n=PER_PAGE)
        iterator = zip_longest(
            cast(Iterable[Iterable[WaifuSelectResult]], partition(waifus)),
            cast(Iterable[Iterable[str]], partition(custom_lines)),
        )
        for i, (sublist, sub_custom_lines) in enumerate(iterator):
            sub_custom_lines = [] if sub_custom_lines is None else sub_custom_lines
            pages.append(
                self._list_page(
                    i, list(sublist), owner, title, spoiler, total, list(sub_custom_lines)
                )
            )

        return pages

    async def _list_page(
        self,
        i: int,
        waifus: list[WaifuSelectResult],
        owner: UserType | discord.Guild,
        title: str,
        spoiler: bool,
        total: int,
        sub_custom_lines: list[str] | None = None,
    ) -> dict[str, Embed | Any]:
        if sub_custom_lines is None:
            sub_custom_lines = []

        text = []

        if len(waifus) > 0:
            edges = {}
            async with asyncio.TaskGroup() as tg:
                chara_ids = [w.character.id_al for w in waifus]
                resp_task = tg.create_task(
                    get_nanapi().anilist.anilist_get_charas(ids_al=','.join(map(str, chara_ids)))
                )

                edge_tasks = [
                    (cid, tg.create_task(WaifuHelper.get_edges(cid))) for cid in chara_ids
                ]

            resp = await resp_task
            if not success(resp):
                raise RuntimeError(resp.result)
            charas = {c.id_al: c for c in resp.result}
            edges = {cid: await task for cid, task in edge_tasks}

            padding = int(math.log10(i * PER_PAGE + len(waifus)) + 1)
            chara_str_tasks = []

            async with asyncio.TaskGroup() as tg:
                for waifu in waifus:
                    chara_str_tasks.append(
                        tg.create_task(
                            WaifuTextHelper(
                                waifu, charas[waifu.character.id_al], edges[waifu.character.id_al]
                            ).get_str(padding=padding)
                        )
                    )

            for j, (chara_str_task, custom_add) in enumerate(
                zip_longest(chara_str_tasks, sub_custom_lines)
            ):
                chara_str = await chara_str_task

                line = f'`{(i * PER_PAGE + j + 1):{padding}}.` {chara_str}'

                if custom_add is not None:
                    line += f'\n`{" " * (padding + 1)}` {custom_add}'

                text.append(line)

        desc = '\n'.join(text) if text else f'Nothing. {self.bot.get_emoji_str("saladedefruits")}'
        if spoiler and text:
            desc = '||' + desc + '||'

        embed = Embed(title=title, description=desc, color=WC_COLOR)

        if isinstance(owner, (discord.User, discord.Member, discord.ClientUser)):
            embed.set_author(name=owner, icon_url=owner.display_avatar.url)
        if isinstance(owner, discord.Guild) and owner.icon is not None:
            embed.set_author(name=owner, icon_url=owner.icon.url)

        embed.set_footer(text=f'{total} character{"s" if total > 1 else ""}')

        page: dict[str, Any] = dict(embed=embed)

        if not spoiler and len(waifus) > 0:
            page = await self._page_add_chara_collage(
                page, [w.character.id_al for w in waifus], as_thumbnail=True
            )

        return page

    async def waifus_selector(
        self,
        ctx: LegacyCommandContext,
        waifus: list[WaifuSelectResult],
        action: str,
        owner: discord.User | discord.Member,
        skip_empty: bool = True,
    ):
        if skip_empty and len(waifus) == 0:
            await ctx.send('*Empty list, skipping selection*', ephemeral=True)
            return []

        pages = [
            self._waifu_selector_page(owner, group, len(waifus))
            for group in batched(waifus, PER_PAGE_SELECTOR)
        ]

        content = f'{ctx.author.mention}\nSelect the characters you want to **{action}**.'

        _, view = await WaifuSelectorView.create(
            self.bot,
            partial(ctx.send, ephemeral=True),
            pages=pages,
            waifus=waifus,
            lock=ctx.author,
            static_content=content,
        )

        if not await view.confirmation:
            raise commands.CommandError('Aborting.')

        selected = view.selected
        return selected

    async def _waifu_selector_page(
        self, owner: discord.User | discord.Member, waifus: Iterable[WaifuSelectResult], total: int
    ):
        embed = Embed(title='Character list', color=WC_COLOR)
        embed.set_author(name=owner, icon_url=owner.display_avatar.url)
        embed.set_footer(text=f'{total} character{"s" if total > 1 else ""}')
        page = dict(embed=embed)
        page = await self._page_add_chara_collage(page, [w.character.id_al for w in waifus])
        return page

    @staticmethod
    async def _page_add_chara_collage(
        page: dict[str, Any], ids_al: list[int], as_thumbnail: bool = False
    ):
        ids_al_str = ','.join(map(str, ids_al))
        url = URL(f'{NANAPI_PUBLIC_URL}/anilist/charas/collages').with_query(ids_al=ids_al_str)
        if as_thumbnail:
            page['embed'].set_thumbnail(url=url)
        else:
            page['embed'].set_image(url=url)
        return page

    ########
    # Lock #
    ########

    @slash_waifu_global.command()
    @legacy_command()
    async def lock(self, ctx: LegacyCommandContext, prioritize_singles: bool = False):
        """Lock your characters to avoid accidentally killing them"""
        if self.trade_lock[ctx.author.id].locked():
            raise commands.CommandError(
                f'**{ctx.author}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        async with self.trade_lock[ctx.author.id]:
            owned_waifus_resp = await get_nanapi().waicolle.waicolle_get_waifus(
                discord_id=ctx.author.id, locked=0, trade_locked=0, blooded=0
            )
            if not success(owned_waifus_resp):
                match owned_waifus_resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(owned_waifus_resp.result)
            waifus = owned_waifus_resp.result

            tracked_waifus_resp = await get_nanapi().waicolle.waicolle_get_player_track_unlocked(
                discord_id=ctx.author.id,
                hide_singles=0 if prioritize_singles else 1,
            )
            if not success(tracked_waifus_resp):
                raise RuntimeError(tracked_waifus_resp.result)
            tracked_waifus_ids = [w.id for w in tracked_waifus_resp.result]

            waifus = sorted(
                waifus, key=lambda w: (w.id not in tracked_waifus_ids, -w.timestamp.timestamp())
            )

            notice = await ctx.reply('Locking characters...')

            selected = await self.waifus_selector(ctx, waifus, 'lock', ctx.author)

            nb = len(selected)
            if nb > 0:
                body = BulkUpdateWaifusBody(ids=[str(w.id) for w in selected], locked=True)
                update_resp = await get_nanapi().waicolle.waicolle_bulk_update_waifus(body)
                if not success(update_resp):
                    raise RuntimeError(update_resp.result)

            await notice.edit(content=f'**{nb}** character{"s" if nb > 1 else ""} locked.')

    @slash_waifu_global.command()
    @legacy_command()
    async def unlock(self, ctx: LegacyCommandContext, character_id: int | None = None):
        """Unlock your accidentally locked characters in order to kill them"""
        if self.trade_lock[ctx.author.id].locked():
            raise commands.CommandError(
                f'**{ctx.author}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        async with self.trade_lock[ctx.author.id]:
            resp = await get_nanapi().waicolle.waicolle_get_waifus(
                discord_id=ctx.author.id, locked=1, trade_locked=0, blooded=0
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp.result)
            waifus = resp.result
            if character_id is not None:
                waifus = [w for w in waifus if w.character.id_al == character_id]

            notice = await ctx.reply('Unlocking characters...')

            selected = await self.waifus_selector(ctx, waifus, 'unlock', ctx.author)

            nb = len(selected)
            if nb > 0:
                body = BulkUpdateWaifusBody(ids=[str(w.id) for w in selected], locked=False)
                resp = await get_nanapi().waicolle.waicolle_bulk_update_waifus(body)
                if not success(resp):
                    raise RuntimeError(resp.result)

            await notice.edit(content=f'**{nb}** character{"s" if nb > 1 else ""} unlocked.')

    ##########
    # Ascend #
    ##########

    @slash_waifu.command()
    @legacy_command()
    async def ascend(self, ctx: LegacyCommandContext):
        """Ascend your characters to a higher level"""
        if self.trade_lock[ctx.author.id].locked():
            raise commands.CommandError(
                f'**{ctx.author}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        async with self.trade_lock[ctx.author.id]:
            notice = await ctx.reply('Ascending characters...')

            resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
                discord_id=ctx.author.id, ascendable=1
            )
            if not success(resp1):
                match resp1.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp1.result)
            waifus = resp1.result

            selected = await self.waifus_selector(ctx, waifus, 'ascend', ctx.author)

            await notice.edit(
                content=f'**{len(selected)}** character{"s" if len(selected) > 1 else ""} '
                f'ascended.'
            )

            for waifu in selected:
                resp2 = await get_nanapi().waicolle.waicolle_ascend_waifu(waifu.id)
                if not success(resp2):
                    raise RuntimeError(resp2.result)
                ascended = resp2.result

                await self._ascend_alert(ctx, ascended)

    async def _ascend_alert(
        self, ctx: LegacyCommandContext, ascended: WaifuSelectResult, user: UserType | None = None
    ):
        if user is None:
            user = ctx.author

        resp3 = await get_nanapi().anilist.anilist_get_charas(str(ascended.character.id_al))
        if not success(resp3):
            raise RuntimeError(resp3.result)
        chara = resp3.result[0]

        embed = Embed(title=f'{chara.name_user_preferred} ascended!', color=WC_COLOR)
        embed.set_image(url=chara.image_large)
        embed.set_author(name=user, icon_url=user.display_avatar.url)
        embed.set_footer(text=f'ID {chara.id_al}')

        await ctx.reply(embed=embed)

    #########
    # Blood #
    #########

    @slash_waifu.command()
    @legacy_command()
    async def blood(self, ctx: LegacyCommandContext):
        """Extract blood from your characters"""
        if self.trade_lock[ctx.author.id].locked():
            raise commands.CommandError(
                f'**{ctx.author}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        async with self.trade_lock[ctx.author.id]:
            notice = await ctx.reply('Blooding characters...')

            resp = await get_nanapi().waicolle.waicolle_get_waifus(
                discord_id=ctx.author.id, locked=0, trade_locked=0, blooded=0
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp.result)
            waifus = resp.result

            selected = await self.waifus_selector(ctx, waifus, 'blood', ctx.author)

            await notice.edit(
                content=f'**{len(selected)}** character{"s" if len(selected) > 1 else ""} blooded.'
            )

            for waifu in selected:
                wid = waifu.id
                resp = await get_nanapi().waicolle.waicolle_blood_waifu(wid)
                if not success(resp):
                    raise RuntimeError(resp.result)
                chara = resp.result

                rank = await RankHelper.get(chara.rank)

                embed = Embed(
                    title=f'{chara.name_user_preferred} died horribly...',
                    description=f'**{rank.blood_shards}** :drop_of_blood: recovered',
                    color=WC_COLOR,
                )
                embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
                embed.set_footer(
                    text=f'ID {chara.id_al} • Costs {rank.blood_price} • Worth {rank.blood_shards}'
                )

                url = URL(f'{NANAPI_PUBLIC_URL}/anilist/charas/collages').with_query(
                    ids_al=str(chara.id_al), blooded=1
                )
                embed.set_image(url=url)
                await ctx.reply(embed=embed)

    @slash_waifu.command()
    @legacy_command()
    async def offering(self, ctx: LegacyCommandContext, character_id: int):
        """Offer blood in exchange for characters"""
        assert self.bot.user is not None
        if self.trade_lock[self.bot.user.id].locked():
            raise commands.CommandError(
                f'**{self.bot.user}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        await self.trade_lock[self.bot.user.id].acquire()

        try:
            body = NewOfferingBody(
                player_discord_id=ctx.author.id,
                chara_id_al=character_id,
                bot_discord_id=self.bot.user.id,
            )
            resp = await get_nanapi().waicolle.waicolle_new_offering(body)
            match resp:
                case Error(code=404):
                    raise commands.CommandError('This character is not available for offering.')
                case Error():
                    raise RuntimeError(resp.result)

            data = resp.result
            trade = TradeHelper(self, data, can_author_accept=True)
            try:
                await trade.send(ctx.reply)
            except Exception:
                await trade.release()
                raise
        finally:
            if self.trade_lock[self.bot.user.id].locked():
                self.trade_lock[self.bot.user.id].release()

    @slash_waifu.command()
    @legacy_command()
    async def loot(self, ctx: LegacyCommandContext, character_id: int):
        """Loot unlocked frozen waifu"""
        body = NewLootBody(player_discord_id=ctx.author.id, chara_id_al=character_id)
        resp = await get_nanapi().waicolle.waicolle_new_loot(body)
        match resp:
            case Error(code=404):
                raise commands.CommandError('No frozen waifu found.')
            case Error():
                raise RuntimeError(resp.result)

        data = resp.result
        trade = TradeHelper(self, data, can_author_accept=True, offeree_silent=True)
        try:
            await trade.send(
                partial(ctx.reply, allowed_mentions=AllowedMentions(users=[ctx.author]))
            )
        except Exception:
            await trade.release()
            raise

    ##########
    # Reroll #
    ##########

    @slash_waifu.command()
    @legacy_command()
    async def reroll(self, ctx: LegacyCommandContext):
        """Reroll characters (3 -> 1)"""
        if self.trade_lock[ctx.author.id].locked():
            raise commands.CommandError('You have a pending trade/reroll/lock/unlock/ascend.')

        async with self.trade_lock[ctx.author.id]:
            notice = await ctx.reply('Rerolling characters...')

            resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
                discord_id=ctx.author.id, locked=0, trade_locked=0, blooded=0
            )
            if not success(resp1):
                match resp1.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp1.result)
            waifus = resp1.result

            rerolled = await self.waifus_selector(ctx, waifus, 'reroll', ctx.author)

            if len(rerolled) < 1:
                raise commands.CommandError(
                    f'You must make at least 1 offer... {self.bot.get_emoji_str("coram")}'
                )

            async with ctx.typing():
                if (nb := len(rerolled)) > 1:
                    content = f'In exchange for these **{nb}** characters...'
                else:
                    content = 'In exchange for this **1** character...'

                pages = self.list_paginator(ctx.author, rerolled, title='Rerolled characters')

                await NavigatorView.create(
                    self.bot, notice.edit, pages=pages, static_content=content
                )

                body = RerollBody(
                    player_discord_id=ctx.author.id,
                    waifus_ids=[str(r.id) for r in rerolled],
                    bot_discord_id=self.bot.bot_id,
                )
                resp2 = await get_nanapi().waicolle.waicolle_reroll(body)
                if not success(resp2):
                    raise RuntimeError(resp2.result)
                result = resp2.result

                await self.drop_alert(ctx.author, result.obtained, 'Reroll', messageable=ctx)

        for ascended in result.nanascends:
            nana = cast(discord.User, self.bot.user)
            asyncio.create_task(self._ascend_alert(ctx, ascended, user=nana))

    #########
    # Trade #
    #########

    @slash_waifu.command()
    @legacy_command()
    async def trade(
        self,
        ctx: LegacyCommandContext,
        other_member: discord.User,
        prioritize_singles: bool = False,
    ):
        """Trade your characters with other players"""
        return await self._trade(ctx, other_member, prioritize_singles)

    async def _trade(
        self,
        ctx: LegacyCommandContext,
        other_member: discord.User | discord.Member,
        prioritize_singles: bool = False,
    ):
        async with self.trade_lock_context(ctx.author, other_member):
            await ctx.reply(f'Trading with **{other_member}**...')

            async with asyncio.TaskGroup() as tg:
                other_track_unlocked_task = tg.create_task(
                    get_nanapi().waicolle.waicolle_get_player_track_unlocked(
                        discord_id=other_member.id, hide_singles=0 if prioritize_singles else 1
                    )
                )
                player_track_unlocked_task = tg.create_task(
                    get_nanapi().waicolle.waicolle_get_player_track_unlocked(
                        discord_id=ctx.author.id, hide_singles=0 if prioritize_singles else 1
                    )
                )
                player_waifus_task = tg.create_task(
                    get_nanapi().waicolle.waicolle_get_waifus(
                        discord_id=ctx.author.id, locked=0, trade_locked=0, blooded=0
                    )
                )
                other_waifus_task = tg.create_task(
                    get_nanapi().waicolle.waicolle_get_waifus(
                        discord_id=other_member.id, locked=0, trade_locked=0, blooded=0
                    )
                )

            player_waifus_resp = await player_waifus_task
            if not success(player_waifus_resp):
                match player_waifus_resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{ctx.author}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(player_waifus_resp.result)
            player_waifus = player_waifus_resp.result

            other_waifus_resp = await other_waifus_task
            if not success(other_waifus_resp):
                match other_waifus_resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{other_member}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(other_waifus_resp.result)
            other_waifus = other_waifus_resp.result

            player_track_unlocked_resp = await player_track_unlocked_task
            if not success(player_track_unlocked_resp):
                raise RuntimeError(player_track_unlocked_resp.result)
            tracked_waifus = player_track_unlocked_resp.result

            tracked_waifus_ids = [w.id for w in tracked_waifus]
            other_waifus = sorted(
                other_waifus,
                key=lambda w: (w.id not in tracked_waifus_ids, -w.timestamp.timestamp()),
            )

            other_track_unlocked_resp = await other_track_unlocked_task
            if not success(other_track_unlocked_resp):
                raise RuntimeError(other_track_unlocked_resp.result)
            other_track_unlocked_waifus = other_track_unlocked_resp.result

            other_track_unlocked_waifus_ids = [w.id for w in other_track_unlocked_waifus]
            player_waifus = sorted(
                player_waifus,
                key=lambda w: (
                    w.id not in other_track_unlocked_waifus_ids,
                    -w.timestamp.timestamp(),
                ),
            )

            chousen_player_coro = self.waifus_selector(ctx, player_waifus, 'give', ctx.author)

            chousen_other_coro = self.waifus_selector(ctx, other_waifus, 'receive', other_member)

            chousen_player, chousen_other = await asyncio.gather(
                chousen_player_coro, chousen_other_coro
            )

            trade_waifus = OrderedDict(
                [
                    (ctx.author.id, [w.id for w in chousen_player]),
                    (other_member.id, [w.id for w in chousen_other]),
                ]
            )

            trade = await TradeHelper.create(self, trade_waifus)
            try:
                await trade.send(ctx.reply)
            except Exception:
                await trade.release()
                raise

    @slash_waifu.command()
    async def inbox(
        self, interaction: Interaction[Bot], member: discord.User | discord.Member | None = None
    ):
        """Find out if you have trades from last year"""
        await interaction.response.defer()
        trades_resp = await get_nanapi().waicolle.waicolle_trade_index()
        match trades_resp:
            case Error():
                raise RuntimeError(trades_resp.result)
            case Success():
                trades = trades_resp.result

        if member is None:
            member = interaction.user

        user_trades = [
            TradeHelper(self, t) for t in trades if t.offeree.user.discord_id == member.id
        ]

        for trade in user_trades:
            send = partial(
                interaction.followup.send,
                allowed_mentions=AllowedMentions(users=[interaction.user]),
            )
            await trade.send(send)
        if len(user_trades) == 0:
            await interaction.followup.send(f'No trades for {member}')

    @asynccontextmanager
    async def trade_lock_context(
        self,
        self_member: discord.User | discord.Member,
        other_member: discord.User | discord.Member,
    ):
        if self.trade_lock[self_member.id].locked():
            raise commands.CommandError(
                f'**{self_member}** has a pending trade/reroll/lock/unlock/ascend.'
            )
        if self.trade_lock[other_member.id].locked():
            raise commands.CommandError(
                f'**{other_member}** has a pending trade/reroll/lock/unlock/ascend.'
            )

        if other_member == self_member:
            raise commands.CommandError("You can't trade by yourself.")

        await self.trade_lock[self_member.id].acquire()
        await self.trade_lock[other_member.id].acquire()

        try:
            yield
        finally:
            if self.trade_lock[self_member.id].locked():
                self.trade_lock[self_member.id].release()
            if self.trade_lock[other_member.id].locked():
                self.trade_lock[other_member.id].release()

    ########
    # Roll #
    ########

    @slash_waifu.command()
    @legacy_command()
    async def roll(self, ctx: LegacyCommandContext):
        """such moecoins, very waifus"""
        resp1 = await get_nanapi().waicolle.waicolle_get_player(ctx.author.id)
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{ctx.author}** is not a player '
                        f'{self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        player = resp1.result

        notice = await ctx.reply('Rolling characters...')
        moecoin = self.bot.get_emoji_str('moecoin')
        hype = self.bot.get_emoji_str('hype')

        embed = Embed(
            title='WaiColle rolls',
            description=f'You have **{player.moecoins}** {moecoin}! {hype}',
            color=WC_COLOR,
        )

        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

        resp2 = await get_nanapi().waicolle.waicolle_get_rolls(ctx.author.id)
        if not success(resp2):
            raise RuntimeError(resp2.result)
        rolls = resp2.result

        view = RollSelectorView(self.bot, ctx.author, rolls, timeout=300)
        await ctx.reply(embed=embed, view=view, ephemeral=True)

        if not await view.confirmation:
            await ctx.reply('Roll aborted')
            return

        await self._roll(ctx, ctx.author, view.selected_roll, notice)

    async def _roll(self, ctx, user: UserType, roll_data: RollData, notice: discord.Message):
        await notice.edit(
            content=f'Rolling **{roll_data.name}** for **{roll_data.price}** '
            f'{self.bot.get_emoji_str("moecoin")}.'
        )
        await self._drop(user, f'Roll: {roll_data.name}', replyable=ctx, roll_id=roll_data.id)

    @slash_waifu_global.command()
    @legacy_command()
    async def daily(self, ctx: LegacyCommandContext):
        """Daily tag informations"""
        resp1 = await get_nanapi().waicolle.waicolle_get_rolls(ctx.author.id)
        if not success(resp1):
            raise RuntimeError(resp1.result)
        rolls = {roll.id: roll for roll in resp1.result}
        daily = rolls['daily']

        resp2 = await get_nanapi().client.client_whoami()
        if not success(resp2):
            raise RuntimeError(resp2.result)
        client = resp2.result

        await ctx.reply(
            f'[{datetime.now(TZ):%Y-%m-%d}] **Daily Roll**\n'
            f'```\n'
            f'{daily.name}\n'
            f'```'
            f'{WC_WEB}/{client.id}/daily'
        )

    #############
    # Customize #
    #############

    @slash_waifu.command()
    @legacy_command()
    async def customize(self, ctx: LegacyCommandContext):
        """Customize your ascended characters"""
        resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=ctx.author.id, ascended=1, blooded=0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{ctx.author}** is not a player '
                        f'{self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        waifus = resp1.result

        notice = await ctx.reply('Customizing characters...')

        selected = await self.waifus_selector(ctx, waifus, 'customize', ctx.author)

        ids_al = ','.join([str(w.character.id_al) for w in selected])
        resp2 = await get_nanapi().anilist.anilist_get_charas(ids_al)
        if not success(resp2):
            raise RuntimeError(resp2.result)
        charas_map = {c.id_al: c for c in resp2.result}

        for waifu in selected:
            helper = WaifuHelper(waifu, charas_map[waifu.character.id_al])
            old_name = helper.name
            await ctx.reply(
                f"Please send a PNG file for {old_name}, 'None' to reset, "
                f'or any other message to skip',
                ephemeral=True,
            )

            def check(message):
                return all(
                    [
                        message.command is None,
                        message.author == ctx.author,
                        message.channel == ctx.channel,
                    ]
                )

            resp = await MultiplexingContext.set_will_delete(check=check)
            resp = resp.message

            custom_image = None
            if resp.content == 'None':
                custom_image = ''
            elif len(resp.attachments) > 0:
                attachment = resp.attachments[0]
                if attachment.content_type == 'image/png':
                    custom_image = base64.b64encode(await attachment.read()).decode()
                else:
                    await resp.reply('Not a valid PNG file!')

            await resp.delete()

            await ctx.reply('Select the new name for this character', ephemeral=True)

            names = [helper.chara.name_user_preferred]
            if helper.chara.name_alternative is not None:
                for alt in helper.chara.name_alternative:
                    if alt and alt not in names:
                        names.append(alt)
            if helper.chara.name_alternative_spoiler is not None:
                for alt in helper.chara.name_alternative_spoiler:
                    if alt and alt not in names:
                        names.append(alt)

            _, name_selector = await StringSelectorView.create(
                ctx.bot,
                partial(ctx.send, ephemeral=True),
                strings=names,
                kind='name',
                owner=ctx.author,
            )

            if not await name_selector.confirmation:
                raise commands.CommandError('Aborting.')

            custom_name: str | None = None
            if len(name_selector.selected) > 0:
                selected_name = name_selector.selected[0]
                if selected_name != helper.chara.name_user_preferred:
                    custom_name = selected_name
                else:
                    custom_name = ''

            body = CustomizeWaifuBody(custom_image=custom_image, custom_name=custom_name)
            resp3 = await get_nanapi().waicolle.waicolle_customize_waifu(waifu.id, body)
            if not success(resp3):
                raise RuntimeError(resp3.result)

        s = 's' if len(selected) > 1 else ''
        await notice.edit(content=f'**{len(selected)}** character{s} customized.')

    ###########
    # Reorder #
    ###########

    @slash_waifu_global.command()
    @legacy_command()
    async def reorder(self, ctx: LegacyCommandContext):
        """Change the order of your ascended characters on collages"""
        notice = await ctx.reply('Reordering characters...')

        resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=ctx.author.id, ascended=1, blooded=0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{ctx.author}** is not a player '
                        f'{self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        waifus = resp1.result

        selected = await self.waifus_selector(ctx, waifus, 'reorder', ctx.author)

        ids_al = ','.join([str(w.character.id_al) for w in selected])
        resp2 = await get_nanapi().anilist.anilist_get_charas(ids_al)
        if not success(resp2):
            raise RuntimeError(resp2.result)
        charas_map = {c.id_al: c for c in resp2.result}

        COLLAGE_POSITIONS: dict[str, Literal['DEFAULT', 'LEFT_OF', 'RIGHT_OF']] = {
            'Default': 'DEFAULT',
            'Left of': 'LEFT_OF',
            'Right of': 'RIGHT_OF',
        }

        for waifu in selected:
            helper = WaifuHelper(waifu, charas_map[waifu.character.id_al])
            waifu_name = helper.name

            _, position_selector = await StringSelectorView.create(
                ctx.bot,
                partial(ctx.send, ephemeral=True),
                strings=list(COLLAGE_POSITIONS.keys()),
                kind=f"{waifu_name}'s position",
                owner=ctx.author,
                capitalize=False,
            )

            if not await position_selector.confirmation:
                raise commands.CommandError('Aborting.')

            if len(position_selector.selected) > 0:
                selected_position = COLLAGE_POSITIONS[position_selector.selected[0]]
                if selected_position != 'DEFAULT':
                    relatives = [w for w in waifus if w.id != waifu.id]
                    selected2 = await self.waifus_selector(
                        ctx,
                        relatives,
                        f'place {waifu_name} {position_selector.selected[0].lower()}',
                        ctx.author,
                        skip_empty=False,
                    )

                    if len(selected2) == 0:
                        raise commands.CommandError('You have to select another waifu.')

                    waifu_relative = selected2[0]
                else:
                    waifu_relative = None

                body = ReorderWaifuBody(
                    custom_position=selected_position,
                    other_waifu_id=waifu_relative.id if waifu_relative else None,
                )
                resp3 = await get_nanapi().waicolle.waicolle_reorder_waifu(waifu.id, body)
                if not success(resp3):
                    raise RuntimeError(resp3.result)

        s = 's' if len(selected) > 1 else ''
        await notice.edit(content=f'**{len(selected)}** character{s} reordered.')

    ###########
    # Collage #
    ###########
    class CollageChoice(Enum):
        full = 'full'
        locked = 'locked'
        unlocked = 'unlocked'
        ascended = 'ascended'
        edged = 'edged'
        custom = 'custom'

    @slash_waifu_global.command(name='collage')
    @legacy_command()
    async def slash_collage(
        self, ctx: LegacyCommandContext, filter: CollageChoice, member: UserType | None = None
    ):
        """Collage - Sangatsu no Phantasia"""
        if member is None:
            member = ctx.author

        filter_formatted = cast(
            Literal['FULL', 'LOCKED', 'UNLOCKED', 'ASCENDED', 'EDGED', 'CUSTOM'],
            filter.value.upper(),
        )

        resp = await get_nanapi().waicolle.waicolle_get_player_collage(member.id, filter_formatted)
        match resp:
            case Error(404):
                raise commands.CommandError(
                    f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                )
            case Error():
                raise RuntimeError(resp.result)
            case Success():
                collage = resp.result

        if collage.url is None:
            raise commands.CommandError(
                f'**{member}** has no character {self.bot.get_emoji_str("saladedefruits")}'
            )

        embed = Embed(title=f'{filter.value.capitalize()} collage', color=WC_COLOR)
        embed.set_image(url=collage.url)
        embed.set_author(name=member, icon_url=member.display_avatar.url)
        embed.set_footer(text=f'{collage.total} characters')

        await ctx.reply(embed=embed)

    ##################
    # Custom collage #
    ##################

    slash_collage_custom = app_commands.Group(
        name='collage-custom', parent=slash_waifu_global, description='Edit your custom collage'
    )

    @slash_collage_custom.command(name='add')
    @legacy_command()
    async def collage_custom_add(self, ctx: LegacyCommandContext):
        """Add characters to your custom collage"""
        notice = await ctx.reply('Selecting characters...')

        resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=ctx.author.id, custom_collage=0, blooded=0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{ctx.author}** is not a player '
                        f'{self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        waifus = resp1.result

        selected = await self.waifus_selector(ctx, waifus, 'display in custom collage', ctx.author)

        if selected:
            body = BulkUpdateWaifusBody(ids=[str(w.id) for w in selected], custom_collage=True)
            resp2 = await get_nanapi().waicolle.waicolle_bulk_update_waifus(body)
            if not success(resp2):
                raise RuntimeError(resp2.result)

        await notice.edit(
            content=f'**{len(selected)}** character{"s" if len(selected) > 1 else ""} '
            f'added to custom collage.'
        )

    @slash_collage_custom.command(name='remove')
    @legacy_command()
    async def collage_custom_remove(self, ctx: LegacyCommandContext):
        """Remove characters from your custom collage"""
        notice = await ctx.reply('Selecting characters...')

        resp1 = await get_nanapi().waicolle.waicolle_get_waifus(
            discord_id=ctx.author.id, custom_collage=1, blooded=0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{ctx.author}** is not a player '
                        f'{self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        waifus = resp1.result

        selected = await self.waifus_selector(ctx, waifus, 'hide in custom collage', ctx.author)

        if selected:
            body = BulkUpdateWaifusBody(ids=[str(w.id) for w in selected], custom_collage=False)
            resp2 = await get_nanapi().waicolle.waicolle_bulk_update_waifus(body)
            if not success(resp2):
                raise RuntimeError(resp2.result)

        await notice.edit(
            content=f'**{len(selected)}** character{"s" if len(selected) > 1 else ""} '
            f'removes from custom collage.'
        )

    #########
    # Album #
    #########

    class TrackChoice(Enum):
        media = 'media'
        staff = 'staff'
        collection = 'collection'

    async def track_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        track_type = get_option(
            interaction, 'track_type', cast_func=partial(getitem, self.TrackChoice)
        )
        if track_type is self.TrackChoice.media:
            fn = media_autocomplete(id_al_as_value=True)
        elif track_type is self.TrackChoice.staff:
            fn = staff_autocomplete(id_al_as_value=True)
        elif track_type is self.TrackChoice.collection:
            fn = collection_autocomplete()
        else:
            return []
        return await fn(interaction, current)

    @slash_waifu_global.command(name='album')
    @app_commands.autocomplete(item=track_autocomplete)
    @legacy_command()
    async def slash_album(
        self,
        ctx: LegacyCommandContext,
        track_type: TrackChoice,
        item: str,
        member: UserType | None = None,
        owned_only: bool = False,
    ):
        """Panini but with waifus"""
        if member is None:
            member = ctx.author

        assert ctx.interaction is not None

        if track_type is self.TrackChoice.media:
            media_id = await autocomplete_cast(ctx.interaction, self.track_autocomplete, int, item)

            resp = await get_nanapi().waicolle.waicolle_get_player_media_album(
                member.id, media_id, owned_only=1 if owned_only else 0
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{member}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp.result)
            collage = resp.result

            collage_type = collage.media.type
            media_str = f'[{collage.media.title_user_preferred}]({collage.media.site_url})'
            collage_desc = f'**{media_str}**'
            collage_id = collage.media.id_al

        elif track_type is self.TrackChoice.staff:
            staff_id = await autocomplete_cast(ctx.interaction, self.track_autocomplete, int, item)
            resp = await get_nanapi().waicolle.waicolle_get_player_staff_album(
                member.id, staff_id, owned_only=1 if owned_only else 0
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{member}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp.result)
            collage = resp.result

            collage_type = 'Staff'
            native = f' ({collage.staff.name_native})' if collage.staff.name_native else ''
            staff_str = f'[{collage.staff.name_user_preferred}{native}]({collage.staff.site_url})'
            collage_desc = f'**{staff_str}**'
            collage_id = collage.staff.id_al

        elif track_type is self.TrackChoice.collection:
            collec_id = await autocomplete_cast(
                ctx.interaction, self.track_autocomplete, UUID, item
            )
            resp = await get_nanapi().waicolle.waicolle_get_player_collection_album(
                member.id, collec_id, owned_only=1 if owned_only else 0
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        raise commands.CommandError(
                            f'**{member}** is not a player '
                            f'{self.bot.get_emoji_str("saladedefruits")}'
                        )
                    case _:
                        raise RuntimeError(resp.result)
            collage = resp.result

            medias_ids_str = ','.join(map(str, collage.collection.medias_ids_al))
            resp2 = await get_nanapi().anilist.anilist_get_medias(medias_ids_str)
            if not success(resp2):
                raise RuntimeError(resp2.result)
            media_map = {m.id_al: m for m in resp2.result}

            media_str = []
            for m_id in collage.collection.medias_ids_al:
                _media = media_map[m_id]
                media_str.append(
                    f'`[{_media.type[0]}-{_media.id_al}]` '
                    f'[{_media.title_user_preferred}]({_media.site_url})'
                )

            staff_ids_str = ','.join(map(str, collage.collection.staffs_ids_al))
            resp3 = await get_nanapi().anilist.anilist_get_staffs(staff_ids_str)
            if not success(resp3):
                raise RuntimeError(resp3.result)
            staff_map = {m.id_al: m for m in resp3.result}

            staff_str = []
            for m_id in collage.collection.staffs_ids_al:
                _staff = staff_map[m_id]
                name_native = f' ({_staff.name_native})' if _staff.name_native else ''
                staff_str.append(
                    f'`[S-{_staff.id_al}]` '
                    f'[{_staff.name_user_preferred}{name_native}]({_staff.site_url})'
                )

            collage_type = 'Collection'
            collage_desc = (
                f'**{collage.collection.name}** '
                f'({self.bot.get_user(collage.collection.author.user.discord_id)})\n'
                + ' • '.join(media_str + staff_str)
            )
            collage_id = None

        else:
            raise RuntimeError('How did you get there?')

        embed = Embed(
            title=f'{collage_type.capitalize()} {"collage" if owned_only else "album"}',
            description=collage_desc,
            color=WC_COLOR,
        )
        embed.set_image(url=collage.url)
        embed.set_author(name=member, icon_url=member.display_avatar.url)

        text = f'ID {collage_id} • ' if collage_id else ''
        if owned_only:
            text += f'{collage.owned} characters'
        else:
            text += f'{collage.owned}/{collage.total} characters'
            text += f' • {(100 * collage.owned / collage.total):.2f}% completed'
        embed.set_footer(text=text)

        await ctx.reply(embed=embed)

    #########
    # Track #
    #########

    slash_track = app_commands.Group(
        name='track', description='Track your favorite albums progress', parent=slash_waifu_global
    )

    @slash_track.command(name='list')
    @legacy_command()
    async def slash_track_list(self, ctx: LegacyCommandContext, member: UserType | None = None):
        """Track your favorite albums progress"""
        if member is None:
            member = ctx.author

        resp = await get_nanapi().waicolle.waicolle_get_player_tracked_items(member.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp.result)
        tracks = resp.result

        stats_tasks: list[
            asyncio.Task[
                Success[
                    Literal[200],
                    PlayerMediaStatsResult,
                ]
                | Success[
                    Literal[200],
                    PlayerStaffStatsResult,
                ]
                | Success[
                    Literal[200],
                    PlayerCollectionStatsResult,
                ]
                | Error[Any, Any]
            ]
        ] = []

        for media in tracks.tracked_medias:
            stats_tasks.append(
                asyncio.create_task(
                    get_nanapi().waicolle.waicolle_get_player_media_stats(member.id, media.id_al)
                )
            )
        for staff in tracks.tracked_staffs:
            stats_tasks.append(
                asyncio.create_task(
                    get_nanapi().waicolle.waicolle_get_player_staff_stats(member.id, staff.id_al)
                )
            )
        for collection in tracks.tracked_collections:
            stats_tasks.append(
                asyncio.create_task(
                    get_nanapi().waicolle.waicolle_get_player_collection_stats(
                        member.id, collection.id
                    )
                )
            )
        resps = (await t for t in stats_tasks)

        elems: list[tuple[float, str]] = []
        async for resp in resps:
            sub_lines: list[str] = []
            match resp:
                case Success(200, PlayerMediaStatsResult()):
                    stat = resp.result
                    desc = (
                        f'`[{stat.media.type[0]}-{stat.media.id_al}]` '
                        f'**{stat.media.title_user_preferred}**'
                    )
                case Success(200, PlayerStaffStatsResult()):
                    stat = resp.result
                    name_native = f' ({stat.staff.name_native})' if stat.staff.name_native else ''
                    desc = (
                        f'`[S-{stat.staff.id_al}]` '
                        f'**{stat.staff.name_user_preferred}{name_native}**'
                    )
                case Success(200, PlayerCollectionStatsResult()):
                    stat = resp.result

                    for media in stat.collection.medias:
                        sub_lines.append(
                            f'​　　`[{media.type[0]}-{media.id_al}]` {media.title_user_preferred}'
                        )

                    for staff in stat.collection.staffs:
                        name_native = f' ({staff.name_native})' if staff.name_native else ''
                        sub_lines.append(
                            f'​　　`[S-{staff.id_al}]` {staff.name_user_preferred}{name_native}'
                        )

                    desc = f'`[C]` **{stat.collection.name}**'
                case Error():
                    raise RuntimeError(resp.result)

            desc, percent = self._format_line(stat.nb_owned, stat.nb_charas, desc)

            if len(sub_lines) > 0:
                desc += '\n' + '\n'.join(sub_lines)

            bisect.insort(elems, (percent, desc), key=itemgetter(0))

        elems = sorted(elems, key=itemgetter(0), reverse=True)

        await AutoNavigatorView.create(
            self.bot,
            ctx.reply,
            title='Tracking list',
            description='\n'.join(map(itemgetter(1), elems)),
            color=WC_COLOR,
            author_name=str(member),
            author_icon_url=member.display_avatar.url,
        )

    @staticmethod
    def _format_line(nb_owned: int, nb_charas: int, *components: str):
        components = *components, f'**{nb_owned}/{nb_charas}** characters'
        if nb_charas > 0:
            percent = 100 * nb_owned / nb_charas
            completion = f'**{percent:.2f}%** completed'
            components = *components, completion
        else:
            percent = 0
        return ' • '.join(components), percent

    @slash_track.command(name='add')
    @app_commands.autocomplete(id=track_autocomplete)
    async def slash_track_add(
        self, interaction: Interaction[Bot], track_type: TrackChoice, id: str
    ):
        """Add a track"""
        await interaction.response.defer()

        if track_type is self.TrackChoice.media:
            media_id = await autocomplete_cast(interaction, self.track_autocomplete, int, id)
            resp = await get_nanapi().waicolle.waicolle_player_track_media(
                interaction.user.id, media_id
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        await interaction.followup.send('Not a player or media not found')
                        return
                    case _:
                        raise RuntimeError(resp.result)
            track = resp.result
            await interaction.followup.send(
                f'**{track.media.title_user_preferred}** ({track.media.type.casefold()}) '
                f'added to track list'
            )

        elif track_type is self.TrackChoice.staff:
            staff_id = await autocomplete_cast(interaction, self.track_autocomplete, int, id)
            resp = await get_nanapi().waicolle.waicolle_player_track_staff(
                interaction.user.id, staff_id
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        await interaction.followup.send('Not a player or staff not found')
                        return
                    case _:
                        raise RuntimeError(resp.result)
            track = resp.result
            name_native = f' ({track.staff.name_native})' if track.staff.name_native else ''
            await interaction.followup.send(
                f'Staff **{track.staff.name_user_preferred}{name_native}** added to track list'
            )

        elif track_type is self.TrackChoice.collection:
            collec_id = await autocomplete_cast(interaction, self.track_autocomplete, UUID, id)
            resp = await get_nanapi().waicolle.waicolle_player_track_collection(
                interaction.user.id, collec_id
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        await interaction.followup.send('Not a player or collection not found')
                        return
                    case _:
                        raise RuntimeError(resp.result)
            track = resp.result
            await interaction.followup.send(
                f'Collection **{track.collection.name}** added to track list'
            )
        else:
            raise RuntimeError('How did you get there?')

    @slash_track.command(name='remove')
    @app_commands.autocomplete(id=track_autocomplete)
    async def slash_track_remove(
        self, interaction: Interaction[Bot], track_type: TrackChoice, id: str
    ):
        """Remove a track"""
        await interaction.response.defer()
        if track_type is self.TrackChoice.media:
            media_id = await autocomplete_cast(interaction, self.track_autocomplete, int, id)
            resp = await get_nanapi().waicolle.waicolle_player_untrack_media(
                interaction.user.id, media_id
            )
        elif track_type is self.TrackChoice.staff:
            staff_id = await autocomplete_cast(interaction, self.track_autocomplete, int, id)
            resp = await get_nanapi().waicolle.waicolle_player_untrack_staff(
                interaction.user.id, staff_id
            )
        elif track_type is self.TrackChoice.collection:
            collec_id = await autocomplete_cast(interaction, self.track_autocomplete, UUID, id)
            resp = await get_nanapi().waicolle.waicolle_player_untrack_collection(
                interaction.user.id, collec_id
            )
        else:
            raise RuntimeError('How did you get there?')

        if not success(resp):
            raise RuntimeError(resp.result)

        await interaction.followup.send(self.bot.get_emoji_str('FubukiGO'))

    class TrackUnlockedSort(Enum):
        RECENT = 'recent'
        RANK = 'rank'

    @slash_track.command(name='unlocked')
    @legacy_command()
    async def slash_track_unlocked(
        self,
        ctx: LegacyCommandContext,
        hide_singles: bool,
        member: UserType | None = None,
        sort_by: TrackUnlockedSort = TrackUnlockedSort.RECENT,
    ):
        """List unlocked characters who are in your tracked medias that other own"""
        await ctx.defer()

        if member is None:
            member = ctx.author

        resp1 = await get_nanapi().waicolle.waicolle_get_player_track_unlocked(
            member.id, 1 if hide_singles else 0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        waifus = resp1.result

        if len(waifus) == 0:
            raise commands.CommandError(
                f'No unlocked tracklisted character found '
                f'{self.bot.get_emoji_str("saladedefruits")}'
            )

        chara_ids = ','.join(str(w.character.id_al) for w in waifus)
        resp2 = await get_nanapi().anilist.anilist_get_charas(chara_ids)
        if not success(resp2):
            raise RuntimeError(resp2.result)
        chara_map = {c.id_al: c for c in resp2.result}

        title = 'Unlocked tracklisted character list'
        if sort_by is self.TrackUnlockedSort.RANK:
            waifus = list(
                sorted(
                    waifus,
                    key=lambda w: (chara_map[w.character.id_al].favourites, w.timestamp),
                    reverse=True,
                )
            )

        custom_lines = (
            f'🏷 {self.bot.get_user(w.owner.user.discord_id)} • ID {w.character.id_al} • '
            for w in waifus
        )

        pages = self.list_paginator(member, waifus, title=title, custom_lines=custom_lines)
        await NavigatorView.create(self.bot, ctx.reply, pages=pages)

    @slash_track.command(name='reversed')
    @legacy_command()
    async def slash_track_reversed(
        self, ctx: LegacyCommandContext, hide_singles: bool, member: UserType | None = None
    ):
        """List unlocked characters that others want"""
        await ctx.defer()

        if member is None:
            member = ctx.author

        resp1 = await get_nanapi().waicolle.waicolle_get_player_track_reversed(
            member.id, 1 if hide_singles else 0
        )
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError(
                        f'**{member}** is not a player {self.bot.get_emoji_str("saladedefruits")}'
                    )
                case _:
                    raise RuntimeError(resp1.result)
        results = resp1.result

        if len(results) == 0:
            raise commands.CommandError(
                f'No one wants your unlocked characters {self.bot.get_emoji_str("saladedefruits")}'
            )

        chara_ids = ','.join(str(r.waifu.character.id_al) for r in results)
        resp2 = await get_nanapi().anilist.anilist_get_charas(chara_ids)
        if not success(resp2):
            raise RuntimeError(resp2.result)

        title = 'Reversed unlocked tracklisted character list'

        custom_lines = []
        for res in results:
            owners = defaultdict(WaifuOwnership)
            for waifu in res.locked:
                owner = owners[waifu.owner.user.discord_id]
                ownership = owner.locked
                if waifu.level == 0:
                    ownership.simple += 1
                if waifu.level == 1:
                    ownership.ascended += 1
                if waifu.level > 1:
                    ownership.double_ascended += 1

            text = []
            for id, entry in owners.items():
                subtext = str(self.bot.get_user(id))
                subtext += f' {entry.locked}'
                text.append(subtext)

            for tracker in res.trackers_not_owners:
                discord_id = tracker.user.discord_id
                if discord_id not in owners:
                    text.append(str(self.bot.get_user(discord_id)) + ' (**0**)')

            custom_lines.append('🔀 ' + ' • '.join(sorted(text, key=str.casefold)))

        pages = self.list_paginator(
            member,
            [cast(WaifuSelectResult, r.waifu) for r in results],  # FIXME: ugly cast
            title=title,
            custom_lines=custom_lines,
        )
        await NavigatorView.create(self.bot, ctx.reply, pages=pages)

    ###############
    # Collections #
    ###############

    slash_collec = app_commands.Group(
        name='collection',
        description='Track your favorite albums progress',
        parent=slash_waifu_global,
    )

    @slash_collec.command(name='new')
    @legacy_command()
    async def slash_collec_new(self, ctx: LegacyCommandContext, name: str):
        """Create a new collection"""
        body = NewCollectionBody(discord_id=ctx.author.id, name=name)
        resp = await get_nanapi().waicolle.waicolle_new_collection(body)
        if not success(resp):
            match resp.code:
                case 409:
                    raise commands.CommandError('You already have a collection with this name.')
                case _:
                    raise RuntimeError(resp.result)

        collec = resp.result
        await ctx.reply(f'Created collection **{collec.name}**')

    @slash_collec.command(name='delete')
    @app_commands.autocomplete(coll=collection_autocomplete())
    @app_commands.rename(coll='collection')
    async def slash_track_colle_delete(self, interaction: Interaction[Bot], coll: str):
        """Delete a collection"""
        await interaction.response.defer()
        cid = await autocomplete_cast(interaction, collection_autocomplete(), UUID, coll)

        resp1 = await get_nanapi().waicolle.waicolle_get_collection(cid)
        if not success(resp1):
            match resp1.code:
                case 404:
                    await interaction.followup.send('Collection not found.')
                    return
                case _:
                    raise RuntimeError(resp1.result)
        collec = resp1.result

        if collec.author.user.discord_id != interaction.user.id:
            await interaction.followup.send('You can only delete your own collections')
            return

        resp2 = await get_nanapi().waicolle.waicolle_delete_collection(cid)
        if not success(resp2):
            raise RuntimeError(resp2.result)
        await interaction.followup.send(self.bot.get_emoji_str('FubukiGO'))

    class CollecTrackChoice(Enum):
        media = 'media'
        staff = 'staff'

    @slash_collec.command(name='add')
    @app_commands.autocomplete(coll=collection_autocomplete(), item=track_autocomplete)
    @app_commands.rename(coll='collection')
    async def slash_track_colle_add(
        self, interaction: Interaction[Bot], coll: str, track_type: CollecTrackChoice, item: str
    ):
        """Add a media AniList ID to collection"""
        await interaction.response.defer()
        cid = await autocomplete_cast(interaction, collection_autocomplete(), UUID, coll)
        id_al = await autocomplete_cast(interaction, self.track_autocomplete, int, item)

        resp1 = await get_nanapi().waicolle.waicolle_get_collection(cid)
        if not success(resp1):
            match resp1.code:
                case 404:
                    raise commands.CommandError('Collection not found.')
                case _:
                    raise RuntimeError(resp1.result)
        collec = resp1.result
        if collec.author.user.discord_id != interaction.user.id:
            await interaction.followup.send('You can only edit your own collections')
            return

        if track_type is self.CollecTrackChoice.media:
            resp2 = await get_nanapi().waicolle.waicolle_collection_track_media(cid, id_al)
            if not success(resp2):
                match resp2.code:
                    case 404:
                        await interaction.followup.send('Media not found.')
                        return
                    case _:
                        raise RuntimeError(resp2.result)

            updated = resp2.result
            await interaction.followup.send(
                f'**{updated.media.title_user_preferred}** ({updated.media.type.casefold()}) '
                f'added to track collection {updated.collection.id} – {updated.collection.name}'
            )
        elif track_type is self.CollecTrackChoice.staff:
            resp2 = await get_nanapi().waicolle.waicolle_collection_track_staff(cid, id_al)
            if not success(resp2):
                match resp2.code:
                    case 404:
                        await interaction.followup.send('Staff not found.')
                        return
                    case _:
                        raise RuntimeError(resp2.result)

            updated = resp2.result
            name_native = f' ({updated.staff.name_native})' if updated.staff.name_native else ''
            await interaction.followup.send(
                f'**{updated.staff.name_user_preferred}{name_native}** '
                f'added to track collection {updated.collection.id} – {updated.collection.name}'
            )
        else:
            raise RuntimeError('How did you get there?')

    @slash_collec.command(name='remove')
    @app_commands.autocomplete(coll=collection_autocomplete(), item=track_autocomplete)
    @app_commands.rename(coll='collection')
    async def slash_track_colle_remove(
        self, interaction: Interaction[Bot], coll: str, track_type: CollecTrackChoice, item: str
    ):
        """Remove a media AniList ID from collection"""
        await interaction.response.defer()
        cid = await autocomplete_cast(interaction, collection_autocomplete(), UUID, coll)
        id_al = await autocomplete_cast(interaction, self.track_autocomplete, int, item)

        resp1 = await get_nanapi().waicolle.waicolle_get_collection(cid)
        if not success(resp1):
            match resp1.code:
                case 404:
                    await interaction.followup.send('Collection not found.')
                    return
                case _:
                    raise RuntimeError(resp1.result)
        collec = resp1.result

        if collec.author.user.discord_id != interaction.user.id:
            raise commands.CommandError('You can only edit your own collections')
        if track_type is self.CollecTrackChoice.media:
            resp2 = await get_nanapi().waicolle.waicolle_collection_untrack_media(cid, id_al)
        elif track_type is self.CollecTrackChoice.staff:
            resp2 = await get_nanapi().waicolle.waicolle_collection_untrack_staff(cid, id_al)
        else:
            raise RuntimeError('How did you get there?')

        if not success(resp2):
            raise RuntimeError(resp2.result)

        await interaction.followup.send(self.bot.get_emoji_str('FubukiGO'))

    ##########
    # Coupon #
    ##########
    slash_waifu_coupon = app_commands.Group(
        name='coupon', description='Coupon commands', parent=slash_waifu
    )

    @slash_waifu_coupon.command(name='list')
    @app_commands.check(is_admin_or_bureau)
    @legacy_command(ephemeral=True)
    async def coupon_list(self, ctx: LegacyCommandContext):
        """List coupons"""
        resp = await get_nanapi().waicolle.waicolle_get_coupons()
        if not success(resp):
            raise RuntimeError(resp.result)
        coupons = resp.result
        fields = [
            EmbedField(
                c.code,
                ' • '.join(str(self.bot.get_user(cc.user.discord_id)) for cc in c.claimed_by)
                or '*Empty*',
                inline=False,
            )
            for c in coupons
        ]
        await AutoNavigatorView.create(self.bot, ctx.reply, fields=fields)

    @slash_waifu_coupon.command(name='create')
    @app_commands.check(is_admin_or_bureau)
    @legacy_command(ephemeral=True)
    async def coupon_create(self, ctx: LegacyCommandContext, custom_code: str | None = None):
        """Create a new coupon"""
        resp = await get_nanapi().waicolle.waicolle_new_coupon(NewCouponBody(code=custom_code))
        if not success(resp):
            match resp.code:
                case 409:
                    raise commands.CommandError('Code already exists.')
                case _:
                    raise RuntimeError(resp.result)
        coupon = resp.result
        await ctx.reply(f'New coupon created: {coupon.code}')

    @slash_waifu_coupon.command(name='delete')
    @app_commands.check(is_admin_or_bureau)
    @legacy_command(ephemeral=True)
    async def coupon_delete(self, ctx: LegacyCommandContext, code: str):
        """Delete a coupon"""
        resp = await get_nanapi().waicolle.waicolle_delete_coupon(code)
        if not success(resp):
            raise RuntimeError(resp.result)
        await ctx.reply(f'Coupon {code} deleted')

    @slash_waifu_coupon.command(name='claim')
    @legacy_command(ephemeral=True)
    async def coupon_claim(self, ctx: LegacyCommandContext, code: str):
        """Claim a coupon"""
        await ctx.defer(ephemeral=True)
        await self._drop(ctx.author, 'Coupon drop', coupon_code=code, replyable=ctx)

    ##########
    # Reward #
    ##########

    async def reward_drop(self, user: discord.User, nb: int, reason: str):
        if user.bot:
            return

        await self._drop(user, reason, nb=nb, rollop_reason=reason.casefold())

    async def reward_coins(self, user: UserType, nb: int, reason: str, room_id: int = BOT_ROOM_ID):
        if user.bot:
            return

        room = self.bot.get_text_channel(room_id)
        assert room is not None

        if nb > 0:
            body = AddPlayerCoinsBody(moecoins=nb)
            resp = await get_nanapi().waicolle.waicolle_add_player_coins(user.id, body)
            if not success(resp):
                match resp.code:
                    case 404:
                        return
                    case _:
                        raise RuntimeError(resp.result)
            await room.send(
                f'{user} [**{reason}**] '
                f'You received **{nb}** {self.bot.get_emoji_str("moecoin")}! '
                f'{self.bot.get_emoji_str("hype")}'
            )
        else:
            await room.send(
                f'{user} [**{reason}**] '
                f'You received **{nb}** {self.bot.get_emoji_str("moecoin")}... '
                f'{self.bot.get_emoji_str("saladedefruits")}'
            )

    ##############
    # On message #
    ##############

    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if ctx.author.bot:
            return

        channel_types = discord.TextChannel, discord.VoiceChannel, discord.Thread
        if not isinstance(ctx.channel, channel_types):
            return

        if ctx.guild is None:
            return

        if ctx.command is not None:
            return

        if ctx.will_delete:
            return

        delta = await self.user_delta(ctx)
        try:
            async with asyncio.timeout(1):
                spam = await run_coro(is_spam(ctx))
        except Exception:
            logger.info('spam check failed horribly')
            print_exc()
            spam = False

        if spam:
            async for _ in conditional_drop.matching_conditions(ctx):
                spam = False

        if spam:
            self.ignored_messages[ctx.author.id] += 1
            logger.info(f'ignoring ({delta}) {ctx.author}: {ctx.message.content}')
            return

        self.accounted_messages[ctx.author.id] += 1
        self.log_user_messages(ctx.author)
        moecoin_gain = 1 + (delta // 3600)

        if self.is_dbl_zn():
            moecoin_gain *= 2

        moecoin_gain = min(72, moecoin_gain)
        moecoin_gain *= GLOBAL_COIN_MULTIPLIER

        if ctx.guild.id not in self.next_drop:
            self.next_drop[ctx.guild.id] = await self.drp_factory(ctx.guild.id)

        if ctx.bananased:
            self.next_drop[ctx.guild.id] += self.speed
            resp = await get_nanapi().waicolle.waicolle_add_player_coins(
                ctx.author.id, AddPlayerCoinsBody(moecoins=-moecoin_gain)
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        return
                    case _:
                        raise RuntimeError(resp.result)
        else:
            self.next_drop[ctx.guild.id] -= self.speed
            resp = await get_nanapi().waicolle.waicolle_add_player_coins(
                ctx.author.id, AddPlayerCoinsBody(moecoins=moecoin_gain)
            )
            if not success(resp):
                match resp.code:
                    case 404:
                        return
                    case _:
                        raise RuntimeError(resp.result)

        try:
            for role_id in (WC_ROLE,):
                if (role_id is None) or ((role := ctx.guild.get_role(role_id)) is None):
                    continue
                perms = ctx.channel.permissions_for(role)
                if perms.read_messages:
                    break
            else:
                return

            await conditional_drop(ctx, self)

            if ctx.channel.id == BOT_ROOM_ID:
                return

            if not isinstance(ctx.channel, discord.TextChannel):
                return

            if ctx.channel.nsfw:
                return

            await self.drop_on_message(ctx)

        finally:
            await self.save_drop(ctx.guild.id)

    async def user_delta(self, ctx: MultiplexingContext):
        latest_message = await user_latest_message.get(str(ctx.author.id))
        await user_latest_message.set(
            ctx.message.created_at.timestamp(), sub_key=str(ctx.author.id)
        )

        if latest_message is None:
            latest_message = self.start_time

        return ctx.message.created_at.timestamp() - latest_message

    @staticmethod
    def is_dbl_zn():
        now = datetime.now(tz=TZ)
        weekday = now.weekday()
        return weekday >= 5 or (weekday == 4 and now.hour >= 18)

    def log_user_messages(self, user: discord.User | discord.Member):
        total = self.ignored_messages[user.id] + self.accounted_messages[user.id]
        logger.info(f'{user} ignored messages: {self.ignored_messages[user.id]}/{total}')

    async def drp_factory(self, guild_id: int) -> int | float:
        # ignore redis connection errors, does mean we lose our progress
        try:
            if (redis_val := await next_drop.get(str(guild_id))) is not None:
                return redis_val
        except Exception:
            pass

        return self._drp_factory()

    def _drp_factory(self):
        return RNG.integers(1, DROP_RATE, dtype=int, endpoint=True)

    async def save_drop(self, guild_id: int):
        return await next_drop.set(self.next_drop[guild_id], str(guild_id))

    async def drop_on_message(self, ctx, force: bool = False):
        async with self.drp_lock[ctx.guild.id]:
            if force or self.next_drop[ctx.guild.id] <= 0:
                listener = WaifuDropReactionListener(self, ctx.message)
                dropped = False

                with suppress(asyncio.TimeoutError):
                    while True:
                        async with asyncio.timeout(WaifuDropReactionListener.timeout):
                            user = await listener.queue.get()

                        dropped = True
                        asyncio.create_task(
                            self._drop(user, 'Random drop', rollop_reason='random')
                        )

                if dropped:
                    self.next_drop[ctx.guild.id] = self._drp_factory()


def user_menu_trade(cog: WaifuCollection):
    @app_commands.context_menu(name='Waifu trade')
    @app_commands.guild_only()
    @handle_command_errors
    async def user_trade(interaction: discord.Interaction[Bot], member: discord.Member):
        ctx = await LegacyCommandContext.from_interaction(interaction)
        await cog._trade(ctx, member)

    return user_trade


async def setup(bot: Bot):
    cog = WaifuCollection(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(user_menu_trade(cog))
