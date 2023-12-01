"""A collection of deecorators."""

import asyncio
import functools
from typing import Any
from typing import Callable
from asyncio import Future


def run_in_executor(_func: Callable[..., Any]) -> Callable[..., Any]:
    """Run blocking code async."""

    @functools.wraps(_func)
    def _wrapped(*args, **kwargs) -> Future:  # type: ignore[no-untyped-def]
        loop = asyncio.get_running_loop()
        func = functools.partial(_func, *args, **kwargs)
        return loop.run_in_executor(executor=None, func=func)

    return _wrapped
