import logging
from dataclasses import dataclass, field
from inspect import get_annotations
from typing import get_args

import discord
from discord import AllowedMentions, app_commands
from discord.app_commands import Choice
from pydantic_ai import BinaryContent, ModelHTTPError
from pydantic_ai.messages import ModelMessage, UserContent

from nanachan.discord.application_commands import LegacyCommandContext, legacy_command
from nanachan.discord.bot import Bot
from nanachan.discord.cog import NanaGroupCog
from nanachan.discord.helpers import Embed, MultiplexingContext, MultiplexingMessage, UserType
from nanachan.settings import AI_DEFAULT_MODEL, AI_MODEL_CLS, AI_PROVIDER, RequiresAI
from nanachan.utils.ai import AgentHelper, RunDeps
from nanachan.utils.misc import autocomplete_truncate

logger = logging.getLogger(__name__)


async def model_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]:
    assert AI_MODEL_CLS
    # trust me bro
    model_name_type = get_annotations(AI_MODEL_CLS, eval_str=True)['_model_name']
    model_names = get_args(get_args(model_name_type)[1])
    return [
        Choice(name=autocomplete_truncate(name), value=name)
        for name in model_names
        if current.lower() in name.lower()
    ]


@dataclass
class ChatContext:
    model_name: str
    history: list[ModelMessage] = field(default_factory=list)


@app_commands.guild_only()
class AI(NanaGroupCog, group_name='ai', required_settings=RequiresAI):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.agent = AgentHelper()
        self.contexts = dict[int, ChatContext]()

    @app_commands.command(name='chat')
    @app_commands.autocomplete(model_name=model_autocomplete)
    @legacy_command()
    async def new_chat(
        self,
        ctx: LegacyCommandContext,
        prompt: str,
        attachment: discord.Attachment | None = None,
        model_name: str | None = None,
    ):
        """Chat with AI"""
        if not model_name:
            assert AI_DEFAULT_MODEL
            model_name = AI_DEFAULT_MODEL

        embed = Embed(description=prompt, color=ctx.author.accent_color)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        if attachment and attachment.content_type and attachment.content_type.startswith('image/'):
            embed.set_image(url=attachment.url)
        embed.set_footer(text=model_name)
        resp = await ctx.reply(embed=embed)

        attachments = []
        if attachment:
            attachments.append(attachment)

        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
            reply_to = resp
        else:
            async with ctx.channel.typing():
                thread = await resp.create_thread(name=prompt[:100], auto_archive_duration=60)
                await thread.add_user(ctx.author)
                reply_to = None

        self.contexts[thread.id] = ChatContext(model_name=model_name)
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
                if attachment.content_type:
                    data = await attachment.read()
                    content.append(BinaryContent(data, media_type=attachment.content_type))

            ctx = self.contexts[thread.id]

            deps = RunDeps(self.bot, author)

            send = reply_to.reply if reply_to is not None else thread.send
            allowed_mentions = AllowedMentions.none()
            allowed_mentions.replied_user = True

            try:
                assert AI_MODEL_CLS
                assert AI_PROVIDER
                model = AI_MODEL_CLS(ctx.model_name, provider=AI_PROVIDER)  # type: ignore
                async for part in self.agent.iter_stream(content, ctx.history, model, deps):
                    resp = await send(part, allowed_mentions=allowed_mentions)
                    send = resp.reply
            except ModelHTTPError as e:
                await send(f'An error occured while streaming the response:\n{e}')
                logger.exception(e)

    @NanaGroupCog.listener()
    async def on_user_message(self, ctx: MultiplexingContext):
        if (
            ctx.bot.user in ctx.message.mentions
            and isinstance(ctx.channel, discord.Thread)
            and ctx.channel.id in self.contexts
        ):
            prompt = ctx.message.stripped_content
            if ctx.bot.user is not None:
                prompt = prompt.replace(ctx.bot.user.mention, '')
            attachments = ctx.message.attachments
            await self.chat(ctx.author, ctx.channel, prompt, attachments, reply_to=ctx.message)


async def setup(bot: Bot):
    await bot.add_cog(AI(bot))
