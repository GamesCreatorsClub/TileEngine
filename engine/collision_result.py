from typing import Generator

from pygame import Rect


class CollisionResult:

    def __init__(self) -> None:
        self.rects = [Rect(0, 0, 0, 0) for _ in range(18)]
        self.gids = [0 for _ in range(18)]
        self.total = 0

    def clear(self) -> None:
        self.total = 0

    def has_collided_gids(self) -> bool:
        return any(self.gids[i] for i in range(self.total) if self.gids[i] > 0)

    def collided_rects(self) -> Generator[tuple[int, Rect], None, None]:
        for i in range(self.total):
            gid = self.gids[i]
            if gid > 0:
                yield gid, self.rects[i]
