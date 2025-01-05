import enum
import os
from abc import ABC
from typing import Optional, Callable, cast

import pygame.draw
from pygame import Rect, Surface
from pygame.font import Font

from editor.pygame_components import ScrollableCanvas, ComponentCollection, Button
from editor.resize_component import ResizeButton, ResizePosition
from editor.tileset_canvas import TilesetCanvas
from engine.tmx import TiledMap, BaseTiledLayer, TiledTileLayer, TiledObjectGroup, TiledObject
from engine.utils import clip

SCROLLING_MARGIN = 10
SCROLLING_STEP = 10


class MapAction(enum.Enum):
    SELECT_OBJECT = (True,)
    ADD_IMAGE_OBJECT = (True,)
    ADD_AREA_OBJECT = (True,)

    SELECT_TILE = (False,)
    BRUSH_TILE = (False,)
    RANDOM_BRUSH_TILE = (False,)
    RUBBER_TILE = (False,)

    def __new__(cls, object_layer: bool):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    def __init__(self, object_layer: bool) -> None:
        self.object_layer = object_layer


class MapActionsPanel(ComponentCollection):
    def __init__(self,
                 rect: Rect,
                 action_selected_callback: Optional[Callable[[MapAction], None]] = None,
                 margin: int = 3) -> None:
        super().__init__(rect)
        self._object_layer = False

        self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "icons-small.png"))

        image_size = self.icon_surface.get_rect().height
        self.margin = margin

        def button(pos: int, img: int, callback: Callable[[], None]) -> Button:
            return Button(
                Rect(rect.x + (image_size + self.margin) * pos + self.margin, self.margin, image_size, image_size),
                self.icon_surface.subsurface(Rect(image_size * img, 0, image_size, image_size)),
                callback
            )

        self.object_buttons = {
            MapAction.SELECT_OBJECT: button(0, 7, lambda: self._select_action(MapAction.SELECT_OBJECT)),
            MapAction.ADD_IMAGE_OBJECT: button(1, 0, lambda: self._select_action(MapAction.ADD_IMAGE_OBJECT)),
            MapAction.ADD_AREA_OBJECT: button(2, 3, lambda: self._select_action(MapAction.ADD_AREA_OBJECT)),
        }
        self.tile_buttons = {
            MapAction.SELECT_TILE: button(0, 7, lambda: self._select_action(MapAction.SELECT_TILE)),
            MapAction.BRUSH_TILE: button(1, 0, lambda: self._select_action(MapAction.BRUSH_TILE)),
            MapAction.RANDOM_BRUSH_TILE: button(2, 8, lambda: self._select_action(MapAction.RANDOM_BRUSH_TILE)),
            MapAction.RUBBER_TILE: button(3, 1, lambda: self._select_action(MapAction.RUBBER_TILE))
        }
        self.components.extend(self.object_buttons.values())
        self.components.extend(self.tile_buttons.values())

        self._action = MapAction.BRUSH_TILE
        self.action_selected_callback = action_selected_callback
        self.action = MapAction.BRUSH_TILE

    def _select_action(self, action: MapAction) -> None:
        self.action = action

    @property
    def object_layer(self) -> bool:
        return self._object_layer

    @object_layer.setter
    def object_layer(self, object_layer: bool) -> None:
        self._object_layer = object_layer
        for b in self.object_buttons.values():
            b.visible = object_layer

        for b in self.tile_buttons.values():
            b.visible = not object_layer

        if self._action.object_layer != object_layer:
            if object_layer:
                self.action = MapAction.SELECT_OBJECT
            else:
                self.action = MapAction.SELECT_TILE

    @property
    def action(self) -> MapAction:
        return self._action

    @action.setter
    def action(self, action: MapAction) -> None:
        self._action = action
        if self._object_layer:
            for k, v in self.object_buttons.items():
                v.selected = k == action
        else:
            for k, v in self.tile_buttons.items():
                v.selected = k == action

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

    def mouse_out(self, _x: int, _y: int) -> bool:
        return False

    def selected(self) -> None:
        pass

    def deselected(self) -> None:
        pass


class NullMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)


class SelectObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas',
                 scrolling_margin: int = SCROLLING_MARGIN,
                 scrolling_step: int = SCROLLING_STEP) -> None:
        super().__init__(map_canvas)
        self.scrolling_margin = scrolling_margin
        self.scrolling_step = scrolling_step
        self.selected_object: Optional[TiledObject] = None
        self.mouse_is_down = False
        self.touch_x = 0
        self.touch_y = 0
        self.viewport = Rect(
            -self.map_canvas.h_scrollbar.offset,
            -self.map_canvas.v_scrollbar.offset,
            self.map_canvas.rect.width - self.map_canvas.v_scrollbar.rect.width,
            self.map_canvas.rect.height - self.map_canvas.h_scrollbar.rect.height)

    def selected(self) -> None:
        pass

    def deselected(self) -> None:
        self.hide_buttons()

    def hide_buttons(self) -> None:
        for b in self.map_canvas.arrow_buttons:
            b.visible = False

    def update_buttons(self) -> None:
        if self.selected_object is not None:
            r = self.selected_object.rect.move(self.map_canvas.rect.x + self.map_canvas.h_scrollbar.offset, self.map_canvas.rect.y + self.map_canvas.v_scrollbar.offset)

            for b in self.map_canvas.arrow_buttons:
                b.update_rect(r)
                b.visible = True

    def movement_callback(self, button: ResizeButton, distance_x: int, distance_y: int) -> None:
        if self.selected_object is not None:
            rect = self.selected_object.rect
            pos = button.position
            dx = pos.dx
            dy = pos.dy

            if dx < 0:
                rect.x += dx * distance_x
            rect.width += abs(dx) * distance_x

            if dy < 0:
                rect.y += dy * distance_y
            rect.height += abs(dy) * distance_y

            self.update_buttons()

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        def find_object(layer: TiledObjectGroup, x: int, y: int) -> Optional[TiledObject]:
            for o in layer.objects_id_map.values():
                if o.visible and o.rect.collidepoint(x, y):
                    return o
            return None

        tiled_map = self.map_canvas.tiled_map
        if tiled_map is not None:
            layer = cast(TiledObjectGroup, self.map_canvas.selected_layer)

            corrected_x = x - self.map_canvas.rect.x - self.map_canvas.h_scrollbar.offset
            corrected_y = y - self.map_canvas.rect.y - self.map_canvas.v_scrollbar.offset

            obj = find_object(layer, corrected_x, corrected_y)
            if obj is not None:
                self.mouse_is_down = True
                self.selected_object = obj
                self.map_canvas.object_selected_callback(obj)
                self.touch_x = x
                self.touch_y = y
                if obj.image is None:
                    self.update_buttons()
            else:
                self.selected_object = None
                self.hide_buttons()
        else:
            self.selected_object = None
            self.hide_buttons()

        return False

    def mouse_up(self, x: int, y: int, modifier) -> bool:
        self.mouse_is_down = False
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.selected_object is not None and self.mouse_is_down and self.viewport.collidepoint(x, y):
            dx = x - self.touch_x
            dy = y - self.touch_y
            if dx == 0 and dy == 0:
                if x <= self.scrolling_margin:
                    dx = -self.scrolling_step
                    self.map_canvas.h_scrollbar.offset += self.scrolling_step
                elif x >= self.viewport.right - self.scrolling_margin:
                    dx = +self.scrolling_step
                    self.map_canvas.h_scrollbar.offset -= self.scrolling_step
                if y <= self.scrolling_margin:
                    dy = -self.scrolling_step
                    self.map_canvas.v_scrollbar.offset += self.scrolling_step
                elif y >= self.viewport.bottom - self.scrolling_margin:
                    dy = self.scrolling_step
                    self.map_canvas.v_scrollbar.offset -= self.scrolling_step

                self.selected_object.x += dx
                self.selected_object.y += dy
            else:
                self.selected_object.x += dx
                self.selected_object.y += dy

                self.touch_x = x
                self.touch_y = y
                self.map_canvas.object_selected_callback(self.selected_object)
                if self.selected_object.image is None:
                    self.update_buttons()

        return True

    def mouse_out(self, x: int, y: int) -> bool:
        self.mouse_is_down = False
        return False


class AddImageObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        tilemap = self.map_canvas.tiled_map
        if tilemap is not None and self.map_canvas.tileset_canvas.selected_tile is not None:
            layer = cast(TiledObjectGroup, self.map_canvas.selected_layer)

            obj = TiledObject(layer)
            obj.id = max(map(lambda o: o.id, layer.objects_id_map.values())) + 1
            obj.gid = self.map_canvas.tileset_canvas.selected_tile
            img = tilemap.images[obj.gid]
            obj.rect = img.get_rect()
            obj.rect.center = x, y
            layer.objects_id_map[obj.id] = obj
            self.map_canvas.object_added_callback(layer, obj)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return True


class AddAreaObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        tilemap = self.map_canvas.tiled_map
        if tilemap is not None and self.map_canvas.tileset_canvas.selected_tile is not None:
            layer = cast(TiledObjectGroup, self.map_canvas.selected_layer)

            obj = TiledObject(layer)
            obj.id = len(layer.objects_id_map)
            obj.gid = 0
            obj.rect = Rect(x, y, 32, 32)
            layer.objects_id_map[obj.id] = obj
            self.map_canvas.object_added_callback(layer, obj)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return True


class SelectTileMouseAdapter(MouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return False


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


class RandomBrushTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)


class RubberTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_canvas: 'MapCanvas') -> None:
        super().__init__(map_canvas)


class MapCanvas(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 font: Font,
                 map_actions_panel: MapActionsPanel,
                 tileset_canvas: TilesetCanvas,
                 object_added_callback: Callable[[TiledObjectGroup, TiledObject], None],
                 object_selected_callback: Callable[[TiledObject], None]) -> None:
        super().__init__(rect)
        self.font = font

        self.arrows_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "arrows-small.png"))

        self._selected_layer: Optional[BaseTiledLayer] = None
        self.object_added_callback = object_added_callback
        self.object_selected_callback = object_selected_callback

        self._null_mouse_adapter = NullMouseAdapter(self)

        self._mouse_object_adapters = {
            MapAction.SELECT_OBJECT: SelectObjectMouseAdapter(self),
            MapAction.ADD_IMAGE_OBJECT: AddImageObjectMouseAdapter(self),
            MapAction.ADD_AREA_OBJECT: AddAreaObjectMouseAdapter(self),
        }
        self._mouse_tile_adapters = {
            MapAction.SELECT_TILE: SelectTileMouseAdapter(self),
            MapAction.BRUSH_TILE: BrushTileMouseAdapter(self),
            MapAction.RANDOM_BRUSH_TILE: RandomBrushTileMouseAdapter(self),
            MapAction.RUBBER_TILE: RubberTileMouseAdapter(self)
        }
        self._mouse_adapter = self._null_mouse_adapter

        arrow_image_size = self.arrows_surface.get_size()[1]

        def size_button(img: int, sel_img: int, position: ResizePosition) -> ResizeButton:
            button = ResizeButton(
                position,
                Rect(0, 0, arrow_image_size, arrow_image_size),
                self.arrows_surface.subsurface(Rect(arrow_image_size * img, 0, arrow_image_size, arrow_image_size)),
                cast(SelectObjectMouseAdapter, self._mouse_object_adapters[MapAction.SELECT_OBJECT]).movement_callback,
                mouse_over_image=self.arrows_surface.subsurface(Rect(arrow_image_size * sel_img, 0, arrow_image_size, arrow_image_size)),
            )
            button.visible = False
            return button

        self.arrow_buttons = [
            size_button(0, 2, ResizePosition.W),
            size_button(5, 7, ResizePosition.SW),
            size_button(1, 3, ResizePosition.S),
            size_button(4, 6, ResizePosition.SE),
            size_button(0, 2, ResizePosition.E),
            size_button(5, 7, ResizePosition.NE),
            size_button(1, 3, ResizePosition.N),
            size_button(4, 6, ResizePosition.NW)
        ]
        self.components.extend(self.arrow_buttons)

        self._tiled_map = None
        self.tileset_canvas = tileset_canvas
        self.map_actions_panel = map_actions_panel
        self.map_actions_panel.action_selected_callback = self._action_changed
        self._action = MapAction.BRUSH_TILE
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

    def deselect_object(self) -> None:
        if isinstance(self._mouse_adapter, SelectObjectMouseAdapter):
            cast(SelectObjectMouseAdapter, self._mouse_adapter).hide_buttons()

    def select_object(self, obj: TiledObject) -> None:
        if not isinstance(self._mouse_adapter, SelectObjectMouseAdapter):
            self._mouse_adapter.deselected()
            self._mouse_adapter = self._mouse_object_adapters[MapAction.SELECT_OBJECT]
        self.map_actions_panel.object_layer = True
        self.map_actions_panel.action = MapAction.SELECT_OBJECT
        select_object_mouse_adapter = cast(SelectObjectMouseAdapter, self._mouse_adapter)
        if select_object_mouse_adapter.selected_object != obj:
            select_object_mouse_adapter.selected_object = obj

            viewport = Rect(-self.h_scrollbar.offset,
                            -self.v_scrollbar.offset,
                            self.rect.width - self.v_scrollbar.rect.width,
                            self.rect.height - self.h_scrollbar.rect.height)

            if not viewport.colliderect(obj.rect):
                cx = self.rect.width // 2
                cy = self.rect.height // 2
                ox, oy = obj.rect.center
                self.h_scrollbar.offset = cx - ox
                self.v_scrollbar.offset = cy - oy

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
        if self._mouse_adapter is not None:
            self._mouse_adapter.deselected()
        if self._selected_layer is not None:
            self.map_actions_panel.object_layer = not isinstance(self._selected_layer, TiledTileLayer)

            if action.object_layer != self.map_actions_panel.object_layer:
                if self.map_actions_panel.object_layer:
                    self._action = MapAction.SELECT_OBJECT
                else:
                    self._action = MapAction.SELECT_TILE

            self._mouse_adapter = self._mouse_object_adapters[self._action] if self.map_actions_panel.object_layer else self._mouse_tile_adapters[self._action]
        else:
            self._mouse_adapter = self._null_mouse_adapter
        self._mouse_adapter.selected()

    def _calc_new_obj_text(self, obj: TiledObject, x_offset, y_offset) -> None:
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
        obj.properties["__text_surface"] = surface
        obj.properties["__old_rect"] = obj.rect.copy()
        obj.properties["__old_name"] = obj.name
        obj.properties["__old_x_offset"] = x_offset
        obj.properties["__old_y_offset"] = y_offset
        r.center = obj.rect.center
        r.move_ip(x_offset, y_offset)
        r.move_ip(0, -obj.rect.height / 2 - r.height / 2 - 4)
        obj.properties["__text_position"] = r

    def _draw_object_layer(self, layer: TiledObjectGroup, surface: Surface, rect: Rect, x_offset: int, y_offset: int) -> None:
        for obj in layer.objects:
            if obj.visible:
                if ("__old_rect" not in obj.properties
                        or obj.properties["__old_rect"] != obj.rect
                        or obj.properties["__old_name"] != obj.name):
                    self._calc_new_obj_text(obj, rect.x + x_offset, rect.y + y_offset)
                if obj.properties["__old_x_offset"] != x_offset or obj.properties["__old_y_offset"] != y_offset:
                    dx = x_offset - obj.properties["__old_x_offset"]
                    dy = y_offset - obj.properties["__old_y_offset"]
                    obj.properties["__old_x_offset"] = x_offset
                    obj.properties["__old_y_offset"] = y_offset
                    obj.properties["__text_position"].move_ip(dx, dy)

                surface.blit(obj.properties["__text_surface"], obj.properties["__text_position"])
                if obj.image is not None:
                    surface.blit(obj.image, (self.rect.x + obj.x + x_offset, self.rect.y + obj.y + y_offset))
                else:
                    r = obj.rect.move(rect.x + x_offset + 1, rect.y + y_offset + 1)
                    pygame.draw.rect(surface, (0, 0, 0), r, width=1)
                    r.move_ip(-1, -1)
                    pygame.draw.rect(surface, (128, 255, 255), r, width=1)

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

    def draw(self, surface: Surface) -> None:
        with clip(surface, self.rect):
            surface.set_clip(self.content_rect)
            self._local_draw(surface)
            for a in self.arrow_buttons:
                if a.visible:
                    a.draw(surface)
        for c in self.components:
            if c not in self.arrow_buttons and c.visible:
                c.draw(surface)

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
        if (self.overlay_surface is None or self._selected_layer is None or not isinstance(self._selected_layer, TiledTileLayer)
                or self._action not in [MapAction.BRUSH_TILE, MapAction.RANDOM_BRUSH_TILE, MapAction.RUBBER_TILE]):
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
            return self._mouse_adapter.mouse_up(x, y, modifier)

    def mouse_down(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_down(x, y, modifier):
            return self._mouse_adapter.mouse_down(x, y, modifier)

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if not super().mouse_move(x, y, modifier):
            return self._mouse_adapter.mouse_move(x, y, modifier)

    def mouse_in(self, x: int, y: int) -> bool:
        if not super().mouse_in(x, y):
            self.calc_mouse_over_rect(x, y)
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        super().mouse_out(x, y)
        self._mouse_adapter.mouse_out(x, y)
        return True
