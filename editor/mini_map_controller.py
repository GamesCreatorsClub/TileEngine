from typing import Any, Optional

import pygame.draw
from pygame import Rect, Surface

from editor.actions_controller import ActionsController, ChangeKind
from editor.map_controller import MapController
from editor.pygame_components import Component
from engine.tmx import TiledElement, TiledMap
from engine.utils import clip


class MiniMap(Component):
    def __init__(self,
                 rect: Rect,
                 actions_controller: ActionsController,
                 map_controller: MapController):
        super().__init__(rect)
        self.actions_controller = actions_controller
        self.map_controller = map_controller
        self.map_controller.scrollbars_moved_callbacks.append(self._scrollbars_moved)
        self.tiled_map: Optional[TiledMap] = None
        self.border = rect.copy()
        self.internal = rect.copy()
        self.place = Rect(0, 0, 0, 0)
        self.map_shape = Rect(0, 0, 0, 0)
        self.redefine_rect(rect)
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_is_down = False
        actions_controller.tiled_map_callbacks.append(self._tiled_map_callback)
        actions_controller.element_attr_change_callbacks.append(self._element_attr_change_callback)

    def _element_attr_change_callback(self, element: TiledElement, _kind: ChangeKind, key: str, _value: Any) -> None:
        if element == self.map_controller.tiled_map and key in ["width", "height", "tilewidth", "tileheight"]:
            self._update_map_shape()

    def _tiled_map_callback(self, tiled_map: TiledMap) -> None:
        self.tiled_map = tiled_map
        self._update_map_shape()

    def _update_map_shape(self) -> None:
        tiled_map = self.tiled_map
        if tiled_map is not None:
            if tiled_map.width >= tiled_map.height:
                h = self.internal.width * tiled_map.height // tiled_map.width
                if h <= self.internal.height:
                    self.map_shape.update(
                        self.internal.x,
                        self.internal.y + (self.internal.height - h) // 2,
                        self.internal.width,
                        h
                    )
                else:
                    w = self.internal.height * tiled_map.width // tiled_map.height
                    self.map_shape.update(
                        self.internal.x + (self.internal.width - w),
                        self.internal.y,
                        w,
                        self.internal.height
                    )
            else:
                w = self.internal.height * tiled_map.width // tiled_map.height
                if w <= self.internal.width:
                    self.map_shape.update(
                        self.internal.x + (self.internal.width - w) // 2,
                        self.internal.y,
                        w,
                        self.internal.height
                    )
                else:
                    h = self.internal.width * tiled_map.height // tiled_map.width
                    self.map_shape.update(
                        self.internal.x,
                        self.internal.y + (self.internal.height - h) // 2,
                        h,
                        self.internal.height
                    )

    def _scrollbars_moved(self, _dx: int, _dy: int) -> None:
        self._update_map_shape()
        h_scrollbar = self.map_controller.h_scrollbar
        v_scrollbar = self.map_controller.v_scrollbar
        xo = -h_scrollbar.offset * self.map_shape.width / h_scrollbar.width
        yo = -v_scrollbar.offset * self.map_shape.height / v_scrollbar.width

        w = self.map_shape.width * h_scrollbar.rect.width / h_scrollbar.width
        h = self.map_shape.height * v_scrollbar.rect.height / v_scrollbar.width
        if self.map_shape.y > self.internal.y:
            yo -= (self.internal.y - self.map_shape.y)
        if self.map_shape.x > self.internal.x:
            xo -= (self.internal.x - self.map_shape.x)

        self.place.update(self.internal.x + xo, self.internal.y + yo, w, h)

    def redefine_rect(self, rect: Rect) -> None:
        self.rect = rect
        self.border.update(self.rect)
        self.border.inflate_ip(-2, -2)
        self.internal.update(self.rect)
        self.internal.inflate_ip(-6, -6)
        self._scrollbars_moved(0, 0)

    def draw(self, surface: Surface) -> None:
        pygame.draw.rect(surface, (128, 128, 128), self.border, width=2)
        with clip(surface, self.internal):
            if self.tiled_map is not None:
                background_colour = self.tiled_map.backgroundcolor if self.tiled_map.backgroundcolor is not None else (0, 0, 0)
                pygame.draw.rect(surface, background_colour, self.map_shape)
            pygame.draw.rect(surface, (255, 255, 0), self.place, width=1)

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_is_down = True
            self.mouse_x = x
            self.mouse_y = y
            return True
        return False

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_is_down = False
            return True
        return False

    def mouse_in(self, x: int, y: int) -> bool:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
        if self.mouse_is_down:
            self.mouse_x = x
            self.mouse_y = y
            return True
        return False

    def mouse_out(self, x: int, y: int) -> bool:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        return True

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        if self.mouse_is_down:
            dx = x - self.mouse_x
            dy = y - self.mouse_y

            h_scrollbar = self.map_controller.h_scrollbar
            v_scrollbar = self.map_controller.v_scrollbar

            xr = h_scrollbar.width / self.map_shape.width
            yr = v_scrollbar.width / self.map_shape.height

            h_scrollbar.offset -= int(dx * xr)
            v_scrollbar.offset -= int(dy * yr)

            self.mouse_x = x
            self.mouse_y = y
            return True
        return False
