from abc import ABC, abstractmethod
from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from engine.utils import clip

DEFAULT_SCROLLBAR_WIDTH = 15


class Component:
    def __init__(self, rect: Rect) -> None:
        self.rect = rect
        self._visible = True

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool) -> None:
        self._visible = visible

    def draw(self, surface: Surface) -> None:
        pass

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
        return False

    def mouse_in(self, x: int, y: int) -> bool:
        return False

    def mouse_out(self, x: int, y: int) -> bool:
        return False


class ComponentCollection(Component):
    def __init__(self, rect: Rect, *components: Component) -> None:
        super().__init__(rect)
        self.components: list[Component] = list(components)
        self.over_component = None
        self.mouse_pressed = False

    def draw(self, surface: Surface) -> None:
        for c in self.components:
            if c.visible:
                c.draw(surface)

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = False
        for c in self.components:
            if c.visible and c.rect.collidepoint(x, y):
                consumed = c.mouse_up(x, y, modifier)
                if consumed:
                    return True
        return False

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = True
        for c in self.components:
            if c.visible and c.rect.collidepoint(x, y):
                consumed = c.mouse_down(x, y, modifier)
                if consumed:
                    return True
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.mouse_pressed and self.over_component is not None:
            self.over_component.mouse_move(x, y, modifier)
        else:
            for c in self.components:
                if c.visible and c.rect.collidepoint(x, y):
                    if self.over_component is None:
                        self.over_component = c
                        c.mouse_in(x, y)
                    elif self.over_component != c:
                        self.over_component.mouse_out(x, y)
                        self.over_component = c
                        c.mouse_in(x, y)

                    consumed = c.mouse_move(x, y, modifier)
                    if consumed:
                        return True
                elif c == self.over_component:
                    c.mouse_out(x, y)
                    self.over_component = None
        return False

    def mouse_out(self, x: int, y: int) -> bool:
        if self.over_component:
            self.over_component.mouse_out(x, y)
            self.over_component = None
        return False

    def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
        for c in self.components:
            if c.visible and c.rect.collidepoint(x, y):
                consumed = c.mouse_wheel(x, y, dx, dy, modifier)
                if consumed:
                    return True
        return False


class Button(Component):
    def __init__(self,
                 rect: Rect,
                 image: Surface,
                 callback: Callable[[], None],
                 mouse_over_image: Optional[Surface] = None,
                 selected_image: Optional[Surface] = None,
                 mouse_over_color: Optional[tuple[int, int, int]] = (220, 220, 220),
                 selected_color: Optional[tuple[int, int, int]] = (128, 128, 128),
                 border_color: Optional[tuple[int, int, int]] = (0, 0, 0)
                 ) -> None:
        super().__init__(rect)
        self._image = image
        self._image_rect: Optional[Rect] = None
        self.image = image
        self.mouse_over_image = mouse_over_image
        self.selected_image = selected_image
        self.mouse_over_color = mouse_over_color
        self.border_color = border_color
        self.selected_color = selected_color
        self.callback = callback

        self._selected = False
        self.mouse_over = False
        self.mouse_pressed = False

    @property
    def image(self) -> Surface:
        return self._image

    @image.setter
    def image(self, image: Surface) -> None:
        self._image = image
        self._image_rect = image.get_rect().copy()
        self._image_rect.center = self.rect.center

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, selected: bool) -> None:
        self._selected = selected

    def draw(self, surface: Surface) -> None:
        if self.visible:
            if self.mouse_over:
                if self.mouse_over_color is not None:
                    pygame.draw.rect(surface, self.mouse_over_color, self.rect, border_radius=4)
                if self.mouse_over_image is not None:
                    surface.blit(self.mouse_over_image, self._image_rect)
                else:
                    surface.blit(self._image, self._image_rect)
                if self.border_color is not None:
                    pygame.draw.rect(surface, self.border_color, self.rect, border_radius=4, width=1)
            else:
                if self.selected:
                    if self.selected_color is not None:
                        pygame.draw.rect(surface, self.selected_color, self.rect, border_radius=4)
                    if self.selected_image is not None:
                        surface.blit(self.selected_image, self._image_rect)
                    else:
                        surface.blit(self._image, self._image_rect)
                else:
                    surface.blit(self._image, self._image_rect)

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        if self.rect.collidepoint(x, y):
            self.callback()
        return True

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = True
        return False

    def mouse_in(self, x: int, y: int) -> bool:
        self.mouse_over = True
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        self.mouse_over = False
        return True


