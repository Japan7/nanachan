import asyncio
import logging
import re
from random import Random
from typing import Optional, cast

from discord import Member
from discord.ext.commands import CommandError, command, has_permissions

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import MultiplexingContext
from nanachan.extensions.waicolle import WaifuCollection
from nanachan.redis.wasabi import wasabi_count
from nanachan.settings import DEBUG, WASABI_FREQUENCY, WASABI_RANGE

log = logging.getLogger(__name__)

random = Random()

perdu_reg = re.compile(r'\bperd', re.IGNORECASE)
creeper_reg = re.compile(r'\bcreeper', re.IGNORECASE)


class Keywords(Cog):
    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if ctx.author.bot:
            return

        if perdu_reg.search(ctx.message.content):
            await ctx.send('負けました... :no_mouth:')
        elif creeper_reg.search(ctx.message.content):
            await ctx.send('AWW MAN')


class Wasabi(Cog):
    wasabi_emoji_name = 'wasabi'

    def __init__(self, bot):
        super().__init__(bot)
        self.wasabi_lock = asyncio.Lock()

    async def get_wasabi_count(self) -> int:
        count = await wasabi_count.get()
        if count is None:
            count = await self.reset_counter()
        await wasabi_count.set(count - 1)
        return count

    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if ctx.author.bot:
            return

        if ctx.guild is None:
            return

        if ctx.will_delete:
            return

        async with self.wasabi_lock:
            count = await self.get_wasabi_count()
            await wasabi_count.set(count - 1)

            if await self.is_wasabi(ctx.message):
                await self.reset_counter()
                await self.send_wasabi(ctx.message)

                waifu_cog = self.bot.get_cog(WaifuCollection.__cog_name__)
                if waifu_cog is not None:
                    waifu_cog = cast(WaifuCollection, waifu_cog)
                    await waifu_cog.reward_drop(ctx.message.author, random.randint(0, 1), 'Wasabi')

    async def is_wasabi(self, message):
        count = await self.get_wasabi_count()
        return (
            any(pattern in message.content.lower() for pattern in ['frott', 'frtt'])
            and count <= WASABI_RANGE
            or count <= 0
        )

    async def send_wasabi(self, message):
        emoji = self.bot.get_nana_emoji(Wasabi.wasabi_emoji_name)
        if emoji:
            await message.add_reaction(emoji)
        else:
            log.warning(
                f'The custom emoji "{Wasabi.wasabi_emoji_name}"'
                f' is not present on server "{message.guild.name}"'
            )
        await message.channel.send('C’est comme le Wasabi !')

    @staticmethod
    async def reset_counter() -> int:
        count = random.randint(WASABI_FREQUENCY, WASABI_FREQUENCY + WASABI_RANGE)
        await wasabi_count.set(count)
        return count


class Ignored(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.ignored_member_ids = {}  # {member_id: unignore_timer}

        # Monkey patch bot.dispatch
        self.bot_dispatch = bot.dispatch
        bot.dispatch = self._dispatch
        # this little guy use copy instead of reference, so we need to copy the new one again
        bot._connection.dispatch = self._dispatch  # pyright: ignore[reportPrivateUsage]

    @has_permissions(administrator=True)
    @command(hidden=True, help='A tyrant command\nIgnore this member for 5 minutes (by default)')
    async def ignore(self, ctx, anas: Member | None = None, period: int = 5):
        if anas is None:
            anas = self.bot.get_anas(ctx.guild)
            assert anas is not None

        if anas.id in self.ignored_member_ids:
            await ctx.send(f'{anas.mention} is already ignored')
            return

        if not DEBUG:
            if anas == ctx.author:
                raise CommandError('Are you a masochist?')

            if anas.guild_permissions.administrator:
                raise CommandError('I cannot ignore ~~a tyrant~~ an admin')

        if anas.bot:
            raise CommandError('I am already ignoring bots')

        if period > 60 * 24:
            raise CommandError('Ignoring for more than one day is harsh')

        timer = self.bot.loop.call_later(period * 60, self._unignore, anas)
        self.ignored_member_ids[anas.id] = timer

        await ctx.send(':ok_hand:')

    @has_permissions(administrator=True)
    @command(hidden=True, help='A tyrant command\nUnignore an ignored member')
    async def unignore(self, ctx, anas: Member | None = None):
        if anas is None:
            anas = self.bot.get_anas(ctx.guild)
            assert anas is not None

        if anas.id in self.ignored_member_ids:
            self.ignored_member_ids[anas.id].cancel()
            self._unignore(anas)
            await ctx.send(':ok_hand:')
        else:
            await ctx.send(f'{anas.mention} is not ignored')

    def _unignore(self, anas: Member):
        del self.ignored_member_ids[anas.id]

    def _dispatch(self, event_name, *args, **kwargs):
        if event_name == 'message':
            if args[0].author.id in self.ignored_member_ids:
                return
        elif event_name == 'raw_reaction_add':
            if args[0].user_id in self.ignored_member_ids:
                return
        elif event_name == 'reaction_add' and args[1].id in self.ignored_member_ids:
            return

        self.bot_dispatch(event_name, *args, **kwargs)


class Bananas(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bananased_member_ids = {}  # {member_id: timer}

    async def bananas_perm(self, ctx, anas: Member, period: int):
        if anas.id in self.bananased_member_ids:
            raise CommandError(f'{anas.mention} is already :banana:')

        if anas == ctx.author:
            return True

        if not ctx.author.guild_permissions.administrator:
            raise CommandError('You cannot do that as a pleb')

        if not DEBUG and anas.guild_permissions.administrator:
            raise CommandError('I cannot :banana: ~~a tyrant~~ an admin')

        if anas.bot:
            raise CommandError('I cannot :banana: my bot friends')

        return True

    @command(hidden=True, help='A tyrant command\nBananas for 5 minutes (by default)')
    async def bananas(self, ctx, anas: Optional[Member] = None, period: int = 5):
        if anas is None:
            anas = self.bot.get_anas(ctx.guild)
            assert anas is not None

        if await self.bananas_perm(ctx, anas, period):
            timer = self.bot.loop.call_later(period * 60, self._unbananas, anas)
            self.bananased_member_ids[anas.id] = timer

            await ctx.send(':ok_hand:')

    @has_permissions(administrator=True)
    @command(hidden=True, help='A tyrant command\nUnbananas')
    async def unbananas(self, ctx, anas: Member | None = None):
        if anas is None:
            anas = self.bot.get_anas(ctx.guild)
            assert anas is not None

        if anas.id in self.bananased_member_ids:
            self.bananased_member_ids[anas.id].cancel()
            self._unbananas(anas)
            await ctx.send(':ok_hand:')
        else:
            await ctx.send(f'{anas.mention} is not :banana:')

    def _unbananas(self, anas: Member):
        del self.bananased_member_ids[anas.id]

    def _bananas(self, message: str):
        new_message = ':banana:'

        i = 1
        while i < len(message):
            j = random.randint(3, 5)
            new_message += message[i : i + j] + ':banana:'
            i += j + 1

        return new_message


async def setup(bot: Bot) -> None:
    await bot.add_cog(Keywords(bot))
    await bot.add_cog(Ignored(bot))
    await bot.add_cog(Bananas(bot))
    await bot.add_cog(Wasabi(bot))
