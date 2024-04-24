from functools import partial
from operator import attrgetter, itemgetter
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.ui import Button
from toolz.curried import compose_left

from nanachan.discord.application_commands import LegacyCommandContext, NanaGroup, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import EmbedField, MultiplexingContext
from nanachan.discord.views import AutoNavigatorView, LockedView, NavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import AnilistService, MediaType, UpsertAnilistAccountBody
from nanachan.utils.anilist import (
    AL_COLOR,
    MediaNavigator,
    media_autocomplete,
    staff_autocomplete,
    staff_page,
)

if TYPE_CHECKING:
    from nanachan.extensions.profiles import Profiles


class Anilist(Cog):
    """ Look up anime and manga on AniList/MyAnimeList """
    emoji = '📺'

    @Cog.listener()
    async def on_ready(self):
        profiles_cog = cast('Profiles', self.bot.get_cog('Profiles'))
        profiles_cog.registrars['AniList and MyAnimeList'] = self.register

    ###############
    # Registering #
    ###############

    async def _register_username(self, service: AnilistService,
                                 interaction: discord.Interaction):

        def check(m: MultiplexingContext) -> bool:
            return m.author == interaction.user

        await interaction.response.edit_message(view=None)

        await interaction.followup.send(
            content=f"{interaction.user.mention}\nWhat is your account username?"
        )
        resp = await MultiplexingContext.set_will_delete(check=check)
        answer = resp.message
        username = answer.content

        resp1 = await get_nanapi().anilist.anilist_upsert_account(
            interaction.user.id,
            UpsertAnilistAccountBody(discord_username=str(interaction.user),
                                     service=service.value,
                                     username=username))
        if not success(resp1):
            raise RuntimeError(resp1.result)

        await interaction.followup.send(
            content=self.bot.get_emoji_str('FubukiGO'))

    async def register(self, interaction: discord.Interaction):
        """Register or change a member AL/MAL account"""
        view = LockedView(self.bot, interaction.user)

        al_button = Button(emoji=self.bot.get_emoji_str('amoesip'),
                           label='AniList',
                           style=ButtonStyle.blurple)
        al_button.callback = partial(self._register_username,
                                     AnilistService.ANILIST)
        view.add_item(al_button)

        mal_button = Button(emoji=self.bot.get_emoji_str('saladedefruits'),
                            label='MyAnimeList',
                            style=ButtonStyle.blurple)
        mal_button.callback = partial(self._register_username,
                                      AnilistService.MYANIMELIST)
        view.add_item(mal_button)

        await interaction.response.edit_message(view=None)

        await interaction.followup.send(
            content=f"{interaction.user.mention}\nSelect your tracking service",
            view=view)

    ###########
    # Helpers #
    ###########

    async def get_accounts(self, ctx: commands.Context):
        """Get members AL/MAL links."""
        llist = []
        services = {}

        resp = await get_nanapi().anilist.anilist_get_accounts()
        if not success(resp):
            raise RuntimeError(resp.result)
        anilists = resp.result
        for anilist in anilists:
            member = self.bot.get_user(anilist.user.discord_id)
            link = ''
            if anilist.service is AnilistService.ANILIST:
                link = f"https://anilist.co/user/{anilist.username}"
            elif anilist.service is AnilistService.MYANIMELIST:
                link = f"https://myanimelist.net/profile/{anilist.username}"
            llist.append(
                EmbedField(str(member), f"[{anilist.service.value}]({link})"))
            services[anilist.service] = services.get(anilist.service, 0) + 1

        llist = sorted(llist,
                       key=compose_left(attrgetter('name'), str.casefold))

        services = sorted(services.items(), key=itemgetter(1), reverse=True)
        services = [f"{count} {service.value}" for service, count in services]

        await AutoNavigatorView.create(
            self.bot,
            ctx.reply,
            title='Registered lists',
            fields=llist,
            color=AL_COLOR,
            author_name=str(ctx.guild),
            author_icon_url=getattr(getattr(ctx.guild, 'icon', None), 'url', None),
            footer_text=f"{len(llist)} users • {', '.join(services)}")

    async def media_search(self, search: str, media_type: MediaType):
        resp = await get_nanapi().anilist.anilist_media_search(
            media_type.value, search)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        if len(results) == 0:
            raise commands.CommandError("No results found")
        return results

    async def staff_search(self, search: str):
        resp = await get_nanapi().anilist.anilist_staff_search(search)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        if len(results) == 0:
            raise commands.CommandError("No results found")
        return results

    ############
    # Commands #
    ############

    slash_anilist = NanaGroup(name="anilist")
    slash_anime = NanaGroup(name="anime")
    slash_manga = NanaGroup(name="manga")
    slash_staff = NanaGroup(name="staff")

    @slash_anilist.command()
    @legacy_command()
    async def accounts(self, ctx: LegacyCommandContext):
        """Get members AL/MAL links."""
        await self.get_accounts(ctx)

    @slash_anime.command(name='search')
    @app_commands.autocomplete(
        search=media_autocomplete(media_type=MediaType.ANIME))
    @legacy_command()
    async def asearch(self, ctx: LegacyCommandContext, search: str):
        """Search an anime on AniList and check who watched it."""
        results = await self.media_search(search, MediaType.ANIME)
        await MediaNavigator.create(self.bot, ctx.reply, medias=results)

    @slash_manga.command(name='search')
    @app_commands.autocomplete(
        search=media_autocomplete(media_type=MediaType.MANGA))
    @legacy_command()
    async def msearch(self, ctx: LegacyCommandContext, search: str):
        """Search a manga on AniList and check who read it."""
        results = await self.media_search(search, MediaType.MANGA)
        await MediaNavigator.create(self.bot, ctx.reply, medias=results)

    @slash_staff.command(name='search')
    @app_commands.autocomplete(search=staff_autocomplete())
    @legacy_command()
    async def ssearch(self, ctx: LegacyCommandContext, search: str):
        """Search a staff on AniList."""
        results = await self.staff_search(search)
        await NavigatorView.create(self.bot, ctx.reply,
                                   pages=[staff_page(s) for s in results])

    @slash_anilist.command(name='recommendations')
    @legacy_command()
    async def user_reco(self,
                        ctx: LegacyCommandContext,
                        user: discord.User | discord.Member | None = None):
        """Get your recommendations."""
        if not user:
            user = ctx.author
        resp = await get_nanapi().anilist.anilist_get_account_recommendations(
            user.id)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        if not results:
            raise commands.CommandError("No recommendations found")
        desc = []
        for i, r in enumerate(results):
            desc.append(
                f"`{i + 1}.` "
                f"**{r.score:.2f}** – "
                f"[{r.media.type.value[:1]}] [{r.media.title_user_preferred}]({r.media.site_url})"
            )
        await AutoNavigatorView.create(self.bot,
                                       ctx.reply,
                                       title='Top recommendations',
                                       description='\n'.join(desc),
                                       color=AL_COLOR,
                                       author_name=str(user),
                                       author_icon_url=user.display_avatar.url)


async def setup(bot: Bot):
    await bot.add_cog(Anilist(bot))
