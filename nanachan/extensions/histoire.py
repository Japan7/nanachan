import re
from random import choice
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from uuid import UUID

from discord import Message
from discord.ext import commands

from nanachan.discord.bot import Bot
from nanachan.discord.cog import Cog
from nanachan.discord.helpers import MultiplexingContext, UserType
from nanachan.discord.views import AutoNavigatorView
from nanachan.nanapi.client import get_nanapi, success
from nanachan.nanapi.model import NewHistoireBody

if TYPE_CHECKING:
    from discord.abc import MessageableChannel


class StoryBuilder:
    def __init__(self, title: str) -> None:
        self._title: str = self.format_title(title)
        self._parts: List[str] = []

    def set_title(self, title: str):
        self._title = self.format_title(title)

    @staticmethod
    def format_title(title: str) -> str:
        return re.sub(r'\s+', ' ', title).capitalize()

    def store(self, text: str) -> int:
        self._parts.append(text)

        return self.get_parts_len()

    def undo(self) -> int:
        if len(self._parts) > 0:
            self._parts.pop()

        return self.get_parts_len()

    def get_parts_len(self) -> int:
        return len(self._parts)

    def to_story(self) -> dict:
        text = '\n'.join(self._parts)
        return dict(title=self._title, text=text)


class Histoire(Cog):
    """Tell your story or that of the greatest heroes of our times"""

    emoji = '👴'

    thumbsup = '\N{THUMBS UP SIGN}'
    ok_hand = '\N{OK HAND SIGN}'

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.story_builders_by_channel_user: Dict[Tuple[int, int], StoryBuilder] = {}

    @Cog.listener()
    async def on_user_message(self, ctx: MultiplexingContext) -> None:
        message = ctx.message
        channel: 'MessageableChannel' = message.channel
        user: UserType = message.author
        builder = self.story_builders_by_channel_user.get((channel.id, user.id))
        conditions = [builder is not None, ctx.command is None]
        if builder is not None and all(conditions):
            parts_count = builder.store(message.content)
            await ctx.send(f'{parts_count} parts cached')

    @commands.group(
        invoke_without_command=True, recursive_help=False, help='Tell you a story (in french)'
    )
    async def histoire(self, ctx: commands.Context, story_id: Optional[str]) -> None:
        _story_id = None
        # Check if story_id is subcommand or real parameter
        if story_id:
            try:
                _story_id = UUID(story_id)
            except ValueError:
                raise commands.BadArgument(f'Invalid subcommand `{story_id}`')

        # Check if database contains at least one story
        resp = await get_nanapi().histoire.histoire_histoire_index()
        if not success(resp):
            raise RuntimeError(resp.result)
        stories = resp.result
        story_ids = [story.id for story in stories]
        if len(story_ids) == 0:
            raise commands.CommandError('No story has been added yet')

        # Select a random story if id not specified
        if not _story_id:
            _story_id = choice(story_ids)

        # Fetch the story
        resp = await get_nanapi().histoire.histoire_get_histoire(_story_id)
        if not success(resp):
            match resp.code:
                case 404:
                    raise commands.CommandError(f'Story with id {_story_id} does not exist')
                case _:
                    raise RuntimeError(resp.result)
        story = resp.result

        await AutoNavigatorView.create(
            self.bot, ctx.reply, title=story.title, description=story.text
        )

    @histoire.command(help='Start the creation of a story')
    async def start(self, ctx: commands.Context, *, title: str) -> None:
        # Ensure title is one line
        if '\n' in title:
            raise commands.BadArgument('Story title must be contained in one line')

        # Check a story is not already recording
        channel: 'MessageableChannel' = ctx.channel
        user = ctx.author
        if (channel, user) in self.story_builders_by_channel_user:
            raise commands.CommandError('A story is already being recorded in this channel')

        # Start the recording
        self.story_builders_by_channel_user[(channel.id, user.id)] = StoryBuilder(title)

        # Tells the user everything is ok
        message: Message = ctx.message
        await message.add_reaction(self.thumbsup)

    @histoire.command(help='Remove the last added block of text')
    async def undo(self, ctx: commands.Context) -> None:
        # Check a story is recording
        channel: 'MessageableChannel' = ctx.channel
        user: UserType = ctx.author
        builder = self.story_builders_by_channel_user.get((channel.id, user.id))
        if builder is None:
            raise commands.CommandError('Nothing to save')

        # Remove last part
        parts_count = builder.undo()

        # Tells the user everything is ok
        await ctx.send(f'{parts_count} parts cached')

    @histoire.command(help='End the story and save it in database')
    async def save(self, ctx: commands.Context, title: Optional[str]) -> None:
        # Check a story is recording
        channel: 'MessageableChannel' = ctx.channel
        user: UserType = ctx.author
        builder = self.story_builders_by_channel_user.get((channel.id, user.id))
        if builder is None:
            raise commands.CommandError('Nothing to save')

        # Check if there is something to save
        if builder.get_parts_len() == 0:
            raise commands.CommandError('Cannot save an empty story')

        # Change story title if needed
        if title is not None:
            builder.set_title(title)

        # Create the new story in database
        story = builder.to_story()
        resp = await get_nanapi().histoire.histoire_new_histoire(NewHistoireBody(**story))
        if not success(resp):
            raise RuntimeError(resp.result)

        # Stop recording
        del self.story_builders_by_channel_user[(channel.id, user.id)]

        # Tells the user the cancellation has been done
        await ctx.message.add_reaction(self.ok_hand)

    @histoire.command(help='Cancel the creation of the story')
    async def cancel(self, ctx: commands.Context) -> None:
        # Check a story is recording
        channel: 'MessageableChannel' = ctx.channel
        user: UserType = ctx.author
        if (channel.id, user.id) not in self.story_builders_by_channel_user:
            raise commands.CommandError('Nothing to cancel')

        # Cancel story creation
        del self.story_builders_by_channel_user[(channel.id, user.id)]

        # Tells the user the cancellation has been done
        await ctx.message.add_reaction(self.ok_hand)

    @commands.has_permissions(administrator=True)
    @histoire.command(hidden=True, help='Delete a story')
    async def delete(self, ctx: commands.Context, story_id: str) -> None:
        try:
            uuid = UUID(story_id)
        except ValueError:
            raise commands.BadArgument(f'Invalid story id `{story_id}`')

        resp = await get_nanapi().histoire.histoire_delete_histoire(uuid)
        if not success(resp):
            raise RuntimeError(resp.result)
        deleted = resp.result

        if deleted is None:
            raise commands.CommandError(f'Story with id {story_id} does not exist')

        await ctx.send(f'{deleted.id} has been deleted')

    @histoire.command(help='List available stories')
    async def list(self, ctx: commands.Context) -> None:
        resp = await get_nanapi().histoire.histoire_histoire_index()
        if not success(resp):
            raise RuntimeError(resp.result)
        stories_resp = resp.result
        # Fetch all stories from database
        stories = [f'{story.id}: {story.title}' for story in stories_resp]

        # Show list
        if stories:
            await AutoNavigatorView.create(
                self.bot, ctx.reply, title='Available stories', description='\n'.join(stories)
            )
        else:
            await ctx.send('No available story')


async def setup(bot: Bot) -> None:
    await bot.add_cog(Histoire(bot))
