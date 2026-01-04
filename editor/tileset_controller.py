from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from editor.actions_controller import ActionsController
from editor.pygame_components import ScrollableCanvas
from editor.toolbar_panel import ToolbarPanel
from engine.tmx import TiledTileset


class TilesetActionsPanel(ToolbarPanel):
    def __init__(self,
                 rect: Rect,
                 icon_surface: Surface,
                 add_tileset_callback: Callable[[], None],
                 remove_tileset_callback: Callable[[], None],
                 grid_on_off: Callable[[], None],
                 add_tile: Callable[[], None],
                 erase_tile: Callable[[], None]) -> None:
        super().__init__(rect, icon_surface=icon_surface)

        self.add_tileset_button = self.add_button(18, -18, add_tileset_callback)
        self.remove_tileset_button = self.add_button(19, -19, remove_tileset_callback)
        self.grid_button = self.add_button(20, -20, grid_on_off)
        self.add_tile_button = self.add_button(21, -21, add_tile)
        self.erase_tile_button = self.add_button(1, -1, erase_tile)


class TilesetController(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 tileset: Optional[TiledTileset],
                 action_controller: ActionsController,
                 tile_selected_callback: Callable[[Optional[list[list[int]]]], None],
                 grid_toggle_callback: Callable[[bool], None]) -> None:
        super().__init__(rect, allow_over=False)
        self._tileset = tileset
        self.action_controller = action_controller
        action_controller.current_tileset_callbacks.append(self._current_tileset_callback)

        self.tile_selected_callback = tile_selected_callback
        self.grid_toggle_callback = grid_toggle_callback

        self._draw_tile_rects = False

        self._selection_rect = Rect(0, 0, 1, 1)
        self._selection: Optional[list[list[int]]] = None
        self._mouse_is_down = False

        self._tileset_rect: Optional[Rect] = None
        self._tileset_rect2: Optional[Rect] = None
        self._tileset_rect3: Optional[Rect] = None

        self.h_scrollbar.visible = tileset is not None
        self.v_scrollbar.visible = tileset is not None

    @property
    def tileset(self) -> TiledTileset:
        return self._tileset

    @property
    def selection_origin(self) -> tuple[int, int]:
        return self._selection_rect.x, self._selection_rect.y

    @property
    def selection(self) -> Optional[list[list[int]]]:
        return self._selection

    def _set_selection(self, data: Optional[list[list[int]]]) -> None:
        self._selection = data
        self.tile_selected_callback(data)

    def grid_on_off(self, on: Optional[bool] = None) -> None:
        if on is None:
            self._draw_tile_rects = not self._draw_tile_rects
        else:
            self._draw_tile_rects = on

        self.grid_toggle_callback(self._draw_tile_rects)

    def redefine_rect(self, rect) -> None:
        super().redefine_rect(rect)
        if self._tileset is not None:
            self._calc_tileset_rect()

    def _current_tileset_callback(self, tileset: TiledTileset) -> None:
        new_tileset = self._tileset != tileset
        self._tileset = tileset
        if tileset is None:
            self.v_scrollbar.visible = False
            self.h_scrollbar.visible = False
            self._selection = None
            self._tileset_rect = None
        else:
            self.v_scrollbar.visible = True
            self.h_scrollbar.visible = True
            self.h_scrollbar.width = tileset.width * (tileset.tilewidth + tileset.spacing) + tileset.margin
            self.v_scrollbar.width = tileset.height * (tileset.tileheight + tileset.spacing) + tileset.margin

            if new_tileset:
                self._selection_rect = Rect(0, 0, 1, 1)
                self._set_selection([[tileset.firstgid]])

            self._calc_tileset_rect()

    def _calc_tileset_rect(self) -> None:
        tileset = self._tileset
        x = self._selection_rect.x * (tileset.tilewidth + tileset.spacing) + self.h_scrollbar.offset + tileset.margin
        y = self._selection_rect.y * (tileset.tileheight + tileset.spacing) + self.v_scrollbar.offset + tileset.margin
        self._tileset_rect = Rect(
            x + self.rect.x,
            y + self.rect.y,
            (tileset.tilewidth + tileset.spacing) * self._selection_rect.width - tileset.spacing,
            (tileset.tileheight + tileset.spacing) * self._selection_rect.height - tileset.spacing)
        self._tileset_rect3 = self._tileset_rect.inflate(2, 2)
        self._tileset_rect2 = self._tileset_rect.inflate(4, 4)

    def scrollbars_moved(self, dx: int, dy: int) -> None:
        if self.selection is not None:
            self._calc_tileset_rect()

    def _local_draw(self, surface: Surface) -> None:
        tileset = self._tileset
        if tileset is not None:
            x = self.rect.x
            y = self.rect.y
            pygame.draw.rect(surface, (0, 0, 0), self.rect)
            surface.blit(tileset.image_surface, (x + self.h_scrollbar.offset, y + self.v_scrollbar.offset))

            if self._draw_tile_rects:
                total_x_offset = x + tileset.margin + self.h_scrollbar.offset
                total_y_offset = y + tileset.margin + self.v_scrollbar.offset
                rect = Rect(0, 0, tileset.tilewidth, tileset.tileheight)
                for t_y in range(tileset.height):
                    for t_x in range(tileset.width):
                        rect.x = t_x * (tileset.tilewidth + tileset.spacing) + total_x_offset
                        rect.y = t_y * (tileset.tileheight + tileset.spacing) + total_y_offset
                        pygame.draw.rect(surface, (64, 32, 32), rect, width=1)

            if self._tileset_rect is not None:
                pygame.draw.rect(surface, (128, 0, 0), self._tileset_rect3, width=1)
                pygame.draw.rect(surface, (128, 255, 255), self._tileset_rect2, width=1)

    def _mouse_to_tile(self, x: int, y: int) -> tuple[int, int]:
        tileset = self._tileset
        x = x - self.h_scrollbar.offset - self.rect.x - self._tileset.margin
        y = y - self.v_scrollbar.offset - self.rect.y - self._tileset.margin
        if x >= 0:
            x = x // (tileset.tilewidth + tileset.spacing)
        else:
            x = -1
        if y >= 0:
            y = y // (tileset.tileheight + tileset.spacing)
        else:
            y = -1
        return x, y

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        other = super().mouse_down(x, y, button, modifier)
        if button == 1:
            self._mouse_is_down = True
            if not other:
                if self._tileset is not None:
                    tileset = self._tileset
                    x, y = self._mouse_to_tile(x, y)

                    if 0 <= x < tileset.width and 0 <= y < tileset.height:
                        self._selection_rect.update(x, y, 1, 1)
                        self._set_selection([[tileset.firstgid + x + y * tileset.width for x in range(self._selection_rect.x, self._selection_rect.right)] for y in range(self._selection_rect.y, self._selection_rect.bottom)])

                        self._calc_tileset_rect()
                        return True
        return other

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        other = super().mouse_up(x, y, button, modifier)
        if button == 1:
            self._mouse_is_down = False
        return other

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        other = super().mouse_move(x, y, modifier)
        if not other and self._mouse_is_down:
            if self._tileset is not None:
                tileset = self._tileset
                x, y = self._mouse_to_tile(x, y)

                if x >= 0 and y >= 0 and not self._selection_rect.collidepoint(x, y):
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
                        self._set_selection([[tileset.firstgid + x + y * tileset.width for x in range(self._selection_rect.x, self._selection_rect.right)] for y in range(self._selection_rect.y, self._selection_rect.bottom)])

                self._calc_tileset_rect()
                return True
        return other

    def mouse_out(self, x: int, y: int) -> bool:
        other = super().mouse_out(x, y)
        self._mouse_is_down = False
        return other
