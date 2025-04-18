import logging
from collections import defaultdict

import discord
from discord import AllowedMentions, app_commands
from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed, MultiplexingContext, MultiplexingMessage, UserType
from nanachan.settings import AI_MODEL, RequiresAI
from nanachan.utils.ai import AgentHelper, RunDeps

logger = logging.getLogger(__name__)


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    def __init__(self, bot: Bot):
        self.bot = bot
        assert AI_MODEL
        self.model = AI_MODEL
        self.agent = AgentHelper(self.model)
        self.messages = defaultdict[int, list[ModelMessage]](list)

    @app_commands.command(name='chat')
    @legacy_command()
    async def new_chat(
        self, ctx: LegacyCommandContext, prompt: str, image: discord.Attachment | None = None
    ):
        """Chat with AI"""
        embed = Embed(description=prompt, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        if image:
            embed.set_image(url=image.url)
        embed.set_footer(text=self.model.model_name)
        resp = await ctx.reply(embed=embed)

        attachments = [image] if image else []

        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                thread = await resp.create_thread(name=prompt[:100], auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None

        await self.chat(ctx.author, thread, prompt, attachments, reply_to=reply_to)

    async def chat(
        self,
        author: UserType,
        thread: discord.Thread,
        prompt: str,
        attachments: list[discord.Attachment],
        reply_to: discord.Message | MultiplexingMessage | None = None,
    ):
        async with thread.typing():
            content: list[UserContent] = [prompt]
            for attachment in attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

            history = self.messages[thread.id]

            deps = RunDeps(self.bot, author)

            send = reply_to.reply if reply_to is not None else thread.send
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                async for block in self.agent.yield_agent_output(content, history, deps):
                    resp = await send(block, allowed_mentions=allowed_mentions)
                    send = resp.reply
            except Exception as e:
                await send(f'An error occured while streaming the response:\n{e}')
                logger.exception(e)

    @NanaGroupCog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if (
            ctx.bot.user in ctx.message.mentions
            and isinstance(ctx.channel, discord.Thread)
            and ctx.channel.id in self.messages
        ):
            prompt = ctx.message.stripped_content
            if ctx.bot.user is not None:
                prompt = prompt.replace(ctx.bot.user.mention, '')
            attachments = ctx.message.attachments
            await self.chat(ctx.author, ctx.channel, prompt, attachments, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
