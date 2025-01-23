import pygame.draw
from pygame import Rect, Surface

from editor.map_controller import MapController
from editor.pygame_components import Component
from engine.utils import clip


class MiniMap(Component):
    def __init__(self,
                 rect: Rect,
                 map_controller: MapController):
        super().__init__(rect)
        self.map_controller = map_controller
        self.map_controller.scrollbars_moved_callbacks.append(self._scrollbars_moved)
        self.border = rect.copy()
        self.internal = rect.copy()
        self.place = Rect(0, 0, 0, 0)
        self.redefine_rect(rect)
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_is_down = False

    def _scrollbars_moved(self, _dx: int, _dy: int) -> None:
        h_scrollbar = self.map_controller.h_scrollbar
        v_scrollbar = self.map_controller.v_scrollbar
        xo = -h_scrollbar.offset * self.internal.width / h_scrollbar.width
        yo = -v_scrollbar.offset * self.internal.width / v_scrollbar.width
        w = h_scrollbar.bar_width * self.internal.width / h_scrollbar.rect.width
        h = v_scrollbar.bar_width * self.internal.width / v_scrollbar.rect.height
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
        if self.mouse_is_down:
            self.mouse_x = x
            self.mouse_y = y
            return True
        return False

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        if self.mouse_is_down:
            dx = x - self.mouse_x
            dy = y - self.mouse_y

            h_scrollbar = self.map_controller.h_scrollbar
            v_scrollbar = self.map_controller.v_scrollbar

            xr = h_scrollbar.width / self.internal.width
            yr = v_scrollbar.width / self.internal.height

            h_scrollbar.offset -= int(dx * xr)
            v_scrollbar.offset -= int(dy * yr)

            self.mouse_x = x
            self.mouse_y = y
            return True
        return False
