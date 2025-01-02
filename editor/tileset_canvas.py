from typing import Optional

import pygame.draw
from pygame import Rect, Surface

from editor.pygame_components import ScrollableCanvas
from engine.tmx import TiledTileset


class TilesetCanvas(ScrollableCanvas):
    def __init__(self, rect: Rect, tileset: Optional[TiledTileset]) -> None:
        super().__init__(rect, allow_over=False)
        self._tileset = tileset
        self._tileset_rect: Optional[Rect] = None
        self._tileset_rect2: Optional[Rect] = None
        self._tileset_rect3: Optional[Rect] = None
        self.h_scrollbar.visible = tileset is not None
        self.v_scrollbar.visible = tileset is not None
        self._selected_tile: Optional[int] = None

    @property
    def selected_tile(self) -> int:
        return self._selected_tile

    @selected_tile.setter
    def selected_tile(self, tile_id: int) -> None:
        tiledset = self._tileset
        if tile_id < tiledset.firstgid or tile_id > tiledset.tilecount + tiledset.firstgid:
            self._selected_tile = None
            return
        self._selected_tile = tile_id

        self._calc_tileset_rect(self._selected_tile - tiledset.firstgid)

    @property
    def tileset(self) -> TiledTileset:
        return self._tileset

    @tileset.setter
    def tileset(self, tileset: TiledTileset) -> None:
        self._tileset = tileset
        if tileset is None:
            self.v_scrollbar.visible = False
            self.h_scrollbar.visible = False
        else:
            self.v_scrollbar.visible = True
            self.h_scrollbar.visible = True
            self.h_scrollbar.width = tileset.width
            self.v_scrollbar.width = tileset.height

    def _calc_tileset_rect(self, gid: int) -> None:
        tiledset = self._tileset
        x = (gid % (tiledset.width // tiledset.tilewidth)) * tiledset.tilewidth + self.h_scrollbar.offset
        y = (gid // (tiledset.width // tiledset.tilewidth)) * tiledset.tileheight + self.v_scrollbar.offset
        self._tileset_rect = Rect(x + self.rect.x, y + self.rect.y, tiledset.tilewidth, tiledset.tileheight)
        self._tileset_rect3 = self._tileset_rect.inflate(2, 2)
        self._tileset_rect2 = self._tileset_rect.inflate(4, 4)

    def scrollbars_moved(self) -> None:
        if self._selected_tile is not None:
            self._calc_tileset_rect(self._selected_tile - self._tileset.firstgid)

    def _local_draw(self, surface: Surface) -> None:
        if self._tileset is not None:
            x = self.rect.x
            y = self.rect.y
            pygame.draw.rect(surface, (0, 0, 0), self.rect)
            surface.blit(self._tileset.image_surface, (x + self.h_scrollbar.offset, y + self.v_scrollbar.offset))

            if self._selected_tile is not None:
                pygame.draw.rect(surface, (128, 0, 0), self._tileset_rect3, width=1)
                pygame.draw.rect(surface, (128, 255, 255), self._tileset_rect2, width=1)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        other = super().mouse_down(x, y, modifier)
        if not other:
            if self._tileset is not None:
                tileset = self._tileset
                x = x - self.h_scrollbar.offset - self.rect.x
                y = y - self.v_scrollbar.offset - self.rect.y
                x = x // tileset.tilewidth
                y = y // tileset.tileheight
                gid = x + y * (tileset.width // tileset.tilewidth)
                if gid < tileset.tilecount:
                    gid = gid + tileset.firstgid
                    self.selected_tile = gid
                    return True
        return other
