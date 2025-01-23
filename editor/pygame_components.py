from enum import Enum, auto

from abc import ABC, abstractmethod
from typing import Optional, Callable, NamedTuple

import pygame.draw
from pygame import Rect, Surface

from engine.utils import clip

DEFAULT_SCROLLBAR_WIDTH = 15


UISize = NamedTuple("UISize", [("width", int), ("height", int)])


class ALIGNMENT(Enum):
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()
    TOP = auto()
    MIDDLE = auto()
    BOTTOM = auto()


class Component:
    def __init__(self, rect: Rect) -> None:
        self.rect = rect
        self._visible = True

    def calculate_size(self) -> UISize:
        return self.rect.size

    def redefine_rect(self, rect: Rect) -> None:
        self.rect = rect
        self.relayout()

    def relayout(self) -> None:
        pass

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool) -> None:
        self._visible = visible

    def draw(self, surface: Surface) -> None:
        pass

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        return False

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        return False

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        return False

    def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
        return False

    def mouse_in(self, x: int, y: int) -> bool:
        return False

    def mouse_out(self, x: int, y: int) -> bool:
        return False


class BaseLayout:
    def __init__(self) -> None:
        pass

    def arrange(self, rect: Rect, components: list[Component]):
        for component in components:
            component.redefine_rect(rect)


class TopDownLayout(BaseLayout):
    def __init__(self, margin: int = 0, stretch: bool = False):
        super().__init__()
        self.margin = margin
        self.stretch = stretch

    def arrange(self, rect: Rect, components: list[Component]) -> None:
        y = rect.y
        for component in components:
            component_size = component.calculate_size()
            height = component_size.height
            # if component.rect is not None and component.rect.height != 0:
            #     height = component.rect.height
            # else:
            #     height = (rect.height - self.margin * (len(components) - 1)) // len(components)
            component.redefine_rect(Rect(rect.x, y, rect.width if self.stretch else component_size.width, height))
            y += self.margin + component.rect.height


class LeftRightLayout(BaseLayout):
    def __init__(self, margin: int = 0, h_alignment: ALIGNMENT = ALIGNMENT.LEFT):
        super().__init__()
        self.margin = margin
        self.h_alignment = h_alignment

    def arrange(self, rect: Rect, components: list[Component]) -> None:
        filled_in_space = False
        x = rect.x
        for component in components:
            if component.visible:
                if component.rect is not None and component.rect.width != 0:
                    width = component.rect.width
                else:
                    width = rect.width - self.margin * (len(components) - 1)
                    filled_in_space = True
                component.redefine_rect(Rect(x, rect.y, width, rect.height))
                x += self.margin + width
        if not filled_in_space and self.h_alignment != ALIGNMENT.LEFT:
            offset = 0
            if self.h_alignment == ALIGNMENT.RIGHT:
                offset = rect.width - (x - rect.x) - 1
            elif self.h_alignment == ALIGNMENT.CENTER:
                offset = (rect.width - (x - rect.x) - 1) // 2
            for component in components:
                if component.rect is not None:
                    component.rect.x = component.rect.x + offset


