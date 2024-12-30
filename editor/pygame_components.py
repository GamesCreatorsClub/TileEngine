from abc import ABC, abstractmethod
from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from engine.tmx import TiledMap, TiledTileset
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
    def __init__(self, rect: Rect, image: Surface, callback: Callable[[], None]) -> None:
        super().__init__(rect)
        self._image = image
        self._image_rect: Optional[Rect] = None
        self.image = image
        self._selected = False
        self.mouse_over = False
        self.mouse_pressed = False
        self.mouse_over_color = (220, 220, 220)
        self.border_color = (0, 0, 0)
        self.selected_color = (128, 128, 128)
        self.callback = callback

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
                pygame.draw.rect(surface, self.mouse_over_color, self.rect, border_radius=4)
                pygame.draw.rect(surface, self.border_color, self.rect, border_radius=4, width=1)
            else:
                if self.selected:
                    pygame.draw.rect(surface, self.selected_color, self.rect, border_radius=4)
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
        return False


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
            surface.set_clip(self.rect)
            # if self.map_width > 0:
            super().draw(surface)
            surface.set_clip(self.content_rect)
            self._local_draw(surface)

    @abstractmethod
    def _local_draw(self, surface: Surface) -> None:
        pass

    def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
        consumed = super().mouse_wheel(x, y, dx, dy, modifier)
        if not consumed:
            self.h_scrollbar.offset -= dx
            self.v_scrollbar.offset += dy
        return True


class MapCanvas(ScrollableCanvas):
    def __init__(self, rect: Rect, tiled_map: Optional[TiledMap]) -> None:
        super().__init__(rect)
        self._tiled_map = tiled_map
        self.h_scrollbar.visible = tiled_map is not None
        self.v_scrollbar.visible = tiled_map is not None

    @property
    def tiled_map(self) -> TiledMap:
        return self._tiled_map

    @tiled_map.setter
    def tiled_map(self, tiled_map: TiledMap) -> None:
        self._tiled_map = tiled_map
        if tiled_map is None:
            self.v_scrollbar.visible = False
            self.h_scrollbar.visible = False
        else:
            self.v_scrollbar.visible = True
            self.h_scrollbar.visible = True
            self.h_scrollbar.width = tiled_map.width * tiled_map.tilewidth
            self.v_scrollbar.width = tiled_map.height * tiled_map.tileheight

    def _local_draw(self, surface: Surface) -> None:
        if self._tiled_map is not None:
            colour = self._tiled_map.backgroundcolor if self._tiled_map.backgroundcolor else (0, 0, 0)
            pygame.draw.rect(surface, colour, self.rect)
            for layer in self._tiled_map.layers:
                if layer.visible:
                    layer.draw(surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)
        #
        # text = self.font.render(f"{self.h_scrollbar.offset}x{self.v_scrollbar.offset}", True, (127, 127, 0))
        # surface.blit(text, self.rect.topleft)


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
