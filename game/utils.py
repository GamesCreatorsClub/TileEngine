from contextlib import contextmanager
from typing import Generator

from pygame import Rect, Surface


@contextmanager
def clip(surface: Surface, rect: Rect) -> Generator[None, Rect, None]:
    existing_clip = surface.get_clip()
    surface.set_clip(rect)
    yield existing_clip
    surface.set_clip(existing_clip)
