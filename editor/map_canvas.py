import enum
import os
from typing import Optional, Callable

import pygame.draw
from pygame import Rect, Surface

from editor.pygame_components import ScrollableCanvas, ComponentCollection, Button
from engine.tmx import TiledMap


class MapAction(enum.Enum):
    SELECT = enum.auto()
    BRUSH = enum.auto()
    RUBBER = enum.auto()


class MapActionsPanel(ComponentCollection):
    def __init__(self, rect: Rect, action_selected_callback: Optional[Callable[[MapAction], None]] = None, margin: int = 3) -> None:
        super().__init__(rect)

        self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "icons-small.png"))

        image_size = self.icon_surface.get_rect().height
        self.margin = margin

        self.select_button = Button(
            Rect(rect.x + self.margin, self.margin, image_size, image_size),
            self.icon_surface.subsurface(Rect(image_size * 7, 0, image_size, image_size)),
            lambda: self._select_action(MapAction.SELECT)
        )
        self.brush_button = Button(
            Rect(rect.x + (image_size + self.margin) +self. margin, self.margin, image_size, image_size),
            self.icon_surface.subsurface(Rect(0, 0, image_size, image_size)),
            lambda: self._select_action(MapAction.BRUSH)
        )
        self.rubber_button = Button(
            Rect(rect.x + (image_size + self.margin) * 2 + self.margin, self.margin, image_size, image_size),
            self.icon_surface.subsurface(Rect(image_size, 0, image_size, image_size)),
            lambda: self._select_action(MapAction.RUBBER)
        )
        self.components.append(self.select_button)
        self.components.append(self.brush_button)
        self.components.append(self.rubber_button)
        self._action = MapAction.BRUSH
        self.action_selected_callback = action_selected_callback

    def _select_action(self, action: MapAction) -> None:
        self.action = action

    @property
    def action(self) -> MapAction:
        return self._action

    @action.setter
    def action(self, action: MapAction) -> None:
        self._action = action
        self.select_button.selected = action == MapAction.SELECT
        self.brush_button.selected = action == MapAction.BRUSH
        self.rubber_button.selected = action == MapAction.RUBBER
        if self.action_selected_callback is not None:
            self.action_selected_callback(action)


class MapCanvas(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 tiled_map: Optional[TiledMap],
                 mouse_down_callback: Callable[[int, int, int, int], None]) -> None:
        super().__init__(rect)
        self._tiled_map = tiled_map
        self.h_scrollbar.visible = tiled_map is not None
        self.v_scrollbar.visible = tiled_map is not None
        self.mouse_over_rect: Optional[Rect] = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.overlay_surface: Optional[Surface] = None
        self.mouse_over_allowed = False
        self.mouse_down_callback = mouse_down_callback

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
            self.overlay_surface = Surface((tiled_map.tilewidth, tiled_map.tileheight), pygame.SRCALPHA, 32)
            self.overlay_surface.fill((255, 255, 0, 64))
            # self.overlay_surface.set_alpha(128)

    def _local_draw(self, surface: Surface) -> None:
        if self._tiled_map is not None:
            colour = self._tiled_map.backgroundcolor if self._tiled_map.backgroundcolor else (0, 0, 0)
            pygame.draw.rect(surface, colour, self.rect)
            for layer in self._tiled_map.layers:
                if layer.visible:
                    layer.draw(surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)

            if self.mouse_over_allowed and self.mouse_over_rect is not None:
                surface.blit(self.overlay_surface, self.mouse_over_rect)
                pygame.draw.rect(surface, (255, 255, 255), self.mouse_over_rect, width=1)

    def scrollbars_moved(self) -> None:
        self._calc_mouse_over_rect(self.mouse_x, self.mouse_y)

    def _calc_mouse_to_tile(self, x: int, y: int) -> tuple[int, int]:
        self.mouse_x = x
        self.mouse_y = y
        tilemap = self.tiled_map
        tile_x = ((x - self.h_scrollbar.offset) // tilemap.tilewidth)
        tile_y = ((y - self.v_scrollbar.offset) // tilemap.tileheight)
        return tile_x, tile_y

    def _calc_mouse_over_rect(self, x: int, y: int) -> None:
        tilemap = self.tiled_map
        tile_x, tile_y = self._calc_mouse_to_tile(x, y)
        if 0 <= tile_x < tilemap.width and 0 <= tile_y < tilemap.height:
            x = tile_x * tilemap.tilewidth + self.h_scrollbar.offset
            y = tile_y * tilemap.tileheight + self.v_scrollbar.offset
            self.mouse_over_rect = Rect(x, y, tilemap.tilewidth, tilemap.tileheight)
        else:
            self.mouse_over_rect = None

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        tile_x, tile_y = self._calc_mouse_to_tile(x, y)
        self.mouse_down_callback(x, y, tile_x, tile_y)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        self._calc_mouse_over_rect(x, y)
        return True

    # def mouse_wheel(self, x: int, y: int, dx: int, dy: int, modifier) -> bool:
    #     return False

    def mouse_in(self, x: int, y: int) -> bool:
        self._calc_mouse_over_rect(x, y)
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        self.mouse_over_rect = None
        return True
