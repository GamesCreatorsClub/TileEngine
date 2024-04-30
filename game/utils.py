from contextlib import contextmanager
from typing import Generator, Union

from pygame import Rect, Surface


@contextmanager
def clip(surface: Surface, rect: Rect) -> Generator[None, Rect, None]:
    existing_clip = surface.get_clip()
    surface.set_clip(rect)
    yield rect
    surface.set_clip(existing_clip)


def abs(v: Union[int, float]) -> Union[int, float]:
    if v < 0: return -v
    return v


def is_close(x1: Union[int, float], x2: Union[int, float], y1: Union[int, float], y2: Union[int, float]) -> bool:
    return -1 <= (x1 - x2) <= 1 and -1 <= (y1 - y2) <= 1
