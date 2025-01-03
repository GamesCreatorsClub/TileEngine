from enum import Enum, auto
from typing import Optional, Callable

from pygame import Rect, Surface

from editor.pygame_components import Button


class ResizePosition(Enum):
    W = (-1, 0)
    SW = (-1, 1)
    S = (0, 1)
    SE = (1, 1)
    E = (1, 0)
    NE = (1, -1)
    N = (0, -1)
    NW = (-1, -1)

    def __new__(cls, dx: int, dy: int):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    def __init__(self, dx: int, dy: int) -> None:
        self.dx = dx
        self.dy = dy


class ResizeButton(Button):
    def __init__(self,
                 position: ResizePosition,
                 rect: Rect,
                 image: Surface,
                 callback: Callable[['ResizeButton', int, int], None],
                 mouse_over_image: Optional[Surface] = None) -> None:
        self.img_rect = image.get_rect()
        self.position = position
        super().__init__(
            self.calc_rect(rect),
            image,
            self._callback,
            mouse_over_image=mouse_over_image,
            selected_image=mouse_over_image,
            mouse_over_color=None,
            selected_color=None,
            border_color=None
        )
        self.position = position
        self.callback = callback
        self.last_mouse_x = 0
        self.last_mouse_y = 0

    def _callback(self) -> None:
        pass

    def update_rect(self, rect: Rect) -> None:
        self.rect = self.calc_rect(rect)
        self._image_rect = self._image.get_rect().copy()
        self._image_rect.center = self.rect.center

    def calc_rect(self, rect: Rect) -> Rect:
        if self.position == ResizePosition.W:
            return self.img_rect.move(rect.x - self.img_rect.width, rect.y + (rect.height - self.img_rect.height) // 2)
        elif self.position == ResizePosition.SW:
            return self.img_rect.move(rect.x - self.img_rect.width, rect.bottom)
        elif self.position == ResizePosition.S:
            return self.img_rect.move(rect.x + (rect.width - self.img_rect.width) // 2, rect.bottom)
        elif self.position == ResizePosition.SE:
            return self.img_rect.move(rect.right, rect.bottom)
        elif self.position == ResizePosition.E:
            return self.img_rect.move(rect.right, rect.y + (rect.height - self.img_rect.height) // 2)
        elif self.position == ResizePosition.NE:
            return self.img_rect.move(rect.right, rect.y - self.img_rect.height)
        elif self.position == ResizePosition.N:
            return self.img_rect.move(rect.x + (rect.width - self.img_rect.width) // 2, rect.y - self.img_rect.height)
        elif self.position == ResizePosition.NW:
            return self.img_rect.move(rect.x - self.img_rect.width, rect.y - self.img_rect.height)

        raise ValueError()

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = True
        self.last_mouse_x = x
        self.last_mouse_y = y
        return True

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = False
        self.last_mouse_x = x
        self.last_mouse_y = y
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.mouse_pressed:
            dx = x - self.last_mouse_x
            dy = y - self.last_mouse_y

            self.last_mouse_x = x
            self.last_mouse_y = y

            self.callback(self, self.position.dx * dx, self.position.dy * dy)

        self.last_mouse_x = x
        self.last_mouse_y = y
        return True

    def mouse_in(self, x: int, y: int) -> bool:
        self.mouse_over = True
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        self.mouse_over = False
        self.mouse_pressed = False
        return True
