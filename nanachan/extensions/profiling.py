import tempfile

import yappi
from discord import File, Interaction, app_commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog


class Profiling(NanaGroupCog, group_name="debug"):

    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(description="start profiler")
    async def start_profiling(self, interaction: Interaction):
        yappi.clear_stats()
        yappi.start()
        await interaction.response.send_message(self.bot.get_emoji_str("FubukiGO"))

    @app_commands.command(description="Upload the profiling data")
    async def stop_profiling(self, interaction: Interaction):
        yappi.stop()
        stats = yappi.get_func_stats()
        await interaction.response.defer()
        with tempfile.NamedTemporaryFile("w+b") as f:
            stats.save(f.name, type="pstat")
            await interaction.followup.send(file=File(f.name, filename="profile"))


async def setup(bot: Bot):
    await bot.add_cog(Profiling(bot))
