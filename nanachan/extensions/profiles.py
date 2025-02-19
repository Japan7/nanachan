import asyncio
import logging
import re
from datetime import date, datetime, timezone
from functools import partial
from operator import itemgetter
from typing import Protocol, TypedDict, override

import discord
import discord.ext
from dateutil.parser import parse
from discord import Interaction, Member, Role, SelectOption, app_commands, ui
from discord.ui import Button

from nanachan.discord.application_commands import (
    LegacyCommandContext,
    legacy_command,
    nana_command,
)
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Embed, MultiplexingContext
from nanachan.discord.views import AutoNavigatorView, BaseView, LockedView
from nanachan.nanapi._client import Error, Success
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    ProfileSearchResult,
    UpsertDiscordAccountBodyItem,
    UpsertProfileBody,
)
from nanachan.settings import YEAR_ROLES
from nanachan.utils.misc import to_producer

logger = logging.getLogger(__name__)


class RegistrarProtocol(Protocol):
    async def __call__(self, interaction: Interaction): ...


class Profiles(Cog):
    """QUOI ?! IL S'APPELLE BOULMECK ?!"""

    emoji = '💳'

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.registrars: dict[str, RegistrarProtocol] = {}

    @Cog.listener()
    async def on_ready(self):
        all_members = {member for guild in self.bot.guilds for member in guild.members}
        await get_nanapi().user.user_upsert_discord_accounts(
            [
                UpsertDiscordAccountBodyItem(discord_id=member.id, discord_username=str(member))
                for member in all_members
            ]
        )

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        year_role = [role.id for role in after.roles if role.id in YEAR_ROLES]
        if len(year_role) != 1:
            return
        year_role = year_role[0]

        if year_role == YEAR_ROLES[0]:  # 4A+
            return

        # skip if role was already there
        for role in before.roles:
            if year_role == role.id:
                return

        current_date = datetime.now()
        graduation_year_offset = 1 if current_date.month >= 7 else 0
        graduation_year = (
            current_date.year + graduation_year_offset + YEAR_ROLES.index(year_role) - 1
        )

        user_profile = UpsertProfileBody(
            discord_username=after.name, graduation_year=graduation_year
        )
        await get_nanapi().user.user_upsert_profile(discord_id=after.id, body=user_profile)

    async def _update_year_roles(
        self, members: list[Member], year_roles: list[Role], target_roles: list[Role]
    ):
        for member, target_role in zip(members, target_roles):
            await member.remove_roles(*year_roles)
            await member.add_roles(target_role)

        logger.info('done syncing member year roles')

    @staticmethod
    def next_birthday(birthdate: datetime):
        today = date.today()
        today = today.replace()
        birthday = birthdate.date()
        if birthday < today:
            birthday = birthday.replace(year=today.year + 1)
        return birthday

    @nana_command(description='Display birthdays of registered Japan7 members')
    @app_commands.guild_only()
    async def birthdays(self, interaction: Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        assert guild is not None
        resp = await get_nanapi().user.user_profile_search(
            ','.join(str(m.id) for m in guild.members)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result
        birthdays = [
            (
                self.next_birthday(p.birthday),
                p.full_name if p.full_name else guild.get_member(p.user.discord_id),
            )
            for p in profiles
            if p.birthday
        ]
        birthdays.sort()
        message_text = [f"**{b[0].strftime("%d/%m")}** • {b[1]}" for b in birthdays]
        icon_url = None if guild.icon is None else guild.icon.url
        await AutoNavigatorView.create(
            self.bot,
            interaction.followup.send,
            title='Japan7 birthdays',
            description='\n'.join(message_text),
            author_name=str(guild),
            author_icon_url=icon_url,
        )

    @nana_command(description='refresh promo roles')
    @app_commands.guild_only()
    async def promo(self, interaction: Interaction):
        """Refresh promo roles"""
        await interaction.response.defer()

        guild = interaction.guild
        assert guild is not None

        resp = await get_nanapi().user.user_profile_search(
            ','.join(str(m.id) for m in guild.members)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result
        now = datetime.now()
        last_promo = now.year if now.month >= 7 else now.year - 1
        year_roles = [
            role for role in (guild.get_role(id) for id in YEAR_ROLES) if role is not None
        ]
        new_roles = []
        members = []
        for profile in profiles:
            if profile.graduation_year is None:
                continue
            member = guild.get_member(profile.user.discord_id)
            if member is None:
                continue
            role_index = max(profile.graduation_year - last_promo, 0)
            new_roles.append(year_roles[role_index])
            members.append(member)

        asyncio.create_task(self._update_year_roles(members, year_roles, new_roles))

        text = [
            f'**{member}** • [**{role}**] {profile.full_name}'
            for member, profile, role in zip(members, profiles, new_roles)
        ]
        text.sort(key=str.casefold)

        icon_url = None if guild.icon is None else guild.icon.url
        await AutoNavigatorView.create(
            self.bot,
            interaction.followup.send,
            title='ENSEEIHT members',
            description='\n'.join(text),
            author_name=str(guild),
            author_icon_url=icon_url,
            footer_text=f'{len(text)} members',
        )

    @staticmethod
    async def _create_or_update_profile(member: Member | discord.User, payload: UpsertProfileBody):
        resp = await get_nanapi().user.user_upsert_profile(member.id, payload)
        if not success(resp):
            raise RuntimeError(resp.result)
        profile = resp.result
        return profile

    @staticmethod
    def create_embed(member: Member, profile: ProfileSearchResult | UpsertProfileBody):
        embed = Embed(colour=getattr(member, 'colour', None))
        embed.set_author(name=member, icon_url=member.display_avatar.url)

        if profile.full_name is not None:
            embed = embed.add_field(name='氏名', value=profile.full_name)

        if profile.graduation_year:
            embed.add_field(name='学級', value=profile.graduation_year)

        if profile.n7_major:
            embed.add_field(name='専門', value=profile.n7_major)

        if profile.pronouns:
            embed.add_field(name='代名詞', value=profile.pronouns)

        if profile.birthday:
            embed.add_field(name='誕生日', value=datetime.strftime(profile.birthday, '%Y-%m-%d'))

        if profile.telephone:
            embed.add_field(name='携帯番号', value=profile.telephone)

        if profile.photo:
            embed.set_thumbnail(url=profile.photo)

        return embed

    @nana_command()
    @legacy_command()
    async def register(self, ctx: LegacyCommandContext):
        """Register yourself into Nana-chan"""
        registrars = sorted(self.registrars.items(), key=itemgetter(0))

        desc = []
        view = LockedView(self.bot, ctx.author)
        for name, callback in registrars:
            emoji = callback.__self__.__class__.emoji  # type: ignore
            desc.append(f'{emoji} **{name}**\n{callback.__doc__}')
            button = Button(label=name, emoji=emoji)
            button.callback = callback
            view.add_item(button)

        embed = Embed(title=f'{self.emoji} Register', description='\n\n'.join(desc))
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        await ctx.reply(
            content=f"React with the {self.bot.get_emoji_str('chousen')} option",
            embed=embed,
            view=view,
        )

    @nana_command(description='Edit your own profile.')
    @legacy_command()
    async def iam(self, ctx: LegacyCommandContext):
        assert ctx.guild
        member = ctx.guild.get_member(ctx.author.id)
        profile_resp = await get_nanapi().user.user_get_profile(ctx.author.id)
        match profile_resp:
            case Success():
                profile = profile_upsert_body_from_search_result(
                    ctx.author.name, profile_resp.result
                )
            case Error(code=404):
                profile = UpsertProfileBody(discord_username=ctx.author.name)
            case _:
                raise RuntimeError(profile_resp.result)
        assert member
        embed = self.create_embed(member, profile)
        await ctx.send(embed=embed, view=ProfileCreateOrChangeView(self.bot, member, profile))

    @nana_command(description="Display other user's profile.")
    @legacy_command()
    async def whois(self, ctx: LegacyCommandContext, other: discord.User):
        profile_resp = await get_nanapi().user.user_get_profile(other.id)
        match profile_resp:
            case Success():
                pass
            case Error(code=404):
                await ctx.reply('User has no registered profile.')
                return
            case _:
                raise RuntimeError(profile_resp.result)

        profile = profile_resp.result
        assert ctx.guild
        member = ctx.guild.get_member(other.id)
        assert member
        await ctx.send(embed=self.create_embed(member, profile))


class ModalDict(TypedDict):
    birthday: datetime | None
    full_name: str | None
    graduation_year: int | None
    pronouns: str | None
    telephone: str | None


class ProfileModal(ui.Modal):
    birthday_regex = re.compile(r'^(\d{4}-\d{2}-\d{2})?$')
    graduation_year_regex = re.compile(r'^(\d{4})?$')
    telephone_regex = re.compile(r'^((\+33)|0\d{9}$)?')

    def __init__(self, *, title: str, profile: UpsertProfileBody):
        super().__init__(title=title)
        self.profile = profile
        default_birthday = (
            self.profile.birthday.strftime('%Y-%m-%d') if self.profile.birthday else None
        )

        TextInput = ui.TextInput[ProfileModal]

        self.birthday = TextInput(
            label='Birthdate',
            placeholder='Enter your birthdate (YYYY-MM-DD)',
            style=discord.TextStyle.short,
            required=False,
            default=default_birthday,
        )
        self.full_name = TextInput(
            label='Full Name',
            placeholder='Enter you full name (First name Last name)',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile.full_name,
        )
        default_graduation_year = (
            str(self.profile.graduation_year) if self.profile.graduation_year else ''
        )
        self.graduation_year = TextInput(
            label='Graduation Year',
            placeholder='Enter your graduation year',
            style=discord.TextStyle.short,
            required=False,
            default=default_graduation_year,
        )
        self.pronouns = TextInput(
            label='Pronouns',
            placeholder='Enter your prnouns',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile.pronouns,
        )
        self.telephone = TextInput(
            label='Phone Number',
            placeholder='Enter your phone number',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile.telephone,
        )

        self.add_item(self.birthday)
        self.add_item(self.full_name)
        self.add_item(self.graduation_year)
        self.add_item(self.pronouns)
        self.add_item(self.telephone)

    @override
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        errors: list[str] = []
        if not self.birthday_regex.fullmatch(self.birthday.value):
            errors.append('Invalid birthday format.')
        if not self.graduation_year_regex.fullmatch(self.graduation_year.value):
            errors.append('Invalid graduation year.')
        if not self.telephone_regex.fullmatch(self.telephone.value):
            errors.append('Invalid phone number')
        response = (
            '\n'.join(errors) if len(errors) > 0 else 'All information gathered succesfully.'
        )

        if not errors:
            self.profile.birthday = self.parse_date(self.birthday.value)
            self.profile.full_name = self.full_name.value or None
            self.profile.graduation_year = self.parse_int(self.graduation_year.value)
            self.profile.pronouns = self.pronouns.value or None
            self.profile.telephone = self.telephone.value or None
        await interaction.followup.send(response, ephemeral=True)

    @staticmethod
    def parse_date(date_str: str):
        return parse(date_str).replace(tzinfo=timezone.utc) if date_str else None

    @staticmethod
    def parse_int(i: str):
        return int(i) if i else None


class ProfileCreateOrChangeView(BaseView):
    def __init__(self, bot: Bot, member: Member, profile: UpsertProfileBody):
        super().__init__(bot)
        self.member = member
        self.profile = profile

        n7_major_select = ui.Select[ProfileCreateOrChangeView](
            placeholder='Select your major at N7',
            options=[
                SelectOption(emoji='⚡', label='Elec', value='Elec'),
                SelectOption(emoji='🌊', label='Hydro', value='Hydro'),
                SelectOption(emoji='💻', label='Info', value='Info'),
            ],
            row=1,
        )
        n7_major_select.callback = self._n7_major_select_cb

        Button = ui.Button[ProfileCreateOrChangeView]

        form_button = Button(label='Open Form', emoji='📔', row=0)
        form_button.callback = self._instantiate_form_modal

        photo_button = Button(label='Upload picture', emoji='🖼️', row=0)
        photo_button.callback = self._photo_button_cb

        confirm_button = Button(
            label='Confirm changes', emoji=self.bot.get_nana_emoji('FubukiGO'), row=2
        )
        confirm_button.callback = self._confirm_button_cb
        cancel_button = Button(
            label='Cancel changes', emoji=bot.get_nana_emoji('FubukiStop'), row=2
        )
        cancel_button.callback = self._cancel_button_cb
        self.add_item(form_button)
        self.add_item(photo_button)
        self.add_item(n7_major_select)
        self.add_item(confirm_button)
        self.add_item(cancel_button)

    async def _edit_embed(self, profile: UpsertProfileBody, interaction: Interaction):
        assert interaction.message
        embed = Profiles.create_embed(self.member, profile=profile)
        await interaction.message.edit(embed=embed)

    async def _photo_button_cb(self, interaction: Interaction):
        await interaction.response.send_message('Upload your profile picture', ephemeral=True)

        def check(message: MultiplexingContext):
            return all(
                [
                    message.command is None,
                    message.author == interaction.user,
                    message.channel == interaction.channel,
                ]
            )

        resp = await MultiplexingContext.set_will_delete(check=check)
        resp = resp.message
        if len(resp.attachments) > 0:
            attachment = resp.attachments[0]
            if attachment.content_type == 'image/png':
                hikari = await to_producer(attachment.url)
                self.profile.photo = hikari['url']
            else:
                await resp.reply('Not a valid PNG file!')
                return

        await resp.delete()
        await self._edit_embed(self.profile, interaction)

    async def _n7_major_select_cb(self, interaction: Interaction):
        await interaction.response.defer()
        assert interaction.data
        assert 'values' in interaction.data
        self.profile.n7_major = interaction.data['values'][0]
        await self._edit_embed(self.profile, interaction)

    async def _confirm_button_cb(self, interaction: Interaction):
        await interaction.response.defer()
        await Profiles._create_or_update_profile(self.member, self.profile)
        assert interaction.message
        await interaction.message.edit(
            content='Profile has been updated successfully.', embed=None, view=None
        )

    async def _cancel_button_cb(self, interaction: Interaction):
        assert interaction.message
        await interaction.message.edit(content='Profile update cancelled.', embed=None, view=None)

    async def _instantiate_form_modal(self, interaction: Interaction):
        modal = ProfileModal(title='Create/Update your Japan7 profile.', profile=self.profile)
        await interaction.response.send_modal(modal)

        if await modal.wait():
            return  # timeout

        self.profile = modal.profile
        await self._edit_embed(self.profile, interaction)

    @override
    async def interaction_check(self, interaction: Interaction):
        return self.member.id == interaction.user.id


@app_commands.context_menu(name='Who is')
async def user_who_is(interaction: Interaction, member: Member):
    resp = await get_nanapi().user.user_get_profile(member.id)
    match resp:
        case Success():
            pass
        case Error(code=404):
            await interaction.response.send_message(
                f'No informations found about **{member}**', ephemeral=True
            )
            return
        case _:
            raise RuntimeError(resp.result)

    profile = resp.result
    send = partial(interaction.response.send_message, ephemeral=True)
    await send(embed=Profiles.create_embed(member, profile))


def profile_upsert_body_from_search_result(
    member_user_name: str, search_result: ProfileSearchResult
):
    return UpsertProfileBody(
        discord_username=member_user_name,
        birthday=search_result.birthday,
        full_name=search_result.full_name,
        graduation_year=search_result.graduation_year,
        n7_major=search_result.n7_major,
        photo=search_result.photo,
        pronouns=search_result.pronouns,
        telephone=search_result.telephone,
    )


async def setup(bot: Bot):
    await bot.add_cog(Profiles(bot))
    bot.tree.add_command(user_who_is)
