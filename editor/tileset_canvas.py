from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from editor.pygame_components import ScrollableCanvas
from engine.tmx import TiledTileset


class TilesetCanvas(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 tileset: Optional[TiledTileset],
                 tile_selected_callback: Callable[[Optional[list[list[int]]]], None]) -> None:
        super().__init__(rect, allow_over=False)
        self._tileset = tileset
        self.tile_selected_callback = tile_selected_callback
        self._tileset_rect: Optional[Rect] = None
        self._tileset_rect2: Optional[Rect] = None
        self._tileset_rect3: Optional[Rect] = None
        self.h_scrollbar.visible = tileset is not None
        self.v_scrollbar.visible = tileset is not None
        self._selected_tile: Optional[int] = None
        self._selection_rect = Rect(0, 0, 1, 1)
        self._selection: Optional[list[list[int]]] = None
        self._mouse_is_down = False

    @property
    def selected_tile(self) -> Optional[int]:
        # return self._selected_tile

        tileset = self._tileset
        if tileset is not None:
            return self._selection_rect.y * tileset.width + self._selection_rect.x + tileset.firstgid

        return None

    @selected_tile.setter
    def selected_tile(self, tile_id: int) -> None:
        tileset = self._tileset
        if tile_id < tileset.firstgid or tile_id > tileset.tilecount + tileset.firstgid:
            self._selected_tile = None
            self.tile_selected_callback(tile_id)
            self._selection_rect.width = 0
            self._selection_rect.height = 0
            return
        self._selected_tile = tile_id
        gid = tile_id - tileset.firstgid
        self._selection_rect.update(gid % tileset.width, gid // tileset.width, 1, 1)

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
            self._selection = None
            self._tileset_rect = None
        else:
            self.v_scrollbar.visible = True
            self.h_scrollbar.visible = True
            self.h_scrollbar.width = tileset.width * tileset.tilewidth
            self.v_scrollbar.width = tileset.height * tileset.tileheight

            if self._selected_tile is not None:
                if self._selected_tile < tileset.firstgid or self._selected_tile >= tileset.firstgid + tileset.tilecount:
                    self._selected_tile = tileset.firstgid

                self._calc_tileset_rect()

    def select_tile(self, gid: Optional[int]) -> None:
        if self._tileset is not None:
            g = gid - self._tileset.firstgid
            x = g % self._tileset.width
            y = g // self._tileset.width
            self._selection_rect.update(x, y, 1, 1)
            self._selection = [[gid]]
        else:
            self._tileset_rect = None
            self._selection = None

    @property
    def selection(self) -> Optional[list[list[int]]]:
        return self._selection

    @selection.setter
    def selection(self, data: Optional[list[list[int]]]) -> None:
        self._selection = data
        self.tile_selected_callback(data)

    def _calc_tileset_rect(self) -> None:
        tileset = self._tileset
        x = self._selection_rect.x * tileset.tilewidth + self.h_scrollbar.offset
        y = self._selection_rect.y * tileset.tileheight + self.v_scrollbar.offset
        self._tileset_rect = Rect(x + self.rect.x, y + self.rect.y, tileset.tilewidth * self._selection_rect.width, tileset.tileheight * self._selection_rect.height)
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

            if self._tileset_rect is not None:
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

                if x < tileset.width and y < tileset.height:
                    self._selection_rect.update(x, y, 1, 1)
                    self.selection = [[tileset.firstgid + x + y * tileset.width for x in range(self._selection_rect.x, self._selection_rect.right)] for y in range(self._selection_rect.y, self._selection_rect.bottom)]

                    self._calc_tileset_rect()
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
                if not self._selection_rect.collidepoint(x, y):
                    updated = False
                    if self._selection_rect.x > x >= 0:
                        self._selection_rect.width += self._selection_rect.x - x
                        self._selection_rect.x = x
                        updated = True
                    elif tileset.width > x + 1 > self._selection_rect.right:
                        self._selection_rect.width += x + 1 - self._selection_rect.right
                        updated = True
                    if 0 <= y < self._selection_rect.y:
                        self._selection_rect.height += self._selection_rect.y - y
                        self._selection_rect.y = y
                        updated = True
                    elif tileset.height > y + 1 > self._selection_rect.bottom:
                        self._selection_rect.height += y + 1 - self._selection_rect.bottom
                        updated = True
                    if updated:
                        self.selection = [[tileset.firstgid + x + y * tileset.width for x in range(self._selection_rect.x, self._selection_rect.right)] for y in range(self._selection_rect.y, self._selection_rect.bottom)]

                self._calc_tileset_rect()
                return True
        return other

    def mouse_out(self, x: int, y: int) -> bool:
        other = super().mouse_out(x, y)
        self._mouse_is_down = False
        return other
