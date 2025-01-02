import enum
import os
from abc import ABC
from typing import Optional, Callable, cast

import pygame.draw
from pygame import Rect, Surface
from pygame.font import Font

from editor.pygame_components import ScrollableCanvas, ComponentCollection, Button
from editor.tileset_canvas import TilesetCanvas
from engine.tmx import TiledMap, BaseTiledLayer, TiledTileLayer, TiledObjectGroup, TiledObject


class MapAction(enum.Enum):
    SELECT = enum.auto()
    BRUSH = enum.auto()
    RUBBER = enum.auto()


class MapActionsPanel(ComponentCollection):
    def __init__(self,
                 rect: Rect,
                 action_selected_callback: Optional[Callable[[MapAction], None]] = None,
                 margin: int = 3) -> None:
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
            Rect(rect.x + (image_size + self.margin) + self. margin, self.margin, image_size, image_size),
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


class MouseAdapter(ABC):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        self.map_canvas = map_canvas

    def mouse_up(self, _x: int, _y: int, _modifier: int) -> bool:
        return False

    def mouse_down(self, _x: int, _y: int, _modifier: int) -> bool:
        return False

    def mouse_move(self, _x: int, _y: int, _modifier: int) -> bool:
        return False


class NullMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)


class SelectTileMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return False


class SelectObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return False


class BrushObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return True


class BrushTileMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)
        self.mouse_is_down = False
        self.last_tile_x = -1
        self.last_tile_y = -1

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        self.mouse_is_down = False
        return False

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_down(x, y, modifier):
            self.mouse_is_down = True
            tilemap = self.map_canvas.tiled_map
            if tilemap is not None and self.map_canvas.tileset_canvas.selected_tile is not None:
                self.last_tile_x, self.last_tile_y = self.map_canvas.calc_mouse_to_tile(x, y)
                cast(TiledTileLayer, self.map_canvas.selected_layer).data[self.last_tile_y][self.last_tile_x] = self.map_canvas.tileset_canvas.selected_tile
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.mouse_is_down:
            tilemap = self.map_canvas.tiled_map
            if tilemap is not None and self.map_canvas.tileset_canvas.selected_tile is not None:
                tile_x, tile_y = self.map_canvas.calc_mouse_to_tile(x, y)
                if tile_x != self.last_tile_x or tile_y != self.last_tile_y:
                    cast(TiledTileLayer, self.map_canvas.selected_layer).data[tile_y][tile_x] = self.map_canvas.tileset_canvas.selected_tile
                    self.last_tile_x = tile_x
                    self.last_tile_y = tile_y

        self.map_canvas.calc_mouse_over_rect(x, y)
        return True


class RubberTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)


