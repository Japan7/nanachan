import asyncio
import calendar
import re
from dataclasses import asdict
from operator import attrgetter
from typing import Any, Callable

import discord
from discord.app_commands import Choice
from discord.ui import Button
from html2text import HTML2Text as HTML2md
from toolz import partition_all
from toolz.curried import compose_left
from yarl import URL

from nanachan.discord.bot import Bot
from nanachan.discord.helpers import Embed, EmbedField
from nanachan.discord.views import NavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import MediaSelectResult, MediaType, StaffSelectResult
from nanachan.settings import NANAPI_PUBLIC_URL
from nanachan.utils.misc import autocomplete_truncate

STAFF_GARBAGE = re.compile(r"\s+")
AL_COLOR = int('48A9F8', 16)
PER_PAGE = 10

html2md = HTML2md()
html2md.body_width = 0
html2md.single_line_break = True


class MediaScoreButton(Button):

    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__(emoji=self.bot.get_emoji_str('yuniiZOOM'),
                         label='Scores',
                         style=discord.ButtonStyle.green,
                         disabled=True)
        self.event = asyncio.Event()

    async def load(self, media: MediaSelectResult, og_embed: Embed):
        self.event.clear()

        self.media = media
        self.og_embed = og_embed

        fields = await get_score_fields(self.bot, media)
        self.fields_partitions = list(partition_all(15, fields))

        self.disabled = len(self.fields_partitions) == 0
        self.curr_ind = 0
        self.label = f"Scores #{self.curr_ind}/{len(self.fields_partitions)}" if len(
            self.fields_partitions) > 0 else 'No score'

        self.event.set()

    async def callback(self, interaction: discord.Interaction):
        await self.event.wait()

        self.curr_ind += 1
        self.curr_ind %= len(self.fields_partitions) + 1
        self.label = f"Scores #{self.curr_ind}/{len(self.fields_partitions)}"

        assert interaction.message is not None
        embeds = interaction.message.embeds
        if self.curr_ind == 0:
            embeds[0] = self.og_embed
        else:
            embeds[0].clear_fields()
            embeds[0].description = None
            for field in self.fields_partitions[self.curr_ind - 1]:
                embeds[0].add_field(**asdict(field))

        await interaction.response.edit_message(embeds=embeds, view=self.view)


class MediaNavigator(NavigatorView):

    def __init__(self, *args, medias: list[MediaSelectResult], **kwargs):
        super().__init__(*args, **kwargs)
        self.medias = medias
        self.score_button = MediaScoreButton(self.bot)
        self.add_item(self.score_button)

    async def get_page(self, new_page: int):
        page = await super().get_page(new_page)
        embed = page['embed'] if 'embed' in page else page['embeds'][0]
        await self.score_button.load(self.medias[new_page], embed)
        return page

    @classmethod
    async def create(cls,
                     bot,
                     send_function: Callable,
                     *,
                     medias: list[MediaSelectResult],
                     static_content: str | None = None,
                     start_at: int = 1,
                     prefetch_min_batch_size: int = 5,
                     prefetch_pages: int = 5,
                     **kwargs):

        return await super().create(
            bot,
            send_function,
            pages=[media_page(media) for media in medias],
            static_content=static_content,
            start_at=start_at,
            prefetch_min_batch_size=prefetch_min_batch_size,
            prefetch_pages=prefetch_pages,
            medias=medias,
            **kwargs)


async def media_embed(media: MediaSelectResult):
    if (color := media.cover_image_color) is not None:
        color = int(color[1:], 16)
    else:
        color = AL_COLOR

    description = html2md.handle(media.description or '').strip()

    embed = Embed(title=media.title_user_preferred,
                  description=description,
                  color=color,
                  url=media.site_url)
    embed.set_image(url=f"https://img.anili.st/media/{media.id_al}")
    embed.set_author(
        name='AniList',
        url='https://anilist.co/',
        icon_url='https://anilist.co/img/icons/msapplication-icon-144x144.png')

    text = f"ID {media.id_al}"
    embed.set_footer(text=text)

    return embed


async def media_page(media: MediaSelectResult) -> dict[str, Embed]:
    embed = await media_embed(media)
    return dict(embed=embed)


