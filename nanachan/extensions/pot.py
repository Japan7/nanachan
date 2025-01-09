from decimal import ROUND_DOWN, Decimal

from discord import Embed, Member
from discord.ext.commands import CommandError, Context, command, guild_only

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import CollectPotBody, PotAddResult, PotGetByUserResult


class Pot(Cog):
    """Collect (virtual) money for someone (may or may not imply any future payment)"""

    emoji = '💸'

    @guild_only()
    @command(help='Collect some money for the poor')
    async def collect(self, ctx: Context, member: Member, amount: Decimal | None = None):
        if amount is None:
            amount = Decimal('1')

        if amount <= 0:
            raise CommandError('The amount must be positive')

        if ctx.author.id == member.id:
            raise CommandError('It would be too easy...')

        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        resp = await get_nanapi().pot.pot_collect_pot(
            member.id, CollectPotBody(discord_username=str(member), amount=float(amount))
        )
        if not success(resp):
            raise RuntimeError(resp.result)
        funding = resp.result

        await self._send_pot(ctx, member, funding)

    @command(help='Show someone’s collected amount')
    async def pot(self, ctx, member: Member):
        resp = await get_nanapi().pot.pot_get_pot(member.id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise CommandError(f'No one has ever collected for {member} :cry:')
                case _:
                    raise RuntimeError(resp.result)
        funding = resp.result
        await self._send_pot(ctx, member, funding)

    @staticmethod
    async def _send_pot(ctx, member: Member, funding: PotAddResult | PotGetByUserResult) -> None:
        average = funding.amount / funding.count

        embed = (
            Embed(color=member.color)
            .set_author(name=f'{member}’s pot', icon_url=member.display_avatar.url)
            .add_field(name='Total', value=f'{funding.amount} €')
            .add_field(name='Count', value=funding.count)
            .add_field(name='Average', value=f'{average:.2f} €')
        )

        await ctx.send(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Pot(bot))
