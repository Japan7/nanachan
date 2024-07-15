from __future__ import annotations

import asyncio
import base64
import io
import re
from datetime import datetime
from functools import partial
from operator import itemgetter
from typing import Optional, Protocol

import vobject
from discord import Interaction, Member, app_commands
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
from nanachan.discord.views import AutoNavigatorView, LockedView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import (
    ProfileSearchResult,
    UpsertDiscordAccountBodyItem,
    UpsertProfileBody,
)
from nanachan.settings import YEAR_ROLES
from nanachan.utils.misc import list_display, to_producer


class RegistrarProtocol(Protocol):

    async def __call__(self, interaction: Interaction):
        ...


class Profiles(Cog):
    """ QUOI ?! IL S'APPELLE BOULMECK ?! """
    emoji = '💳'

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.registrars: dict[str, RegistrarProtocol] = {}

    @Cog.listener()
    async def on_ready(self):
        all_members = {member for guild in self.bot.guilds for member in guild.members}
        await get_nanapi().user.user_upsert_discord_accounts(
            [UpsertDiscordAccountBodyItem(discord_id=member.id, discord_username=str(member))
             for member in all_members]
        )

    @command(aliases=['iam'],
             help='Tell who you are\n'
                  'You need to attach your .vcf card while using this command')
    async def i_am(self, ctx):
        vcard = await self._fetch_vcard(ctx.message)
        profile = await self._create_or_update_profile(ctx.author, vcard)
        await self._year_role_member(ctx, profile)
        await self._send_vcard(ctx.send, ctx.author, profile)

    @guild_only()
    @command(aliases=['thisis'],
             help='Tell who this member is\n'
                  'You need to attach the member’s .vcf card while using this command')
    async def this_is(self, ctx, member: Member):
        vcard = await self._fetch_vcard(ctx.message)
        profile = await self._create_or_update_profile(member, vcard)
        await self._year_role_member(ctx, profile)
        await self._send_vcard(ctx.send, member, profile)

    @this_is.error
    async def thisis_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send('SPARTAAAA!!')
        else:
            await self.bot.on_command_error(ctx, error, force=True)

    async def _year_role_member(self, ctx: Context,
                                profile: ProfileSearchResult):
        guild = ctx.guild
        assert guild is not None

        if (profile.promotion is not None and 'ENSEEIHT' in profile.promotion
                and (year_search := re.search(r'\d+', profile.promotion))):
            promotion = int(year_search.group(0))

            now = datetime.now()
            last_promotion = now.year if now.month >= 7 else now.year - 1

            member = guild.get_member(profile.user.discord_id)
            if member is None:
                return

            year_roles = [role for role in (guild.get_role(id) for id in YEAR_ROLES)
                          if role is not None]
            for i, role in enumerate(year_roles):
                if promotion <= last_promotion + i:
                    await member.remove_roles(*year_roles)
                    await member.add_roles(role)
                    return member, profile, role

    @command()
    @typing
    async def promo(self, ctx: Context):
        """Refresh promo roles"""
        guild = ctx.guild
        assert guild is not None

        resp = await get_nanapi().user.user_profile_search(','.join(
            str(m.id) for m in guild.members
        ))
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result

        refreshed = await asyncio.gather(*(
            self._year_role_member(ctx, profile) for profile in profiles
        ))

        text = [
            f"**{member}** • [**{role}**] {profile.full_name}"
            for member, profile, role in filter(None, refreshed)
        ]
        text.sort(key=str.casefold)

        icon_url = None if guild.icon is None else guild.icon.url
        await AutoNavigatorView.create(self.bot,
                                       ctx.reply,
                                       title='ENSEEIHT members',
                                       description='\n'.join(text),
                                       author_name=str(guild),
                                       author_icon_url=icon_url,
                                       footer_text=f"{len(text)} members")

    @command(aliases=['whois'],
             help='Display information about someone')
    async def who_is(self, ctx: MultiplexingContext, *, search_tags):
        members_and_profiles: dict[int, tuple[Member, ProfileSearchResult]] = {}

        if (guild := ctx.guild) is None:
            guild = self.bot.get_bot_room().guild

        # search in the discord names
        for member in guild.members:
            magic_string = '\0'.join({
                member.name, member.nick or member.name,
                str(member.id), member.mention,
                f'{member.name}#{member.discriminator}'
            })
            if re.search(re.escape(search_tags), magic_string, re.IGNORECASE):
                resp = await get_nanapi().user.user_get_profile(member.id)
                if not success(resp):
                    match resp.code:
                        case 404:
                            continue
                        case _:
                            raise RuntimeError(resp.result)
                profile = resp.result
                members_and_profiles[member.id] = (member, profile)

        # search in the cards information
        search = f'%{search_tags}%'
        resp = await get_nanapi().user.user_profile_search(pattern=search)
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result

        for profile in profiles:
            member = guild.get_member(profile.user.discord_id)
            if member is None:
                continue

            members_and_profiles[member.id] = (member, profile)

        # display all what we found
        if len(members_and_profiles) > 0:
            for member, profile in members_and_profiles.values():
                await self._send_vcard(ctx.send, member, profile)
        else:
            await ctx.send('分かりません :confounded:')

    @guild_only()
    @group(aliases=['profiles'], invoke_without_command=True,
           help='List & manage profiles')
    async def profile(self, ctx):
        subcommand = ctx.subcommand_passed
        if subcommand is not None:
            raise BadArgument(f'Invalid profile command `{subcommand}`')
        else:
            raise BadArgument('Subcommand needed')

    @guild_only()
    @profile.command(help='List known members (this can be a long list)')
    async def list(self, ctx):
        resp = await get_nanapi().user.user_profile_search(','.join(
            [str(m.id) for m in ctx.guild.members]))
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result
        if profiles:
            members = []
            width = 0
            for profile in profiles:
                member = ctx.guild.get_member(profile.user.discord_id)
                members.append((str(member), profile.full_name))
                width = max(width, len(str(member)))
            members = [f'{m[0].ljust(width)} : {m[1]}' for m in members]
            for page in list_display('Member list', members):
                await ctx.send(page)
        else:
            await ctx.send('```No member registered on this server```')

    @guild_only()
    @profile.command(help='List unknown members (this can be a long list)')
    async def check(self, ctx):
        resp = await get_nanapi().user.user_profile_search(','.join(
            [str(m.id) for m in ctx.guild.members]))
        if not success(resp):
            raise RuntimeError(resp.result)
        profiles = resp.result
        discord_ids = [p.user.discord_id for p in profiles]

        unknown_members = sorted((str(member) for member in ctx.guild.members
                                  if member.id not in discord_ids and not member.bot),
                                 key=str.lower)

        discords_ids_without_pp = [
            p.user.discord_id for p in profiles if p.photo is None
        ]

        members_without_pp = sorted((str(member) for member in ctx.guild.members
                                     if member.id in discords_ids_without_pp and not member.bot))

        message = False
        if unknown_members:
            message = True
            for page in list_display('Unknown members', unknown_members):
                await ctx.send(page)
        if members_without_pp:
            message = True
            for page in list_display('Members without profile picture', members_without_pp):
                await ctx.send(page)
        if not message:
            await ctx.send('```All this server\'s members are known and have a profile picture```')

    @staticmethod
    async def _fetch_vcard(message):
        for attachment in message.attachments:
            if attachment.filename.endswith('.vcf'):
                break
        else:
            raise BadArgument('`.vcf` file not found')

        return vobject.readOne((await attachment.read()).decode())  # type: ignore |not exported ig

    @staticmethod
    async def _create_or_update_profile(member: Member, vcard):
        full_name = vcard.fn.value
        promotion = re.sub('&amp,', '&', Profiles._flatten(vcard.org.value))
        telephone = vcard.tel.value if 'tel' in vcard.contents else ''
        photo = base64.b64encode(vcard.photo.value).decode('ascii') if len(
            vcard.photo.value) > 5 else ''

        resp = await get_nanapi().user.user_upsert_profile(
            member.id,
            UpsertProfileBody(discord_username=str(member),
                              full_name=full_name,
                              promotion=promotion,
                              telephone=telephone,
                              photo=photo))
        if not success(resp):
            raise RuntimeError(resp.result)
        profile = resp.result
        return profile

    @staticmethod
    def _flatten(l):
        if isinstance(l, list):
            result = Profiles._flatten(l[0])
            if len(l) > 1:
                for element in l[1:]:
                    result += ',' + Profiles._flatten(element)
            return result
        else:
            return l

    @staticmethod
    async def _send_vcard(send_func, member: Optional[Member], profile):
        embed = Embed(colour=getattr(member, 'colour', None))
        embed = embed.add_field(name='氏名', value=profile.full_name)

        if member is not None:
            embed.set_author(name=member,
                             icon_url=member.display_avatar.url)

        if profile.promotion:
            embed.add_field(name='学級', value=profile.promotion)

        if profile.telephone:
            embed.add_field(name='携帯番号', value=profile.telephone)

        if profile.photo:
            image = io.BytesIO(base64.b64decode(profile.photo))
            hikari = await to_producer(image, filename='profile.jpg')
            embed.set_thumbnail(url=hikari['url'])

        await send_func(embed=embed)

    @nana_command()
    @legacy_command()
    async def register(self, ctx: LegacyCommandContext):
        """ Register yourself into Nana-chan """
        registrars = sorted(self.registrars.items(), key=itemgetter(0))

        desc = []
        view = LockedView(self.bot, ctx.author)
        for name, callback in registrars:
            emoji = callback.__self__.__class__.emoji  # type: ignore
            desc.append(f"{emoji} **{name}**\n{callback.__doc__}")
            button = Button(label=name, emoji=emoji)
            button.callback = callback
            view.add_item(button)

        embed = Embed(title=f"{self.emoji} Register",
                      description='\n\n'.join(desc))
        embed.set_author(name=ctx.author,
                         icon_url=ctx.author.display_avatar.url)
        await ctx.reply(
            content=f"React with the {self.bot.get_emoji_str('chousen')} option",
            embed=embed,
            view=view)


@app_commands.context_menu(name='Who is')
async def user_who_is(interaction: Interaction, member: Member):
    resp = await get_nanapi().user.user_get_profile(member.id)
    if not success(resp):
        match resp.code:
            case 404:
                await interaction.response.send_message(
                    f"No informations found about **{member}**", ephemeral=True)
                return
            case _:
                raise RuntimeError(resp.result)
    profile = resp.result
    send = partial(interaction.response.send_message, ephemeral=True)
    await Profiles._send_vcard(send, member, profile)


async def setup(bot: Bot):
    await bot.add_cog(Profiles(bot))
    bot.tree.add_command(user_who_is)
