from collections import namedtuple
from contextlib import contextmanager
from typing import Generator, Union

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
