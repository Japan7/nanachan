from discord import Interaction, Member, app_commands

from nanachan.discord.application_commands import nana_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import Embed
from nanachan.discord.views import NavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import WrappedEmbed


class Wrapped(Cog):
    YEAR = 2025

    def __init__(self, bot: Bot):
        super().__init__(bot)

    @nana_command(description='Your year in review!')
    @app_commands.guild_only()
    async def wrapped(self, interaction: Interaction, member: Member | None = None):
        """Display your yearly wrapped statistics with fun comparisons."""
        await interaction.response.defer()

        discord_id = member.id if member else interaction.user.id
        resp = await get_nanapi().wrapped.wrapped_get_wrapped(
            discord_id=str(discord_id),
            year=self.YEAR,
        )

        if not success(resp):
            await interaction.followup.send(
                f'Could not fetch your wrapped data {self.bot.get_emoji_str("saladedefruits")}'
            )
            return

        wrapped_data = resp.result

        if not wrapped_data.embeds:
            sad = self.bot.get_emoji_str('saladedefruits')
            await interaction.followup.send(
                f'No data found for {self.YEAR}. Were you even here? {sad}'
            )
            return

        # Convert API embeds to Discord embeds
        pages = [{'embed': self._convert_embed(e)} for e in wrapped_data.embeds]

        # Use NavigatorView for pagination
        mention = member.mention if member else interaction.user.mention
        await NavigatorView.create(
            self.bot,
            interaction.followup.send,
            pages=pages,
            static_content=f"✨ **{mention}'s {self.YEAR} Wrapped** ✨",
        )

    def _convert_embed(self, wrapped_embed: WrappedEmbed) -> Embed:
        """Convert a WrappedEmbed from the API to a Discord Embed."""
        # Resolve custom emojis in title and description
        title = wrapped_embed.title
        if title:
            title = self.bot.get_emojied_str(title)

        description = wrapped_embed.description
        if description:
            description = self.bot.get_emojied_str(description)

        embed = Embed(
            title=title,
            description=description,
            colour=wrapped_embed.color,
        )

        # Add fields if present
        if wrapped_embed.fields:
            for field in wrapped_embed.fields:
                embed.add_field(
                    name=self.bot.get_emojied_str(field.name),
                    value=self.bot.get_emojied_str(field.value),
                    inline=field.inline if field.inline is not None else True,
                )

        # Set footer if present
        if wrapped_embed.footer:
            embed.set_footer(text=self.bot.get_emojied_str(wrapped_embed.footer))

        # Set image if present
        if wrapped_embed.image_url:
            embed.set_image(url=wrapped_embed.image_url)

        return embed


async def setup(bot: Bot):
    await bot.add_cog(Wrapped(bot))