class ComponentCollection(Component):
    def __init__(self, rect: Rect, *components: Component) -> None:
        super().__init__(rect)
        self.layout: Optional[BaseLayout] = None
        self.components: list[Component] = list(components)
        self.over_component = None
        self.mouse_pressed = 0

    def calculate_size(self) -> UISize:
        if self.layout:
            self.layout.arrange(self.rect, self.components)

        max_width = 0
        max_height = 0

        for component in self.components:
            component_rect = component.rect
            if component_rect.right > max_width: max_width = component_rect.right
            if component_rect.bottom > max_height: max_height = component_rect.bottom

        return UISize(max_width - self.rect.x, max_height - self.rect.y)

    def redefine_rect(self, rect) -> None:
        self.rect = rect
        self.relayout()

    def relayout(self) -> None:
        self.rect.size = self.calculate_size()
        if self.layout is not None:
            self.layout.arrange(self.rect, self.components)
        else:
            for component in self.components:
                component.redefine_rect(self.rect)

    def draw(self, surface: Surface) -> None:
        for c in self.components:
            if c.visible:
                c.draw(surface)

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        self.mouse_pressed &= ~button
        if self.over_component is not None:
            self.over_component.mouse_up(x, y, button, modifier)
            if self.mouse_pressed == 0:
                self.over_component = None
        else:
            for c in self.components:
                if c.visible and c.rect.collidepoint(x, y):
                    consumed = c.mouse_up(x, y, button, modifier)
                    if consumed:
                        return True
        return False

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        self.mouse_pressed |= button
        if self.mouse_pressed != 0 and self.over_component is not None:
            self.over_component.mouse_down(x, y, button, modifier)
        else:
            for c in self.components:
                if c.visible and c.rect.collidepoint(x, y):
                    consumed = c.mouse_down(x, y, button, modifier)
                    if consumed:
                        return True
        return False

    def mouse_move(self, x: int, y: int, modifier: int) -> bool:
        if self.mouse_pressed != 0 and self.over_component is not None:
            # print(f"mouse_move: Handing over already selected component {type(self.over_component)}")
            return self.over_component.mouse_move(x, y, modifier)
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

                    # print(f"mouse_move: over component {type(self.over_component)}")
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
                 callback: Optional[Callable[[], None]] = None,
                 mouse_over_image: Optional[Surface] = None,
                 disabled_image: Optional[Surface] = None,
                 selected_image: Optional[Surface] = None,
                 mouse_over_color: Optional[tuple[int, int, int]] = (220, 220, 220),
                 selected_color: Optional[tuple[int, int, int]] = (128, 128, 128),
                 border_color: Optional[tuple[int, int, int]] = (0, 0, 0)
                 ) -> None:
        super().__init__(rect)
        self._image = image
        self._image_rect: Optional[Rect] = None
        self.image = image
        self.disabled = False
        self.mouse_over_image = mouse_over_image
        self.disabled_image = disabled_image
        self.selected_image = selected_image
        self.mouse_over_color = mouse_over_color
        self.border_color = border_color
        self.selected_color = selected_color
        self.callback = callback

        self._selected = False
        self.mouse_over = False
        self.mouse_pressed = False

    def redefine_rect(self, rect):
        self.rect = rect
        self._image_rect = self._image.get_rect().copy()
        self._image_rect.center = self.rect.center

    @property
    def image(self) -> Surface:
        return self._image

    @image.setter
    def image(self, image: Surface) -> None:
        self._image = image
        self.redefine_rect(self.rect)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, selected: bool) -> None:
        self._selected = selected

    def draw(self, surface: Surface) -> None:
        if self.visible:
            if self.disabled:
                if self.disabled_image is not None:
                    surface.blit(self.disabled_image, self._image_rect)
            elif self.mouse_over:
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

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            if self.rect.collidepoint(x, y) and self.callback is not None:
                self.callback()
        return True

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
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
                 callback: Optional[Callable[[int], None]] = None) -> None:
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

    def redefine_rect(self, rect: Rect) -> None:
        super().redefine_rect(rect)
        self._recalculate_bar_rect()

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

            if scroll_range != 0:
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

            if scroll_range != 0:
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
            diff = value - self._offset
            self._offset = value
            if self.callback is not None:
                self.callback(diff)
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

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_pressed = False
        return True

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
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
        self.h_scrollbar = Scrollbar(r, True, allow_over=allow_over, callback=self._scrollbar_h_moved)

        r = rect.move(rect.width - scrollbar_width, 0)
        r.width = scrollbar_width
        r.height -= scrollbar_width
        self.v_scrollbar = Scrollbar(r, False, allow_over=allow_over, callback=self._scrollbar_v_moved)
        self.components += [self.h_scrollbar, self.v_scrollbar]

    def _scrollbar_h_moved(self, diff: int) -> None:
        self.scrollbars_moved(diff, 0)

    def _scrollbar_v_moved(self, diff: int) -> None:
        self.scrollbars_moved(0, diff)

    def scrollbars_moved(self, dx: int, dy: int) -> None:
        pass

    def relayout(self) -> None:
        self.content_rect.update(self.rect)
        self.content_rect.width -= self.scrollbar_width
        self.content_rect.height -= self.scrollbar_width

        r = self.rect.move(0, self.rect.height - self.scrollbar_width)
        r.width -= self.scrollbar_width
        r.height = self.scrollbar_width
        self.h_scrollbar.redefine_rect(r)

        r = self.rect.move(self.rect.width - self.scrollbar_width, 0)
        r.width = self.scrollbar_width
        r.height -= self.scrollbar_width
        self.v_scrollbar.redefine_rect(r)

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


class Divider(Component):
    def __init__(self,
                 rect: Rect,
                 horizontal: bool,
                 parent: Component,
                 min_left_top: int = 100,
                 min_right_bottom: int = 100) -> None:
        super().__init__(rect)
        self.horizontal = horizontal
        self.parent = parent
        self.min_right_bottom = min_right_bottom
        self.min_left_top = min_left_top
        self.spacer_rect = Rect(rect.x, rect.y, rect.width, rect.height)
        self.redefine_rect(rect)
        self.mouse_is_down = False
        self.mouse_x = 0
        self.mouse_y = 0

    def redefine_rect(self, rect: Rect) -> None:
        super().redefine_rect(rect)
        if self.horizontal:
            self.spacer_rect.update(rect.x + rect.width // 50, rect.y + rect.width // 2 - 1, rect.width * 48 // 50, 2)
        else:
            self.spacer_rect.update(rect.x + rect.width // 2 - 1, rect.y + rect.height // 50, 2, rect.height * 48 // 50)

    def draw(self, surface: Surface) -> None:
        pygame.draw.rect(surface, (128, 128, 128), self.spacer_rect)

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
        if self.horizontal:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENS)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)

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
            if self.horizontal:
                dx = 0
                dy = y - self.mouse_y
                if self.rect.y + dy < self.parent.rect.y + self.min_left_top:
                    dy = 0
                if self.rect.y + dy > self.parent.rect.bottom - self.min_right_bottom:
                    dy = 0
            else:
                dy = 0
                dx = x - self.mouse_x
                if self.rect.x + dx < self.parent.rect.x + self.min_left_top:
                    dx = 0
                if self.rect.x + dx > self.parent.rect.right - self.min_right_bottom:
                    dx = 0

            self.rect.move_ip(dx, dy)
            self.redefine_rect(self.rect)
            self.parent.relayout()

            self.mouse_x = x
            self.mouse_y = y
            return True
        return False
