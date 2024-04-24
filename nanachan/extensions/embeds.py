import asyncio
import contextlib as ctxlib
import datetime
import functools
import logging
import re
from collections import OrderedDict
from functools import partial
from html.parser import HTMLParser
from pprint import pformat
from typing import List, Optional

import discord
from discord.ext import commands
from discord.utils import escape_markdown
from yarl import URL

from nanachan.discord.helpers import Colour, Embed
from nanachan.settings import RequiresReddit, RequiresTwitch
from nanachan.utils.mime import is_image
from nanachan.utils.misc import get_session, print_exc, to_hikari
from nanachan.utils.reddit import get_reddit
from nanachan.utils.twitch import TwitchAPI

logger = logging.getLogger(__name__)


class OpenGraphParser(HTMLParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.og = {}
        self.colour = Colour.default()

    @property
    def valid(self):
        return any(['title' in self.og,
                    'site_name' in self.og])

    def handle_starttag(self, tag, attrs):
        if tag != 'meta':
            return

        attrs = dict(attrs)
        prop = attrs.get('property') or ""
        if prop.startswith('og:'):
            self.og[prop[3:]] = attrs['content']

        if attrs.get('name') == "theme-color":
            colour = attrs['content']
            assert colour is not None
            self.colour = Colour.from_string(colour)

    handle_startendtag = handle_starttag


class Embedder:

    def __init__(self, regex, func):
        self.regex: re.Pattern[str] = re.compile(regex)
        self.func = func

    def check(self, url: URL):
        return self.regex.search(str(url))

    def __call__(self, ctx, url, *args, **kwargs):
        return self.func(ctx, url, *args, **kwargs)


class CancelEmbeds(Exception):
    pass


class Embeds(commands.Cog):

    url_prog = re.compile(r"https?://[^\s]+")
    embedders = []
    fallback_embedders = []

    def __init__(self, bot):
        self.bot = bot

    @classmethod
    def set_embedder(cls, regex: str, func, fallback=False):
        new_embedder = Embedder(regex, func)
        if fallback:
            cls.fallback_embedders.append(new_embedder)
        else:
            cls.embedders.append(new_embedder)

        return new_embedder

    @classmethod
    def embedder(cls, regex: str, fallback=False):

        def decorator(func):
            return cls.set_embedder(regex, func, fallback)

        return decorator

    @classmethod
    async def default_embedder(
            cls,
            ctx,
            url: URL,
            strip_image: bool = False) -> Optional[List[discord.Embed]]:
        headers = {
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0"
        }
        try:
            async with asyncio.timeout(5):
                for embedder in cls.fallback_embedders:
                    if match := embedder.check(url):
                        return await embedder(ctx, url, *match.groups())

                async with get_session().get(url, headers=headers) as resp:
                    if "text/html" in resp.headers['Content-Type']:
                        parser = OpenGraphParser()
                        parser.feed(await resp.text())

                        logger.debug(pformat(parser.og))
                        logger.debug(str(parser.colour))

                        if parser.valid:

                            embed = Embed(title=parser.og.get('title', None),
                                          description=parser.og.get(
                                              'description'),
                                          url=parser.og.get('url', url),
                                          colour=parser.colour)

                            # discord doesn't support video embeds, so we link the video
                            if 'video:url' in parser.og:
                                embed.add_field(name="Video",
                                                value=f"[Link]({parser.og['video:url']})")

                            if 'site_name' in parser.og:
                                embed.set_author(name=parser.og['site_name'])

                            if not strip_image and (image_url := parser.og.get('image', None)):
                                image_url = URL(image_url)
                                if image_url.path:
                                    if not image_url.scheme:
                                        image_url = url.join(image_url)

                                    embed.set_image(url=str(image_url))

                            return [embed]
        except CancelEmbeds:
            raise
        except Exception as e:
            print_exc(e)

    @staticmethod
    def get_embedders(ctx, *urls: URL, force=False, fallback=True):
        embedders = OrderedDict()
        found_custom_embeds = False

        with ctxlib.suppress(CancelEmbeds):
            for url in urls:
                if url in embedders:
                    continue

                for embedder in Embeds.embedders:
                    if match := embedder.check(url):
                        found_custom_embeds = True
                        embedders[url] = functools.partial(
                            embedder, ctx, url, *match.groups())
                        break

                else:  # tfw when I find a use to for ... else
                    if fallback:
                        embedders[url] = functools.partial(
                            Embeds.default_embedder, ctx, url)

            if found_custom_embeds or force:
                return asyncio.gather(*[em() for em in embedders.values()])


async def reddit_post_embedder(post, force_image=False):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(post.subreddit.load())
        if post.author is not None:
            tg.create_task(post.author.load())
        _is_image = await tg.create_task(is_image(post.url))

    if force_image and not _is_image:
        return

    if post.over_18 and post.spoiler:
        description = '`[NSFW][SPOILER]`'
    elif post.over_18:
        description = '`[NSFW]`'
    elif post.spoiler:
        description = '`[SPOILER]`'
    else:
        if len(post.selftext) > 2048:
            description = post.selftext[:(2048-20)] + '\n\n`[TRUNCATED POST]`'
        else:
            description = post.selftext

    def embed_creator():
        embed = Embed(colour=0xFF4500,
                      title=escape_markdown(post.title),
                      description=description,
                      timestamp=datetime.datetime.fromtimestamp(
                          post.created_utc),
                      url=f'https://www.reddit.com{post.permalink}')

        embed.set_author(name=f'r/{post.subreddit}',
                         url=f'https://www.reddit.com/r/{post.subreddit}',
                         icon_url=getattr(post.subreddit, 'icon_img', None))
        embed.set_footer(
            text=f'u/{"[deleted]" if post.author is None else post.author.name} on reddit',
            icon_url=getattr(post.author, 'icon_img', None)
        )
        embed.add_field(name='🔺 Upvotes', value=post.score)
        embed.add_field(name='💬 Comments', value=post.num_comments)
        return embed

    if hasattr(post, "is_gallery") and post.is_gallery:
        embeds = []
        for item in post.gallery_data["items"]:
            embed = embed_creator()
            embed.set_image(
                url=post.media_metadata[item['media_id']]['s']['u'])
            embeds.append(embed)

        return embeds

    else:
        embed = embed_creator()
        if post.over_18 or post.spoiler:
            embed.set_image(url=post.preview['images'][0]['variants']
                            ['obfuscated']['source']['url'])
        elif _is_image:
            embed.set_image(url=post.url)
        elif (hasattr(post, 'media') and post.media and 'oembed' in post.media
                and 'thumbnail_url' in post.media['oembed']):
            # There might still be a gif in thumbnail
            embed.set_image(url=post.media['oembed']['thumbnail_url'])
        elif hasattr(post, 'preview'):
            embed.set_image(url=post.preview['images'][0]['source']['url'])

        return [embed]


@Embeds.embedder(r"\breddit.com/r/[^/]+/comments")
@RequiresReddit
async def reddit_post_embedder_from_url(ctx, url: URL):
    reddit = get_reddit()
    assert reddit is not None

    post = await reddit.submission(url=str(url))
    return await reddit_post_embedder(post)


@Embeds.embedder(r"//(?:www\.)?twitch\.tv/([^/]+)$")
@RequiresTwitch
async def twitch_channel_embed(ctx, url: URL, username: str):
    twitch = TwitchAPI.get_twitch()
    assert twitch is not None

    streams, users = await asyncio.gather(
        twitch.api('GET', 'streams', first=1, user_login=username),
        twitch.api('GET', 'users', login=username)
    )

    stream_data = streams.get('data')
    user_data = users.get('data')

    if user_data and stream_data:
        stream = stream_data[0]
        user = user_data[0]
        user_url = f"https://twitch.tv/{username}"

        embed = Embed(title=stream['title'],
                      url=user_url,
                      colour=Colour(0x9244ff))

        thumb = await to_hikari(stream['thumbnail_url'].format(width=1280, height=720))
        footer = escape_markdown(
            f"Twitch • {stream['game_name']} ⋅ {stream['viewer_count']} viewers"
        )

        embed.set_author(name=user['display_name'],
                         icon_url=user['profile_image_url'],
                         url=user_url)
        embed.set_image(url=thumb['url'])
        embed.set_footer(text=footer,
                         icon_url='https://hikari.butaishoujo.moe/p/430a4b57/twitch.png')

        return [embed]


Embeds.set_embedder(r"\bnyaa.si", partial(
    Embeds.default_embedder, strip_image=True))


async def setup(bot):
    await bot.add_cog(Embeds(bot))
