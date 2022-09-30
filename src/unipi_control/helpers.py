import asyncio
import functools
from collections.abc import MutableMapping


class DataStorage(MutableMapping):
    """A container object that works like a dict.

    Attributes
    ----------
    data : dict
        Store the data for this container object.
    """

    def __init__(self):
        self.data: dict = {}

    def __getitem__(self, key: str):
        return self.data[key]

    def __setitem__(self, key: str, value):
        self.data[key] = value

    def __delitem__(self, key: str):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"{type(self).__name__}({self.data})"


def run_in_executor(_func):
    """Decorator to run blocking code."""

    @functools.wraps(_func)
    def wrapped(*args, **kwargs):
        loop = asyncio.get_running_loop()
        func = functools.partial(_func, *args, **kwargs)
        return loop.run_in_executor(executor=None, func=func)

    return wrapped