async def get_score_fields(bot: Bot, media: MediaSelectResult):
    resp = await get_nanapi().anilist.anilist_get_media_list_entries(
        media.id_al,)
    if not success(resp):
        raise RuntimeError(resp.result)
    entries = resp.result

    total = (media.episodes
             if media.type == MediaType.ANIME else media.chapters) or '?'

    fields = []
    for entry in entries:
        status = entry.status.capitalize()
        if status != 'Completed':
            progress = f" ({entry.progress}/" + str(total) + ')'
        else:
            progress = ''

        score = f"\nScored {entry.score:.2f}/10" if entry.score else ''
        fields.append(
            EmbedField(name=str(bot.get_user(entry.account.user.discord_id)),
                       value=status + progress + score))

    return sorted(fields, key=compose_left(attrgetter('name'), str.casefold))


def media_autocomplete(media_type: MediaType | None = None,
                       id_al_as_value: bool = False):

    async def autocomplete(interaction: discord.Interaction, current: str):
        resp = await get_nanapi().anilist.anilist_media_title_autocomplete(
            current, media_type.value if media_type is not None else None)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result

        choices: list[Choice] = []
        for r in results:
            name = r.title_user_preferred
            if id_al_as_value:
                name = f"{r.id_al} — {name}"
            if media_type is None:
                name = f"[{r.type[:1]}] {name}"
            value = str(r.id_al) if id_al_as_value else autocomplete_truncate(
                r.title_user_preferred)
            choices.append(Choice(name=autocomplete_truncate(name),
                                  value=value))

        return choices

    return autocomplete


async def staff_embed(staff: StaffSelectResult):
    title = STAFF_GARBAGE.sub(" ", staff.name_user_preferred)
    if staff.name_native is not None:
        title += f" ({staff.name_native})"

    embed = Embed(title=title, color=AL_COLOR, url=staff.site_url)
    embed.set_author(
        name='AniList',
        url='https://anilist.co/',
        icon_url='https://anilist.co/img/icons/msapplication-icon-144x144.png')
    embed.set_thumbnail(url=staff.image_large)

    embed.add_field(name='Favourites', value=f"{staff.favourites}")

    if (gender := staff.gender) is not None:
        embed.add_field(name='Gender', value=gender)

    if staff.age is not None:
        embed.add_field(name='Age', value=staff.age)

    birth = None
    if staff.date_of_birth_month is not None:
        birth = calendar.month_name[staff.date_of_birth_month]
        if staff.date_of_birth_day is not None:
            birth += f" {staff.date_of_birth_day}"
            if staff.date_of_birth_year is not None:
                birth += f", {staff.date_of_birth_year}"
    if birth is not None:
        embed.add_field(name='Birthday', value=birth)

    death = None
    if staff.date_of_death_month is not None:
        death = calendar.month_name[staff.date_of_death_month]
        if staff.date_of_death_day is not None:
            death += f" {staff.date_of_death_day}"
            if staff.date_of_death_year is not None:
                death += f", {staff.date_of_death_year}"
    if death is not None:
        embed.add_field(name='Death', value=death)

    resp = await get_nanapi().anilist.anilist_get_staff_chara_edges(staff.id_al)
    if not success(resp):
        raise RuntimeError(resp.result)
    edges = resp.result

    if edges:
        charas_map = {e.character.id_al: e.character.favourites for e in edges}
        sorted_ids = sorted(charas_map,
                            key=lambda id: charas_map[id],
                            reverse=True)
        ids_al_str = ','.join(map(str, sorted_ids))
        url = URL(f"{NANAPI_PUBLIC_URL}/anilist/charas/collages").with_query(
            ids_al=ids_al_str, hide_no_images=1)
        embed.set_image(url=url)

    text = f"ID {staff.id_al}"
    embed.set_footer(text=text)

    return embed


async def staff_page(staff: StaffSelectResult) -> dict[str, Any]:
    embed = await staff_embed(staff)
    page: dict[str, Any] = dict(embed=embed)
    return page


def staff_autocomplete(id_al_as_value: bool = False):

    async def autocomplete(interaction: discord.Interaction, current: str):
        resp = await get_nanapi().anilist.anilist_staff_name_autocomplete(
            current)
        if not success(resp):
            raise RuntimeError(resp.result)
        results = resp.result
        choices: list[Choice] = []
        for r in results:
            native = f" ({r.name_native})" if r.name_native else ''
            choice = Choice(
                name=autocomplete_truncate(f"{r.name_user_preferred}{native}"),
                value=(str(r.id_al) if id_al_as_value else
                       autocomplete_truncate(r.name_user_preferred)))
            choices.append(choice)

        return choices

    return autocomplete
