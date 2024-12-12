from __future__ import annotations

import asyncio
import base64
import io
import re
from datetime import datetime
from functools import partial
from operator import itemgetter
from typing import Optional, Protocol

import discord
from discord import Interaction, Member, SelectOption, app_commands, ui
from discord.ext.commands import (
    BadArgument,
    Context,
    MissingRequiredArgument,
    command,
    group,
    guild_only,
)
from discord.ui import Button

from nanachan.discord.application_commands import (
    LegacyCommandContext,
    legacy_command,
    nana_command,
)
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Embed, MultiplexingContext, typing
from nanachan.discord.views import AutoNavigatorView, BaseView, LockedView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    ProfileSearchResult,
    UpsertDiscordAccountBodyItem,
    UpsertProfileBody,
)
from nanachan.settings import YEAR_ROLES
from nanachan.utils.misc import list_display, to_producer


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
        self.registrars['Japan7 Profile'] = self._register

    async def _register(self, interaction: Interaction):
        assert interaction.guild
        member = interaction.guild.get_member(interaction.user.id)
        assert member
        profile = await self._get_profile(interaction.user.id)
        await interaction.response.send_message(
            view=ProfileCreateOrChangeView(self.bot, member, profile)
        )

    async def _year_role_member(self, ctx: Context, profile: ProfileSearchResult):
        guild = ctx.guild
        assert guild is not None

        if (
            profile.graduation_year is not None
            and 'ENSEEIHT' in profile.graduation_year
            and profile.graduation_year is not None
        ):
            graduation_year = int(profile.graduation_year)

            now = datetime.now()
            last_promotion = now.year if now.month >= 7 else now.year - 1

            member = guild.get_member(profile.user.discord_id)
            if member is None:
                return

            year_roles = [
                role for role in (guild.get_role(id) for id in YEAR_ROLES) if role is not None
            ]
            for i, role in enumerate(year_roles):
                if graduation_year <= last_promotion + i:
                    await member.remove_roles(*year_roles)
                    await member.add_roles(role)
                    return member, profile, role

    @command()
    @typing
    async def promo(self, ctx: Context):
        """Refresh promo roles"""
        guild = ctx.guild
        assert guild is not None

        resp = await get_nanapi().user.user_profile_search(
            ','.join(str(m.id) for m in guild.members)
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result

        refreshed = await asyncio.gather(
            *(self._year_role_member(ctx, profile) for profile in profiles)
        )

        text = [
            f'**{member}** • [**{role}**] {profile.full_name}'
            for member, profile, role in filter(None, refreshed)
        ]
        text.sort(key=str.casefold)

        icon_url = None if guild.icon is None else guild.icon.url
        await AutoNavigatorView.create(
            self.bot,
            ctx.reply,
            title='ENSEEIHT members',
            description='\n'.join(text),
            author_name=str(guild),
            author_icon_url=icon_url,
            footer_text=f'{len(text)} members',
        )

    # @nana_command(description='Display information about someone')
    # @legacy_command()
    # async def whois(self, ctx: LegacyCommandContext, user: discord.User):
    #     profile_resp = await get_nanapi().user.user_get_profile(user.id)
    #     if not success(profile_resp):
    #         raise RuntimeError(profile_resp.result)
    #     profile = profile_resp.result
    #     assert ctx.guild
    #     await ctx.send(
    #         embed=self._create_vcard(
    #         ctx.guild.get_member(user.id), profile
    #         )
    #     )

    async def _get_profile(self, discord_id: int):
        profile_resp = await get_nanapi().user.user_get_profile(discord_id)
        if not success(profile_resp):
            match profile_resp.code:
                case 404:
                    user = self.bot.get_user(discord_id)
                    assert user
                    await self._create_or_update_profile(
                        user, UpsertProfileBody(discord_username=user.name)
                    )
                    return await self._get_profile(discord_id=discord_id)
                case _:
                    raise RuntimeError(profile_resp.result)
        return profile_resp.result

    @staticmethod
    async def _create_or_update_profile(member: Member | discord.User, payload: UpsertProfileBody):
        resp = await get_nanapi().user.user_upsert_profile(member.id, payload)
        if not success(resp):
            raise RuntimeError(resp.result)
        profile = resp.result
        return profile

    @staticmethod
    def create_vcard(member: Optional[Member], profile: ProfileSearchResult):
        embed = Embed(colour=getattr(member, 'colour', None))
        embed = embed.add_field(name='氏名', value=profile.full_name)

        if member is not None:
            embed.set_author(name=member, icon_url=member.display_avatar.url)

        if profile.graduation_year:
            embed.add_field(name='学級', value=profile.graduation_year)

        if profile.telephone:
            embed.add_field(name='携帯番号', value=profile.telephone)

        # if profile.photo:
        #     embed.set_thumbnail(url=profile.photo)

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

    @nana_command()
    @legacy_command()
    async def iam(self, ctx: LegacyCommandContext):
        assert ctx.guild
        member = ctx.guild.get_member(ctx.author.id)
        profile = await self._get_profile(ctx.author.id)
        assert member
        await ctx.send(view=ProfileCreateOrChangeView(self.bot, member, profile))


class ProfileModal(ui.Modal):
    def __init__(self, *, title: str, profile: ProfileSearchResult):
        super().__init__(title=title)
        self.profile_dict = {
            'birthday': profile.birthday.date().strftime(r'%Y-%m-%d') if profile.birthday else '',
            'full_name': profile.full_name if profile.full_name else '',
            'graduation_year': re.findall(r'\d{4}', profile.graduation_year)[0]
            if profile.graduation_year
            else '',
            'pronouns': profile.pronouns if profile.pronouns else '',
            'telephone': profile.telephone if profile.telephone else '',
        }
        self.birthday = ui.TextInput(
            label='Birthdate',
            placeholder='Enter your birthdate (YYYY-MM-DD)',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile_dict['birthday'],
        )
        self.full_name = ui.TextInput(
            label='Full Name',
            placeholder='Enter you full name (First name Last name)',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile_dict['full_name'],
        )
        self.graduation_year = ui.TextInput(
            label='Graduation Year',
            placeholder='Enter your graduation year',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile_dict['graduation_year'],
        )
        self.pronouns = ui.TextInput(
            label='Pronouns',
            placeholder='Enter your prnouns',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile_dict['pronouns'],
        )
        self.telephone = ui.TextInput(
            label='Phone Number',
            placeholder='Enter your phone number',
            style=discord.TextStyle.short,
            required=False,
            default=self.profile_dict['telephone'],
        )

    async def on_submit(self, interaction: Interaction):
        errors = []
        if (
            self.birthday.value != ''
            and re.fullmatch(r'^\d{4}-\d{2}-\d{2}$', self.birthday.value) is None
        ):
            errors.append('Invalid birthday format.')
        if self.full_name.value != '':
            errors.append('Invalid full name format.')
        if (
            self.graduation_year.value != ''
            and re.fullmatch(r'^\d{4}$', self.graduation_year.value) is None
        ):
            errors.append('Invalid gradutaion year.')
        if (
            self.telephone.value != ''
            and re.fullmatch(r'^(\+33)|0\d{9}$', self.telephone.value) is None
        ):
            errors.append('Invalid phone number')
        response = (
            '\n'.join(errors) if len(errors) > 0 else 'All information gathered succesfully.'
        )

        await interaction.response.send_message(response, ephemeral=True)


class ProfileCreateOrChangeView(BaseView):
    def __init__(self, bot: Bot, member: Member, profile: ProfileSearchResult):
        super().__init__(bot)
        self.member = member
        self.profile = profile
        self.embed = Profiles.create_vcard(member, profile)
        n7_major_select = ui.Select(
            placeholder='Select your major at N7',
            options=[
                SelectOption(emoji='⚡', label='3EA', value='3EA'),
                SelectOption(emoji='🌊', label='MF2E', value='MF2E'),
                SelectOption(emoji='💻', label='SN', value='SN'),
            ],
            row=1,
        )
        n7_major_select.callback = self._n7_major_select_cb
        form_button = ui.Button(label='Open Form', emoji='📔', row=0)
        form_button.callback = partial(self._instantiate_form_modal, discord_id=member.id)
        photo_button = ui.Button(label='Upload picture', emoji='🖼️', row=0)
        photo_button.callback = self._photo_button_cb
        confirm_button = ui.Button(
            label='Confirm changes', emoji=self.bot.get_nana_emoji('FubukiGO')
        )
        cancel_button = ui.Button(label='Cancel changes', emoji=bot.get_nana_emoji('FubukiStop'))
        self.add_item(form_button)
        self.add_item(n7_major_select)

    def _edit_embed(self, profile: ProfileSearchResult):
        self.embed = Profiles.create_vcard(self.member, profile=profile)

    async def _photo_button_cb(self, interaction: Interaction):
        await interaction.response.send_message('Upload your profile picture', ephemeral=True)

        def check(message):
            return all(
                [
                    message.command is None,
                    message.author == interaction.user,
                    message.channel == interaction.channel,
                ]
            )

        resp = await MultiplexingContext.set_will_delete(check=check)
        resp = resp.message
        profile_picture = None
        if len(resp.attachments) > 0:
            attachment = resp.attachments[0]
            if attachment.content_type == 'image/png':
                profile_picture = await attachment.read()
                hikari = await to_producer(
                    profile_picture, filename=f'profile_{interaction.user.id}.jpg'
                )
                self.profile.photo = hikari['url']
            else:
                await resp.reply('Not a valid PNG file!')

        await resp.delete()

    async def _n7_major_select_cb(self, interaction: Interaction):
        assert interaction.data
        assert 'values' in interaction.data
        self.profile.n7_major = interaction.data['values'][0]

    async def _instantiate_form_modal(self, interaction: Interaction, discord_id: int):
        modal = ProfileModal(title='Create/Update your Japan7 profile.', profile=self.profile)
        await interaction.response.send_modal(modal)
        await modal.wait()
        self._update_profile_from_dict(self.profile, modal.profile_dict)

    @staticmethod
    def _update_profile_from_dict(profile: ProfileSearchResult, profile_dict: dict[str, str]):
        for key, val in profile_dict.items():
            if hasattr(profile, key):
                setattr(profile, key, val)


@app_commands.context_menu(name='Who is')
async def user_who_is(interaction: Interaction, member: Member):
    resp = await get_nanapi().user.user_get_profile(member.id)
    if not success(resp):
        match resp.code:
            case 404:
                await interaction.response.send_message(
                    f'No informations found about **{member}**', ephemeral=True
                )
                return
            case _:
                raise RuntimeError(resp.result)
    profile = resp.result
    send = partial(interaction.response.send_message, ephemeral=True)
    await send(embed=Profiles.create_vcard(member, profile))


async def setup(bot: Bot):
    await bot.add_cog(Profiles(bot))
    bot.tree.add_command(user_who_is)
