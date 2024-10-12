from typing import Generator

from pygame import Rect

from engine.level import Level


class CollisionResult:

    def __init__(self) -> None:
        self.rects = [Rect(0, 0, 0, 0) for _ in range(9)]
        self.gids = [0 for _ in range(9)]
        self.total = 0

    def clear(self) -> None:
        self.total = 0

    def has_collided_gids(self) -> bool:
        return any(self.gids[i] for i in range(self.total) if self.gids[i] > 0)

    def collided_rects(self) -> Generator[tuple[int, Rect], None, None]:
        for i in range(self.total):
            g = self.gids[i]
            if g > 0:
                yield g, self.rects[i]

    def collect(self, rect: Rect, level: Level) -> 'CollisionResult':
        self.total = 0

        main_layer = level.main_layer
        level_map = level.map
        t_w = level_map.tilewidth
        t_h = level_map.tileheight

        t_col = rect.x // t_w
        t_row = rect.y // t_h
        start_col = t_col

        t_x = t_col * t_w
        t_y = t_row * t_h

        try:
            while t_y + t_h >= rect.y and t_y < rect.bottom:
                while t_x + t_w > rect.x and t_x < rect.right:
                    self.rects[self.total].update(t_x, t_y, t_w, t_h)
                    self.gids[self.total] = main_layer.data[t_row][t_col]
                    self.total += 1
                    t_col += 1
                    t_x = t_col * t_w
                t_col = start_col
                t_row += 1
                t_x = t_col * t_w
                t_y = t_row * t_h
        except IndexError as e:
            raise IndexError(f"[{t_row}][{t_col}]", e)

        return self
