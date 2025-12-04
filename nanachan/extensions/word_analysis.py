import discord
from discord import app_commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.nanapi.client import get_nanapi_client


class WordAnalysis(Cog):
    """Commands for word frequency analysis."""

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.nanapi = get_nanapi_client()

    @app_commands.command(name="word-frequency")
    @app_commands.describe(
        days="The number of past days to include in the analysis (default: 30).",
        top_n="The number of top words to display (default: 20, max: 25)."
    )
    async def word_frequency(self, interaction: discord.Interaction, days: int = 30, top_n: int = 20):
        """Analyze word frequency for the current server."""
        await interaction.response.defer(thinking=True)

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if not guild_id:
                await interaction.followup.send("❌ This command can only be used in a server.")
                return

            # Limit top_n to 25 due to Discord embed field limit
            top_n = min(top_n, 25)

            resp = await self.nanapi.discord.discord_get_word_frequency(
                guild_id=str(guild_id),
                days=days,
                top_n=top_n,
            )

            if not resp.code == 200:
                await interaction.followup.send(f"❌ Failed to analyze word frequency: {resp.result}")
                return

            analysis = resp.result

            embed = discord.Embed(
                title=f"📊 Top {len(analysis.top_words)} Most Frequent Words",
                description=(
                    f"Analyzed **{analysis.total_messages:,}** messages "
                    f"containing **{analysis.total_words:,}** words over the last **{days}** days.\n"
                    f"Unique vocabulary: **{analysis.unique_words:,}** words"
                ),
                color=discord.Color.blue()
            )

            # Limit to 25 fields to avoid Discord API error
            for word_data in analysis.top_words[:25]:
                embed.add_field(
                    name=f"🔹 {word_data['word']}",
                    value=(
                        f"**{word_data['count']:,}** occurrences • "
                        f"**{word_data['unique_users']}** users"
                    ),
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while analyzing word frequency: {e}")

    @app_commands.command(name="user-words")
    @app_commands.describe(
        user="The user to analyze.",
        days="The number of past days to include in the analysis (default: 30).",
        top_n="The number of signature words to display (default: 10, max: 25)."
    )
    async def user_words(self, interaction: discord.Interaction, user: discord.User, days: int = 30, top_n: int = 10):
        """Analyze the signature words of a specific user."""
        await interaction.response.defer(thinking=True)

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if not guild_id:
                await interaction.followup.send("❌ This command can only be used in a server.")
                return

            # Limit top_n to 25 due to Discord embed field limit
            top_n = min(top_n, 25)

            resp = await self.nanapi.discord.discord_get_user_characteristic_words(
                user_id=str(user.id),
                guild_id=str(guild_id),
                days=days,
                top_n=top_n,
            )

            if not resp.code == 200:
                await interaction.followup.send(f"❌ Failed to analyze user words: {resp.result}")
                return

            analysis = resp.result

            embed = discord.Embed(
                title=f"✨ Signature Words for {user.display_name}",
                description=(
                    f"Analyzed **{analysis.user_messages:,}** messages from this user "
                    f"over the last **{days}** days.\n"
                    f"Community messages: **{analysis.community_messages:,}**"
                ),
                color=discord.Color.green()
            )

            if analysis.characteristic_words:
                # Limit to 25 fields to avoid Discord API error
                for word_data in analysis.characteristic_words[:25]:
                    embed.add_field(
                        name=f"🔸 {word_data['word']}",
                        value=(
                            f"**{word_data['user_count']:,}** uses • "
                            f"**{word_data['ratio']:.1f}x** more than average"
                        ),
                        inline=False
                    )

                # Add summary stats
                summary = analysis.comparison_summary
                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"**Vocabulary Size:** {summary.get('user_vocabulary_size', 'N/A'):,}\n"
                        f"**Unique Words:** {summary.get('user_exclusive_words', 'N/A'):,}\n"
                        f"**Overlap:** {summary.get('vocabulary_overlap_percent', 'N/A')}%"
                    ),
                    inline=False
                )
            else:
                embed.description = f"No significant signature words found for {user.display_name} in the last {days} days."

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while analyzing user words: {e}")


async def setup(bot: Bot):
    await bot.add_cog(WordAnalysis(bot))
