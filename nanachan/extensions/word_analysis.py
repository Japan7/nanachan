import discord
from discord import app_commands
from discord.ext import commands

from nanachan.discord.cog import Cog
from nanachan.nanapi.client import get_nanapi_client
from nanachan.nanapi.model import WordFrequencyAnalysis, UserWordAnalysis


class WordAnalysis(Cog):
    """Commands for word frequency analysis."""

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.nanapi = get_nanapi_client()

    @app_commands.command(name="word-frequency")
    @app_commands.describe(
        days="The number of past days to include in the analysis (default: 30).",
        top_n="The number of top words to display (default: 20)."
    )
    async def word_frequency(self, interaction: discord.Interaction, days: int = 30, top_n: int = 20):
        """Analyze word frequency for the current server."""
        await interaction.response.defer()

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if not guild_id:
                await interaction.followup.send("This command can only be used in a server.")
                return

            analysis: WordFrequencyAnalysis = await self.nanapi.discord_get_word_frequency(
                guild_id=str(guild_id),
                top_n=top_n,
            )

            embed = discord.Embed(
                title=f"Top {len(analysis.top_words)} Most Frequent Words",
                description=f"Analyzed {analysis.total_messages} messages and {analysis.total_words} words.",
                color=discord.Color.blue()
            )

            for word_data in analysis.top_words:
                embed.add_field(
                    name=word_data['word'],
                    value=f"Count: {word_data['count']} | Users: {word_data['unique_users']}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="user-words")
    @app_commands.describe(
        user="The user to analyze.",
        top_n="The number of signature words to display (default: 10)."
    )
    async def user_words(self, interaction: discord.Interaction, user: discord.User, top_n: int = 10):
        """Analyze the signature words of a specific user."""
        await interaction.response.defer()

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if not guild_id:
                await interaction.followup.send("This command can only be used in a server.")
                return

            analysis: UserWordAnalysis = await self.nanapi.discord_get_user_characteristic_words(
                user_id=str(user.id),
                guild_id=str(guild_id),
                top_n=top_n,
            )

            embed = discord.Embed(
                title=f"Signature Words for {user.display_name}",
                description=f"Analyzed {analysis.user_messages} messages from this user.",
                color=discord.Color.green()
            )

            if analysis.characteristic_words:
                for word_data in analysis.characteristic_words:
                    embed.add_field(
                        name=word_data['word'],
                        value=f"Count: {word_data['user_count']} | Ratio: {word_data['ratio']:.2f}x",
                        inline=False
                    )
            else:
                embed.description = f"No significant signature words found for {user.display_name}."

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WordAnalysis(bot))