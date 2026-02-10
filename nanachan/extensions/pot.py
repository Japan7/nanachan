from decimal import ROUND_DOWN, Decimal, InvalidOperation

from discord import Embed, Interaction, Member, app_commands

from nanachan.discord.application_commands import nana_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.nanapi._client import Error, Success
from nanachan.nanapi.client import get_nanapi
from nanachan.nanapi.model import CollectPotBody, PotAddResult, PotGetByUserResult


class Pot(Cog):
    """Collect (virtual) money for someone (may or may not imply any future payment)"""

    emoji = '💸'

    @nana_command(description='Collect some money for the poor')
    @app_commands.rename(amount_str='amount')
    @app_commands.guild_only()
    async def collect(
        self, interaction: Interaction, member: Member, amount_str: str | None = None
    ):
        if amount_str is None:
            amount = Decimal('1')
        else:
            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                await interaction.response.send_message(f'invalid amount: {amount_str}')
                return

        if amount <= 0:
            await interaction.response.send_message('The amount must be positive')
            return

        if interaction.user.id == member.id:
            await interaction.response.send_message('It would be too easy...')
            return

        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        await interaction.response.defer()

        resp = await get_nanapi().pot.pot_collect_pot(
            str(member.id), CollectPotBody(discord_username=str(member), amount=float(amount))
        )
        match resp:
            case Error():
                resp.raise_exc()
            case Success():
                pass

        funding = resp.result

        await self._send_pot(interaction, member, funding)

    @nana_command(description='Show someone’s collected amount of money')
    async def pot(self, interaction: Interaction, member: Member):
        await interaction.response.defer()
        resp = await get_nanapi().pot.pot_get_pot(str(member.id))

        match resp:
            case Success():
                pass
            case Error(404):
                await interaction.response.send_message(
                    f'No one has ever collected for {member} :cry:'
                )
                return
            case Error():
                resp.raise_exc()

        funding = resp.result
        await self._send_pot(interaction, member, funding)

    @staticmethod
    async def _send_pot(
        interaction: Interaction, member: Member, funding: PotAddResult | PotGetByUserResult
    ) -> None:
        average = funding.amount / funding.count

        embed = (
            Embed(color=member.color)
            .set_author(name=f'{member}’s pot', icon_url=member.display_avatar.url)
            .add_field(name='Total', value=f'{funding.amount} €')
            .add_field(name='Count', value=funding.count)
            .add_field(name='Average', value=f'{average:.2f} €')
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Pot(bot))
