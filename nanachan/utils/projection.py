import asyncio
from datetime import datetime
from functools import partial
from uuid import UUID

import discord
from discord.ui import Button

from nanachan.discord.bot import Bot
from nanachan.discord.helpers import Embed
from nanachan.discord.views import BaseView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import MediaSelectResult, ProjectionStatus, ProjoSelectResultMedias
from nanachan.settings import NANAPI_PUBLIC_URL, TZ
from nanachan.utils.anilist import MediaNavigator


async def get_active_projo(channel_id: int):
    resp = await get_nanapi().projection.projection_get_projections(
        channel_id=channel_id, status=ProjectionStatus.ONGOING.value
    )
    if not success(resp):
        raise RuntimeError(resp.result)
    projos = resp.result
    return projos[0] if len(projos) > 0 else None


async def get_projo_embed_view(bot: Bot, projo_id: UUID):
    resp = await get_nanapi().projection.projection_get_projection(projo_id)
    if not success(resp):
        raise RuntimeError(resp.result)
    projection = resp.result

    thread = bot.get_thread(projection.channel_id)
    if thread is None:
        thread = await bot.fetch_thread(projection.channel_id)

    description = []
    thumbnail_id = None
    duration = 0

    al_medias_dict: dict[int, MediaSelectResult] = {}
    ids_al_str = None
    if len(projection.medias) > 0:
        ids_al = [media.id_al for media in projection.medias]
        ids_al_str = ','.join(map(str, ids_al))
        resp = await get_nanapi().anilist.anilist_get_medias(ids_al_str)
        if not success(resp):
            raise RuntimeError(resp.result)

        al_medias = resp.result
        al_medias_dict = {media.id_al: media for media in al_medias}

    all_medias = projection.medias + projection.external_medias
    for media in sorted(
        all_medias, key=lambda m: m.added_alias if m.added_alias is not None else 0
    ):
        if isinstance(media, ProjoSelectResultMedias):
            anime = al_medias_dict[media.id_al]

            description.append(
                f"{anime.title_user_preferred} "
                f"({anime.episodes or '??'} eps, "
                f"[{anime.id_al}](https://anilist.co/anime/{anime.id_al}))"
            )

            if duration != -1:
                if anime.episodes is not None and anime.duration is not None:
                    duration += anime.episodes * anime.duration
                else:
                    duration = -1  # STOP THE COUNT! (we don"t want a partial duration)

            if thumbnail_id is None:
                thumbnail_id = anime.id_al
        else:
            description.append(media.title)

    embed = Embed(title=projection.name, description='\n'.join(description), color=0x9966CC)

    if ids_al_str is not None:
        embed.set_thumbnail(url=f'{NANAPI_PUBLIC_URL}/anilist/medias/collages?ids_al={ids_al_str}')

    embed.add_field(name='Thread', value=thread.mention)

    members = await thread.fetch_members()
    users = [u for u in map(bot.get_user, (m.id for m in members)) if u is not None and not u.bot]

    names = [str(u) for u in users]
    footer = ' | '.join(sorted(names, key=str.casefold))
    embed.set_footer(text=footer)

    if duration > 0:
        embed.add_field(name='Duration', value=f'{duration//60:02}h{duration%60:02}')

    if len(projection.guild_events) > 0:
        now = datetime.now(tz=TZ)
        value = '\n'.join(
            f'**{e.start_time.astimezone(TZ)}** • {e.name}'
            for e in projection.guild_events
            if e.start_time >= now
        )
        if value:
            embed.add_field(name='Upcoming Events', value=value, inline=False)

    view = ProjectionView(bot, projection.id)
    view.infos_bt.disabled = len(projection.medias) == 0

    return embed, view


class ProjectionInfosButton(Button):
    def __init__(self, bot: Bot, projo_id: UUID):
        self.bot = bot
        self.projo_id = projo_id
        super().__init__(
            emoji=self.bot.get_nana_emoji('AquaInspect'),
            label='AniList search',
            style=discord.ButtonStyle.blurple,
            custom_id=f'projo-infos-{self.projo_id}',
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        resp = await get_nanapi().projection.projection_get_projection(self.projo_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        projo = resp.result

        ids_al = [media.id_al for media in projo.medias]
        ids_al_str = ','.join(map(str, ids_al))
        resp = await get_nanapi().anilist.anilist_get_medias(ids_al_str)
        if not success(resp):
            raise RuntimeError(resp.result)
        al_medias = resp.result
        al_medias_dict = {media.id_al: media for media in al_medias}

        medias = [al_medias_dict[m.id_al] for m in projo.medias]
        send_func = partial(interaction.followup.send, ephemeral=True)
        await MediaNavigator.create(self.bot, send_func, medias=medias)


class ProjectionView(BaseView):
    JOIN_EMOTE = '\N{CALENDAR}'

    def __init__(self, bot: Bot, projo_id: UUID):
        super().__init__(bot)
        self.projo_id = projo_id

        self.join_bt = Button(
            emoji=self.JOIN_EMOTE,
            label='Join thread',
            style=discord.ButtonStyle.green,
            custom_id=f'projo-join-{self.projo_id}',
        )
        self.join_bt.callback = self.join
        self.add_item(self.join_bt)

        self.infos_bt = ProjectionInfosButton(self.bot, self.projo_id)
        self.add_item(self.infos_bt)

    async def join(self, interaction: discord.Interaction):
        resp = await get_nanapi().projection.projection_get_projection(self.projo_id)
        if not success(resp):
            raise RuntimeError(resp.result)
        projo = resp.result

        thread = self.bot.get_thread(projo.channel_id)
        assert thread is not None

        asyncio.create_task(thread.add_user(interaction.user))
        embed, view = await get_projo_embed_view(self.bot, projo.id)
        await interaction.response.edit_message(embed=embed, view=view)