class Scrollbar(Component):
    def __init__(self,
                 rect: Rect,
                 horizontal: bool,
                 allow_over: bool = True,
                 min_width: int = 50,
                 callback: Optional[Callable[[], None]] = None) -> None:
        super().__init__(rect)
        self.horizontal = horizontal
        self.allow_over = allow_over
        self.min_width = min_width
        self.bar_width = self.min_width
        self.callback = callback
        self.bar_screen_range = 0
        self._width = 100
        self._offset = 0
        self.bar_rect = rect.copy()
        self._recalculate_bar_rect()
        self.mouse_is_over = False
        self.mouse_pressed = False
        self.mouse_pressed_x = 0
        self.mouse_pressed_y = 0

    def _recalculate_bar_rect(self) -> None:
        if self.horizontal:
            self.bar_width = self.rect.width * (self.rect.width / self._width)
            if self.bar_width < self.min_width:
                self.bar_width = self.min_width
            if self.bar_width >= self.rect.width:
                self.bar_width = self.rect.width
            self.bar_screen_range = self.rect.width - (0 if self.allow_over else self.bar_width)
            scroll_range = self._width if self.allow_over else (self._width - self.rect.width)

            self.bar_rect.y = self.rect.y + 2
            self.bar_rect.height = self.rect.height - 4

            r = (((self.rect.width // 2) if self.allow_over else 0) - self._offset) / scroll_range
            x = int(r * self.bar_screen_range)
            self.bar_rect.x = self.rect.x + x - (self.bar_width // 2 if self.allow_over else 0)
            self.bar_rect.width = self.bar_width
        else:
            self.bar_width = self.rect.height * (self.rect.height / self._width)
            if self.bar_width < self.min_width:
                self.bar_width = self.min_width
            if self.bar_width >= self.rect.height:
                self.bar_width = self.rect.height
            self.bar_screen_range = self.rect.height - (0 if self.allow_over else self.bar_width)
            scroll_range = self._width if self.allow_over else (self._width - self.rect.height + self.bar_width)

            self.bar_rect.x = self.rect.x + 2
            self.bar_rect.width = self.rect.width - 4

            r = (((self.rect.height // 2) if self.allow_over else 0) - self._offset) / scroll_range
            y = int(r * self.bar_screen_range)
            self.bar_rect.y = self.rect.y + y - (self.bar_width // 2 if self.allow_over else 0)
            self.bar_rect.height = self.bar_width

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int) -> None:
        self._width = width
        self._recalculate_bar_rect()

    @property
    def offset(self) -> int:
        return self._offset

    @offset.setter
    def offset(self, o: int) -> None:
        v = self.rect.width if self.horizontal else self.rect.height
        if self.allow_over:
            if o <= -self._width + v // 2:
                o = -self._width + v // 2
            if o > v // 2:
                o = v // 2
        else:
            if o <= -self._width + v:
                o = -self._width + v
            if o > 0:
                o = 0

        value = int(o)
        if self._offset != value:
            self._offset = value
            if self.callback is not None:
                self.callback()
        self._recalculate_bar_rect()

    def draw(self, surface: Surface) -> None:
        with clip(surface, self.rect):
            pygame.draw.rect(surface, (200, 200, 200), self.rect)
            colour = (0, 0, 0) if self.mouse_is_over else (80, 80, 80)
            pygame.draw.rect(surface, colour, self.bar_rect, border_radius=4)

    def mouse_in(self, x: int, y: int) -> bool:
        self.mouse_is_over = True
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        self.mouse_is_over = False
        self.mouse_pressed = False
        return True

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        self.mouse_pressed = False
        return True

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        if self.bar_rect.collidepoint(x, y):
            self.mouse_pressed = True
            self.mouse_pressed_x = x
            self.mouse_pressed_y = y
        else:
            if self.horizontal:
                bar_representation = self._width * self.bar_rect.width / self.bar_screen_range
                if x > self.bar_rect.right:
                    self.offset -= bar_representation
                else:
                    self.offset += bar_representation
            else:
                bar_representation = self._width * self.bar_rect.height / self.bar_screen_range
                if y > self.bar_rect.bottom:
                    self.offset -= bar_representation
                else:
                    self.offset += bar_representation
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.mouse_pressed:
            if self.horizontal:
                dx = self.mouse_pressed_x - x
                self.offset += dx * self._width / self.bar_screen_range
                self.mouse_pressed_x = x
                self.mouse_pressed_y = y
            else:
                dy = self.mouse_pressed_y - y
                self.offset += dy * self._width / self.bar_screen_range
                self.mouse_pressed_x = x
                self.mouse_pressed_y = y
        return True


class ScrollableCanvas(ComponentCollection, ABC):
    def __init__(self,
                 rect: Rect,
                 scrollbar_width: int = DEFAULT_SCROLLBAR_WIDTH,
                 allow_over: bool = True) -> None:
        super().__init__(rect)
        self.scrollbar_width = scrollbar_width
        self.content_rect = rect.copy()
        self.content_rect.width -= scrollbar_width
        self.content_rect.height -= scrollbar_width

        r = rect.move(0, rect.height - scrollbar_width)
        r.width -= scrollbar_width
        r.height = scrollbar_width
        self.h_scrollbar = Scrollbar(r, True, allow_over=allow_over, callback=self.scrollbars_moved)

        r = rect.move(rect.width - scrollbar_width, 0)
        r.width = scrollbar_width
        r.height -= scrollbar_width
        self.v_scrollbar = Scrollbar(r, False, allow_over=allow_over, callback=self.scrollbars_moved)
        self.components += [self.h_scrollbar, self.v_scrollbar]

    def scrollbars_moved(self) -> None:
        pass

    def draw(self, surface: Surface) -> None:
        with clip(surface, self.rect):
            # if self.map_width > 0:
            surface.set_clip(self.content_rect)
            self._local_draw(surface)
        super().draw(surface)

    @abstractmethod
    def _local_draw(self, surface: Surface) -> None:
        pass

    def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
        consumed = super().mouse_wheel(x, y, dx, dy, modifier)
        if not consumed:
            self.h_scrollbar.offset -= dx
            self.v_scrollbar.offset += dy
        return True