class MapCanvas(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 font: Font,
                 map_actions_panel: MapActionsPanel,
                 tileset_canvas: TilesetCanvas) -> None:
        super().__init__(rect)
        self.font = font
        self._selected_layer: Optional[BaseTiledLayer] = None

        self._null_mouse_adapter = NullMouseAdapter(self)

        self._select_object_mouse_adapter = SelectObjectMouseAdapter(self)
        self._brush_object_mouse_adapter = BrushObjectMouseAdapter(self)

        self._select_tile_mouse_adapter = SelectTileMouseAdapter(self)
        self._brush_tile_mouse_adapter = BrushTileMouseAdapter(self)
        self._rubber_tile_mouse_adapter = RubberTileMouseAdapter(self)
        self._mouse_adater = self._null_mouse_adapter

        self._tiled_map = None
        self.tileset_canvas = tileset_canvas
        self.map_actions_panel = map_actions_panel
        self.map_actions_panel.action_selected_callback = self._action_changed
        self._action = MapAction.SELECT
        self._action_changed(map_actions_panel.action)
        self.mouse_over_rect: Optional[Rect] = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.overlay_surface: Optional[Surface] = None

        self.v_scrollbar.visible = False
        self.h_scrollbar.visible = False

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

    @property
    def selected_layer(self) -> Optional[BaseTiledLayer]:
        return self._selected_layer

    @selected_layer.setter
    def selected_layer(self, layer: Optional[BaseTiledLayer]) -> None:
        self._selected_layer = layer
        if layer is not None and isinstance(layer, TiledTileLayer):
            self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
        else:
            self.mouse_over_rect = None
        self._action_changed(self._action)

    def tile_selection_changed(self) -> None:
        if self.tileset_canvas.selected_tile is not None:
            tileset = self.tileset_canvas.tileset
            self.overlay_surface = Surface((tileset.tilewidth, tileset.tileheight), pygame.SRCALPHA, 32)
            self.overlay_surface.blit(self.tiled_map.images[self.tileset_canvas.selected_tile], (0, 0))
            # self.overlay_surface.fill((255, 255, 0, 64))
            self.overlay_surface.set_alpha(128)
            self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
        else:
            self.mouse_over_rect = None
            self.overlay_surface = None

    def _action_changed(self, action: MapAction) -> None:
        self._action = action
        if self._selected_layer is not None:
            if isinstance(self._selected_layer, TiledTileLayer):
                if action == MapAction.SELECT:
                    self._mouse_adater = self._select_tile_mouse_adapter
                elif action == MapAction.BRUSH:
                    self._mouse_adater = self._brush_tile_mouse_adapter
                elif action == MapAction.RUBBER:
                    self._mouse_adater = self._rubber_tile_mouse_adapter
                else:
                    self._mouse_adater = self._null_mouse_adapter
            else:
                if action == MapAction.SELECT:
                    self._mouse_adater = self._select_object_mouse_adapter
                elif action == MapAction.BRUSH:
                    self._mouse_adater = self._brush_object_mouse_adapter
                else:
                    self._mouse_adater = self._null_mouse_adapter
        else:
            self._mouse_adater = self._null_mouse_adapter

    def _calculate_new_obj_text(self, obj: TiledObject, x_offset, y_offset) -> None:
        text_white = self.font.render(obj.name, True, (255, 255, 255))
        # text_white = self.font.render(obj.name, False, (255, 255, 255))
        text_black = self.font.render(obj.name, False, (0, 0, 0))
        surface = Surface((text_white.get_size()[0] + 4, text_white.get_size()[1] + 5), pygame.SRCALPHA, 32)
        r = surface.get_rect().inflate(-1, -1)
        r.update(1, 1, r.width, r.height)
        pygame.draw.rect(surface, (0, 0, 0), r, border_radius=4)
        r.update(0, 0, r.width, r.height)
        pygame.draw.rect(surface, (128, 128, 128), r, border_radius=4)
        r.update(3, 2, r.width, r.height)
        surface.blit(text_black, r)
        r.update(2, 1, r.width, r.height)
        surface.blit(text_white, r)
        obj.properties["_text_surface"] = surface
        obj.properties["_old_rect"] = obj.rect.copy()
        obj.properties["_old_name"] = obj.name
        obj.properties["_old_x_offset"] = x_offset
        obj.properties["_old_y_offset"] = y_offset
        r.center = obj.rect.center
        r.move_ip(x_offset, y_offset)
        r.move_ip(0, -obj.rect.height / 2 - r.height / 2 - 4)
        obj.properties["_text_position"] = r

    def _draw_object_layer(self, layer: TiledObjectGroup, surface: Surface, rect: Rect, x_offset: int, y_offset: int) -> None:
        for obj in layer.objects:
            if obj.visible:
                if ("_old_rect" not in obj.properties
                        or obj.properties["_old_rect"] != obj.rect
                        or obj.properties["_old_name"] != obj.name):
                    self._calculate_new_obj_text(obj, rect.x + x_offset, rect.y + y_offset)
                if obj.properties["_old_x_offset"] != x_offset or obj.properties["_old_y_offset"] != y_offset:
                    dx = x_offset - obj.properties["_old_x_offset"]
                    dy = y_offset - obj.properties["_old_y_offset"]
                    obj.properties["_old_x_offset"] = x_offset
                    obj.properties["_old_y_offset"] = y_offset
                    obj.properties["_text_position"].move_ip(dx, dy)

                surface.blit(obj.properties["_text_surface"], obj.properties["_text_position"])
                if obj.image:
                    surface.blit(obj.image, (self.rect.x + obj.x + x_offset, self.rect.y + obj.y + y_offset))
                else:
                    r = obj.rect.move(rect.x + x_offset + 1, rect.y + y_offset + 1)
                    pygame.draw.rect(surface, (0, 0, 0), r, width=1)
                    r.move_ip(-1, -1)
                    pygame.draw.rect(surface, (128, 128, 128), r, width=1)

    def _local_draw(self, surface: Surface) -> None:
        if self._tiled_map is not None:
            colour = self._tiled_map.backgroundcolor if self._tiled_map.backgroundcolor else (0, 0, 0)
            pygame.draw.rect(surface, colour, self.rect)
            for layer in self._tiled_map.layers:
                if layer.visible:
                    if isinstance(layer, TiledObjectGroup):
                        self._draw_object_layer(layer, surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)
                    else:
                        layer.draw(surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)

            if self.mouse_over_rect is not None:
                surface.blit(self.overlay_surface, self.mouse_over_rect)
                pygame.draw.rect(surface, (255, 255, 255), self.mouse_over_rect, width=1)

    def scrollbars_moved(self) -> None:
        self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)

    def calc_mouse_to_tile(self, x: int, y: int) -> tuple[int, int]:
        self.mouse_x = x
        self.mouse_y = y
        tilemap = self.tiled_map
        tile_x = ((x - self.h_scrollbar.offset) // tilemap.tilewidth)
        tile_y = ((y - self.v_scrollbar.offset) // tilemap.tileheight)
        return tile_x, tile_y

    def calc_mouse_over_rect(self, x: int, y: int) -> None:
        if self.overlay_surface is None or self._selected_layer is None or not isinstance(self._selected_layer, TiledTileLayer) or self._action == MapAction.SELECT:
            self.mouse_over_rect = None
            return

        tilemap = self.tiled_map
        tile_x, tile_y = self.calc_mouse_to_tile(x, y)
        if 0 <= tile_x < tilemap.width and 0 <= tile_y < tilemap.height:
            x = tile_x * tilemap.tilewidth + self.h_scrollbar.offset
            y = tile_y * tilemap.tileheight + self.v_scrollbar.offset
            self.mouse_over_rect = Rect(x, y, tilemap.tilewidth, tilemap.tileheight)
        else:
            self.mouse_over_rect = None

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_up(x, y, modifier):
            return self._mouse_adater.mouse_up(x, y, modifier)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_down(x, y, modifier):
            return self._mouse_adater.mouse_down(x, y, modifier)

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_move(x, y, modifier):
            return self._mouse_adater.mouse_move(x, y, modifier)

    def mouse_in(self, x: int, y: int) -> bool:
        if not super().mouse_in(x, y):
            self.calc_mouse_over_rect(x, y)
        return True
