import pygame.draw
from typing import Callable, Optional

from pygame import Rect, Surface

from editor.pygame_components import LeftRightLayout, Button, Component, ComponentCollection


class Spacer(Component):
    def __init__(self, rect: Rect, margin: int = 4) -> None:
        super().__init__(rect)
        self.margin = margin
        self.spacer_rect = rect
        self.redefine_rect(rect)

    def redefine_rect(self, rect: Rect) -> None:
        self.rect = rect
        self.spacer_rect = rect.move(self.margin, 0)
        self.spacer_rect.width = 2
        self.spacer_rect.height -= 4
        self.spacer_rect.y += 2

    def draw(self, surface: Surface) -> None:
        pygame.draw.rect(surface, (128, 128, 128), self.spacer_rect)


class ToolbarPanel(ComponentCollection):
    def __init__(self, rect: Rect, icon_surface: Surface, margin: int = 0) -> None:
        super().__init__(rect)
        self.layout = LeftRightLayout()
        self.icon_surface = icon_surface
        self.margin = margin
        self.image_size = icon_surface.get_rect().height // 2
        self.rect.height = self.image_size + margin * 2
        self.icons_in_one_row = icon_surface.get_rect().width // self.image_size

    def add_button(self,
                   image_number: int,
                   disabled_image_number: Optional[int] = None,
                   callback: Optional[Callable[[], None]] = None) -> Button:
        if disabled_image_number is not None and disabled_image_number < 0:
            disabled_image_number = -disabled_image_number + self.icons_in_one_row
        button = Button(
            Rect(0, 0, self.image_size, self.image_size),
            self.icon_surface.subsurface(Rect(self.image_size * (image_number % self.icons_in_one_row), (image_number // self.icons_in_one_row) * self.image_size, self.image_size, self.image_size)),
            disabled_image=self.icon_surface.subsurface(Rect(self.image_size * (disabled_image_number % self.icons_in_one_row), (disabled_image_number // self.icons_in_one_row) * self.image_size, self.image_size, self.image_size)) if disabled_image_number is not None else None,
            callback=callback
        )
        self.components.append(button)
        self.relayout()
        return button

    def add_spacer(self) -> None:
        spacer = Spacer(Rect(0, 0, self.image_size // 4, self.image_size))
        self.components.append(spacer)
