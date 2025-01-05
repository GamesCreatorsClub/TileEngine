from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from editor.pygame_components import ScrollableCanvas
from engine.tmx import TiledTileset


class TilesetCanvas(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 tileset: Optional[TiledTileset],
                 tile_selected_callback: Callable[[Optional[int]], None]) -> None:
        super().__init__(rect, allow_over=False)
        self._tileset = tileset
        self.tile_selected_callback = tile_selected_callback
        self._tileset_rect: Optional[Rect] = None
        self._tileset_rect2: Optional[Rect] = None
        self._tileset_rect3: Optional[Rect] = None
        self.h_scrollbar.visible = tileset is not None
        self.v_scrollbar.visible = tileset is not None
        self._selected_tile: Optional[int] = None
        self._selection = Rect(0, 0, 1, 1)
        self._mouse_is_down = False

    @property
    def selected_tile(self) -> Optional[int]:
        # return self._selected_tile

        tileset = self._tileset
        if tileset is not None:
            return self._selection.y * (tileset.width // tileset.tilewidth) + self._selection.x + tileset.firstgid

        return None

    @selected_tile.setter
    def selected_tile(self, tile_id: int) -> None:
        tileset = self._tileset
        if tile_id < tileset.firstgid or tile_id > tileset.tilecount + tileset.firstgid:
            self._selected_tile = None
            self.tile_selected_callback(tile_id)
            self._selection.width = 0
            self._selection.height = 0
            return
        self._selected_tile = tile_id
        gid = tile_id - tileset.firstgid
        w = (tileset.width // tileset.tilewidth)
        self._selection.update(gid % w, gid // w, 1, 1)

        self._calc_tileset_rect()
        self.tile_selected_callback(tile_id)

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

            if self._selected_tile is not None:
                if self._selected_tile < tileset.firstgid or self._selected_tile >= tileset.firstgid + tileset.tilecount:
                    self._selected_tile = tileset.firstgid

                self._calc_tileset_rect()

    def _calc_tileset_rect(self) -> None:
        tileset = self._tileset
        x = self._selection.x * tileset.tilewidth + self.h_scrollbar.offset
        y = self._selection.y * tileset.tileheight + self.v_scrollbar.offset
        self._tileset_rect = Rect(x + self.rect.x, y + self.rect.y, tileset.tilewidth * self._selection.width, tileset.tileheight * self._selection.height)
        self._tileset_rect3 = self._tileset_rect.inflate(2, 2)
        self._tileset_rect2 = self._tileset_rect.inflate(4, 4)

    def scrollbars_moved(self) -> None:
        if self._selected_tile is not None:
            self._calc_tileset_rect()

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
        self._mouse_is_down = True
        if not other:
            if self._tileset is not None:
                tileset = self._tileset
                x = x - self.h_scrollbar.offset - self.rect.x
                y = y - self.v_scrollbar.offset - self.rect.y
                x = x // tileset.tilewidth
                y = y // tileset.tileheight

                self._selection.update(x, y, 1, 1)
                self._calc_tileset_rect()

                gid = x + y * (tileset.width // tileset.tilewidth)
                if gid < tileset.tilecount:
                    gid = gid + tileset.firstgid
                    self.selected_tile = gid
                    return True
        return other

    def mouse_up(self, x: int, y: int, modifier: int) -> bool:
        other = super().mouse_up(x, y, modifier)
        self._mouse_is_down = False
        return other

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        other = super().mouse_up(x, y, modifier)
        if not other and self._mouse_is_down:
            if self._tileset is not None:
                tileset = self._tileset
                x = x - self.h_scrollbar.offset - self.rect.x
                y = y - self.v_scrollbar.offset - self.rect.y
                x = x // tileset.tilewidth
                y = y // tileset.tileheight

                # print(f"Move: {x}, {y} - {self._selection}")
                if not self._selection.collidepoint(x, y):
                    if x < self._selection.x:
                        self._selection.width += self._selection.x - x
                        self._selection.x = x
                    elif x + 1 > self._selection.right:
                        self._selection.width += x + 1 - self._selection.right
                    if y < self._selection.y:
                        self._selection.height += self._selection.y - y
                        self._selection.y = y
                    elif y + 1 > self._selection.bottom:
                        self._selection.height += y + 1 - self._selection.bottom

                self._calc_tileset_rect()
                return True
        return other

    def mouse_out(self, x: int, y: int) -> bool:
        other = super().mouse_out(x, y)
        self._mouse_is_down = False
        return other
