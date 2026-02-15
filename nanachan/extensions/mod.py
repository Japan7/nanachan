from discord import Interaction, Permissions, User, app_commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.nanapi._client import UpsertUser
from nanachan.nanapi.client import get_nanapi


@app_commands.default_permissions(Permissions(administrator=True))
@app_commands.guild_only()
class ModCommands(NanaGroupCog, group_name='mod'):
    """Moderator commands"""

    @app_commands.command(description='Verify age of Discord users')
    async def kid(self, interaction: Interaction[Bot], member: User, is_kid: bool = True):
        await interaction.response.defer()

        body = UpsertUser(
            discord_id=str(member.id),
            discord_username=str(member),
            age_verified=not is_kid,
        )
        resp = await get_nanapi().user.user_upsert_user(body=body)
        resp = resp.raise_exc()

        fubukigo = interaction.client.get_emoji_str('FubukiGO')
        if is_kid:
            await interaction.followup.send(
                f'{member.mention} is a kid now {fubukigo}\n'
                'To appeal this decision, touch grass (with picture or didn’t happen)'
            )
        else:
            await interaction.followup.send(
                f'{member.mention} is not a kid anymore. good job {fubukigo}\n'
            )


async def setup(bot: Bot):
    await bot.add_cog(ModCommands(bot))
