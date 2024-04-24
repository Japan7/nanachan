from functools import cache

import asyncpraw

__all__ = ('get_reddit',)


@cache
def get_reddit():
    from nanachan.settings import (REDDIT_CLIENT_ID, REDDIT_SECRET,  # noqa
                                   REDDIT_USER_AGENT, RequiresReddit)
    if RequiresReddit:
        assert REDDIT_CLIENT_ID and REDDIT_SECRET and REDDIT_USER_AGENT
        return asyncpraw.Reddit(client_id=REDDIT_CLIENT_ID,
                                client_secret=REDDIT_SECRET,
                                user_agent=REDDIT_USER_AGENT)
