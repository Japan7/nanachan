import tempfile
import tracemalloc

import yappi
from discord import File, Interaction, app_commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog


class Profiling(NanaGroupCog, group_name='debug'):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot
        self.tracemalloc_snap1 = None

    @app_commands.command(description='start profiler')
    async def start_profiling(self, interaction: Interaction):
        yappi.clear_stats()
        yappi.start()
        await interaction.response.send_message(self.bot.get_emoji_str('FubukiGO'))

    @app_commands.command(description='Upload the profiling data')
    async def stop_profiling(self, interaction: Interaction):
        yappi.stop()
        stats = yappi.get_func_stats()
        await interaction.response.defer()

        with tempfile.NamedTemporaryFile('w+b') as f:
            stats.save(f.name, type='pstat')
            await interaction.followup.send(file=File(f.name, filename='profile'))

    @app_commands.command(description='start tracemalloc')
    async def start_tracemalloc(self, interaction: Interaction):
        tracemalloc.start()
        self.tracemalloc_snap1 = tracemalloc.take_snapshot()
        await interaction.response.send_message(self.bot.get_emoji_str('FubukiGO'))

    @app_commands.command(description='stop tracemalloc')
    async def stop_tracemalloc(self, interaction: Interaction):
        if self.tracemalloc_snap1 is None:
            await interaction.response.send_message('tracemalloc was not started')
            return

        await interaction.response.defer()

        snapshot = tracemalloc.take_snapshot()
        compare = snapshot.compare_to(self.tracemalloc_snap1, 'lineno')
        with tempfile.NamedTemporaryFile('w+') as f:
            f.writelines(f'{l}\n' for l in compare)
            f.flush()
            await interaction.followup.send(file=File(f.name, filename='tracemalloc'))

        tracemalloc.stop()
        self.tracemalloc_snap1 = None


async def setup(bot: Bot):
    await bot.add_cog(Profiling(bot))
