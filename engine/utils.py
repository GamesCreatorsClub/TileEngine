from collections import namedtuple
from contextlib import contextmanager
from itertools import chain
from typing import Generator, Union, Any, Iterator, ChainMap

from pygame import Rect, Surface


Position = namedtuple("Position", ["x", "y"])
Size = namedtuple("Size", ["width", "height"])


@contextmanager
def clip(surface: Surface, rect: Rect) -> Generator[None, Rect, None]:
    existing_clip = surface.get_clip()
    surface.set_clip(rect)
    yield rect
    surface.set_clip(existing_clip)


def is_close(x1: Union[int, float], x2: Union[int, float], y1: Union[int, float], y2: Union[int, float]) -> bool:
    return -1 <= (x1 - x2) <= 1 and -1 <= (y1 - y2) <= 1


def int_tuple(t: tuple[Union[int, float], Union[int, float]]) -> tuple[int, int]:
    return int(t[0]), int(t[1])


class NestedDict(dict):
    def __init__(self) -> None:
        super().__init__()
        self.over: dict = {}

    def __getitem__(self, key: str) -> Any:
        if key in self.over:
            return self.over[key]
        return super().__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.over:
            self.over[key] = value
        else:
            super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if key in self.over:
            del self.over[key]
        else:
            super().__delitem__(key)

    def __iter__(self) -> Iterator:
        return iter(chain(self.over, super().__iter__()))

    def __len__(self) -> int:
        return len(self.over.keys() | super().keys())

    def __contains__(self, key) -> bool:
        return key in self.over or super().__contains__(key)
