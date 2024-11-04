from typing import Any, Callable

__all__ = ('RequiredSettings',)


class RequiredSettings:

    def __init__(self, *args: Any):
        self.configured = all(args)

    def __bool__(self):
        return self.configured

    def __call__[T: Callable[..., Any]](self, func: T) -> T | None:
        if self.configured:
            return func
        else:
            return None
