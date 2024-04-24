import asyncio

from nanachan.utils.misc import async_dummy, dummy

__all__ = ('RequiredSettings',)


class RequiredSettings:

    def __init__(self, *args):
        self.configured = all(args)

    def __bool__(self):
        return self.configured

    def __call__(self, func):
        if self.configured:
            return func
        elif asyncio.iscoroutinefunction(func):
            return async_dummy
        else:
            return dummy
