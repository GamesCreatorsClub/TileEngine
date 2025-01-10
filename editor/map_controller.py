import enum
import os
from abc import ABC
from random import Random
from typing import Optional, Callable, cast

import pygame.draw
from pygame import Rect, Surface
from pygame.font import Font

from editor.actions_controller import ActionsController
from editor.pygame_components import ScrollableCanvas, ComponentCollection, Button
from editor.resize_component import ResizeButton, ResizePosition
from editor.tileset_controller import TilesetController
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
    FILL_TILE = (False,)
    RANDOM_FILL_TILE = (False,)

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

        self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "icons.png"))

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
            MapAction.ADD_IMAGE_OBJECT: button(1, 2, lambda: self._select_action(MapAction.ADD_IMAGE_OBJECT)),
            MapAction.ADD_AREA_OBJECT: button(2, 3, lambda: self._select_action(MapAction.ADD_AREA_OBJECT)),
        }
        self.tile_buttons = {
            MapAction.SELECT_TILE: button(0, 3, lambda: self._select_action(MapAction.SELECT_TILE)),
            MapAction.BRUSH_TILE: button(1, 2, lambda: self._select_action(MapAction.BRUSH_TILE)),
            MapAction.RANDOM_BRUSH_TILE: button(2, 8, lambda: self._select_action(MapAction.RANDOM_BRUSH_TILE)),
            MapAction.RUBBER_TILE: button(3, 1, lambda: self._select_action(MapAction.RUBBER_TILE)),
            MapAction.FILL_TILE: button(4, 5, lambda: self._select_action(MapAction.FILL_TILE)),
            MapAction.RANDOM_FILL_TILE: button(5, 9, lambda: self._select_action(MapAction.RANDOM_FILL_TILE)),
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
    def __init__(self, map_controller: 'MapController') -> None:
        self.map_controller = map_controller
        self.action_controller = map_controller.actions_controller

    def mouse_up(self, _x: int, _y: int, _button: int, _modifier: int) -> bool:
        return False

    def mouse_down(self, _x: int, _y: int, _button: int, _modifier: int) -> bool:
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
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)


class SelectObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_controller: 'MapController',
                 scrolling_margin: int = SCROLLING_MARGIN,
                 scrolling_step: int = SCROLLING_STEP) -> None:
        super().__init__(map_controller)
        self.scrolling_margin = scrolling_margin
        self.scrolling_step = scrolling_step
        self.selected_object: Optional[TiledObject] = None
        self.mouse_is_down = False
        self.touch_x = 0
        self.touch_y = 0
        self.viewport = Rect(
            -self.map_controller.h_scrollbar.offset,
            -self.map_controller.v_scrollbar.offset,
            self.map_controller.rect.width - self.map_controller.v_scrollbar.rect.width,
            self.map_controller.rect.height - self.map_controller.h_scrollbar.rect.height)

    def selected(self) -> None:
        pass

    def deselected(self) -> None:
        self.hide_buttons()

    def hide_buttons(self) -> None:
        for b in self.map_controller.arrow_buttons:
            b.visible = False

    def update_buttons(self) -> None:
        if self.selected_object is not None:
            r = self.selected_object.rect.move(self.map_controller.rect.x + self.map_controller.h_scrollbar.offset, self.map_controller.rect.y + self.map_controller.v_scrollbar.offset)

            for b in self.map_controller.arrow_buttons:
                b.update_rect(r)
                b.visible = True

    def movement_callback(self, button: ResizeButton, distance_x: int, distance_y: int) -> None:
        if self.selected_object is not None:
            rect = self.selected_object.rect
            pos = button.position
            x = rect.x
            y = rect.y
            width = rect.width
            height = rect.height
            dx = pos.dx
            dy = pos.dy

            if dx < 0:
                x += dx * distance_x
            width += abs(dx) * distance_x

            if dy < 0:
                y += dy * distance_y
            height += abs(dy) * distance_y

            if x != rect.x or y != rect.y:
                self.action_controller.move_object(self.selected_object, x, y)
            if width != rect.width or height != rect.height:
                self.action_controller.resize_object(self.selected_object, width, height)

            self.update_buttons()

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            def find_object(layer: TiledObjectGroup, x: int, y: int) -> Optional[TiledObject]:
                for o in layer.objects_id_map.values():
                    if o.visible and o.rect.collidepoint(x, y):
                        return o
                return None

            layer = self.map_controller.object_layer
            if layer is not None:
                corrected_x = x - self.map_controller.rect.x - self.map_controller.h_scrollbar.offset
                corrected_y = y - self.map_controller.rect.y - self.map_controller.v_scrollbar.offset

                obj = find_object(layer, corrected_x, corrected_y)
                if obj is not None:
                    self.mouse_is_down = True
                    self.selected_object = obj
                    self.map_controller.object_selected_callback(obj)
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

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_is_down = False
        return False

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.selected_object is not None and self.mouse_is_down and self.viewport.collidepoint(x, y):
            dx = x - self.touch_x
            dy = y - self.touch_y
            if dx == 0 and dy == 0:
                if x <= self.scrolling_margin:
                    dx = -self.scrolling_step
                    self.map_controller.h_scrollbar.offset += self.scrolling_step
                elif x >= self.viewport.right - self.scrolling_margin:
                    dx = +self.scrolling_step
                    self.map_controller.h_scrollbar.offset -= self.scrolling_step
                if y <= self.scrolling_margin:
                    dy = -self.scrolling_step
                    self.map_controller.v_scrollbar.offset += self.scrolling_step
                elif y >= self.viewport.bottom - self.scrolling_margin:
                    dy = self.scrolling_step
                    self.map_controller.v_scrollbar.offset -= self.scrolling_step

                self.action_controller.move_object(
                    self.selected_object,
                    self.selected_object.rect.x + dx,
                    self.selected_object.rect.y + dy
                )
            else:
                self.action_controller.move_object(
                    self.selected_object,
                    self.selected_object.rect.x + dx,
                    self.selected_object.rect.y + dy
                )

                self.touch_x = x
                self.touch_y = y
                self.map_controller.object_selected_callback(self.selected_object)
                if self.selected_object.image is None:
                    self.update_buttons()

        return True

    def mouse_out(self, x: int, y: int) -> bool:
        # self.mouse_is_down = False
        return False


class AddImageObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            layer = self.map_controller.object_layer
            tilemap = self.map_controller.tiled_map
            if layer is not None and self.map_controller.tileset_controller.selection is not None:
                obj = TiledObject(layer)
                obj.gid = self.map_controller.tileset_controller.selection[0][0]
                img = tilemap.images[obj.gid]
                obj.rect = img.get_rect()
                obj.rect.center = (
                    x - self.map_controller.rect.x - self.map_controller.h_scrollbar.offset,
                    y - self.map_controller.rect.y - self.map_controller.v_scrollbar.offset
                )
                self.action_controller.add_object(obj)

                self.map_controller.object_added_callback(layer, obj)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return True


class AddAreaObjectMouseAdapter(MouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            layer = self.map_controller.object_layer
            if layer is not None and self.map_controller.tileset_controller.selection is not None:
                obj = TiledObject(layer)
                obj.gid = 0
                obj.rect = Rect(0, 0, 32, 32)
                obj.rect.center = (
                    x - self.map_controller.rect.x - self.map_controller.h_scrollbar.offset,
                    y - self.map_controller.rect.y - self.map_controller.v_scrollbar.offset
                )
                self.action_controller.add_object(obj)
                self.map_controller.object_added_callback(layer, obj)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        return True


class SelectTileMouseAdapter(MouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)
        self.mouse_is_down = False
        self.touch_x = 0
        self.touch_y = 0
        self.current_selection = None
        self.current_selection_viewport = None
        self.add_selection = None

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.touch_x = x
            self.touch_y = y
            self.mouse_is_down = True
            self.current_selection = None
            self.current_selection_viewport = None
            self.add_selection = modifier == pygame.KMOD_SHIFT
            if not self.add_selection:
                self.map_controller.select_none()
        return False

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_is_down = False
            self.current_selection = None
            self.current_selection_viewport = None
        return True

    def mouse_move(self, x: int, y: int, _modifier: int) -> bool:
        if self.mouse_is_down:
            if self.current_selection is None:
                self.current_selection = Rect(0, 0, 0, 0)
                self.current_selection_viewport = Rect(0, 0, 0, 0)
                if self.add_selection:
                    self.map_controller.selection.append(self.current_selection)
                    self.map_controller.selection_viewport_rects.append(self.current_selection_viewport)
                else:
                    self.map_controller.selection = [self.current_selection]
                    self.map_controller.selection_viewport_rects = [self.current_selection_viewport]
                self.map_controller.selection_changed_callback(self.map_controller.selection)

            tiled_map = self.map_controller.tiled_map
            if tiled_map is not None and (x != self.touch_x or y != self.touch_y):
                start_tile_x, start_tile_y = self.map_controller.calc_mouse_to_tile(self.touch_x, self.touch_y)
                end_tile_x, end_tile_y = self.map_controller.calc_mouse_to_tile(x, y)
                if start_tile_x > end_tile_x:
                    start_tile_x, end_tile_x = end_tile_x, start_tile_x
                if start_tile_y > end_tile_y:
                    start_tile_y, end_tile_y = end_tile_y, start_tile_y
                self.current_selection.update(start_tile_x, start_tile_y, end_tile_x - start_tile_x + 1, end_tile_y - start_tile_y + 1)

                self.current_selection_viewport.update(
                    self.map_controller.rect.x + self.current_selection.x * tiled_map.tilewidth + self.map_controller.h_scrollbar.offset,
                    self.map_controller.rect.y + self.current_selection.y * tiled_map.tileheight + self.map_controller.v_scrollbar.offset,
                    self.current_selection.width * tiled_map.tilewidth,
                    self.current_selection.height * tiled_map.tileheight,
                )

                return True
        return False

    def mouse_out(self, x: int, y: int) -> bool:
        return False


class BrushTileMouseAdapter(MouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)
        self.mouse_is_down = False
        self.last_tile_x = -1
        self.last_tile_y = -1

    def update_map(self, x: int, y: int, data: list[list[int]]) -> None:
        width = len(data)
        height = len(data[0])
        mc = self.map_controller
        ac = self.action_controller
        for iy in range(width):
            for ix in range(height):
                if mc.is_in_selection(ix + x, iy + y):
                    gid = data[iy][ix]
                    if gid != 0:
                        ac.plot(ix + x, iy + y, gid)

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            self.mouse_is_down = False
        return False

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if button == 1:
            if not super().mouse_down(x, y, button, modifier):
                self.mouse_is_down = True
                tilemap = self.map_controller.tiled_map
                if tilemap is not None and self.map_controller.tileset_controller.selection is not None:
                    self.last_tile_x, self.last_tile_y = self.map_controller.calc_mouse_to_tile(x, y)

                    data = self.map_controller.tileset_controller.selection
                    self.update_map(self.last_tile_x, self.last_tile_y, data)
        return True

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if self.mouse_is_down:
            tilemap = self.map_controller.tiled_map
            if tilemap is not None and self.map_controller.tileset_controller.selection is not None:
                tile_x, tile_y = self.map_controller.calc_mouse_to_tile(x, y)
                if tile_x != self.last_tile_x or tile_y != self.last_tile_y:
                    self.last_tile_x = tile_x
                    self.last_tile_y = tile_y

                    data = self.map_controller.tileset_controller.selection
                    self.update_map(self.last_tile_x, self.last_tile_y, data)

        self.map_controller.calc_mouse_over_rect(x, y)
        return True


class RandomBrushTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)
        self.random = Random()

    def update_map(self, x: int, y: int, data: list[list[int]]) -> None:
        if self.map_controller.is_in_selection(x, y):
            rx = self.random.randint(0, len(data) - 1)
            ry = self.random.randint(0, len(data[0]) - 1)
            gid = data[ry][rx]
            if gid != 0:
                self.action_controller.plot(x, y, gid)


class FillTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)
        self.random = Random()

    def update_map(self, x: int, y: int, data: list[list[int]]) -> None:
        cm = self.map_controller
        ac = self.action_controller
        tiled_map = self.map_controller.tiled_map
        layer = self.map_controller.tiled_layer
        width = len(data)
        height = len(data[0])
        selected_gid = layer.data[y][x]

        px = x % width
        py = y % height

        def find_left(x: int, y: int) -> int:
            while x > 0 and layer.data[y][x - 1] == selected_gid and cm.is_in_selection(x - 1, y):
                x -= 1
            return x

        stack = [(find_left(x, y), y)]

        while len(stack) > 0:
            top = False
            bottom = False
            x, y = stack[0]
            del stack[0]
            while x < tiled_map.width and layer.data[y][x] == selected_gid and cm.is_in_selection(x, y):
                if y > 0 and layer.data[y - 1][x] == selected_gid and cm.is_in_selection(x, y - 1):
                    if not top:
                        stack.append((find_left(x, y - 1), y - 1))
                        top = True
                    else:
                        top = False
                if y < tiled_map.height - 1 and layer.data[y + 1][x] == selected_gid and cm.is_in_selection(x, y + 1):
                    if not bottom:
                        stack.append((find_left(x, y + 1), y + 1))
                        bottom = True
                    else:
                        bottom = False

                ac.plot(x, y, data[(y - py) % height][(x - px) % width])

                x += 1


class RandomFillTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)
        self.random = Random()

    def update_map(self, x: int, y: int, data: list[list[int]]) -> None:
        ac = self.action_controller
        cm = self.map_controller
        tiled_map = self.map_controller.tiled_map
        layer = self.map_controller.tiled_layer
        selected_gid = layer.data[y][x]

        def find_left(x: int, y: int) -> int:
            while x > 0 and layer.data[y][x - 1] == selected_gid and cm.is_in_selection(x - 1, y):
                x -= 1
            return x

        stack = [(find_left(x, y), y)]

        while len(stack) > 0:
            top = False
            bottom = False
            t = stack[0]
            x, y = t
            del stack[0]
            while x < tiled_map.width and layer.data[y][x] == selected_gid and cm.is_in_selection(x, y):
                if y > 0 and layer.data[y - 1][x] == selected_gid and cm.is_in_selection(x, y - 1):
                    if not top:
                        stack.append((find_left(x, y - 1), y - 1))
                        top = True
                    else:
                        top = False
                if y < tiled_map.height - 1 and layer.data[y + 1][x] == selected_gid and cm.is_in_selection(x, y + 1):
                    if not bottom:
                        stack.append((find_left(x, y + 1), y + 1))
                        bottom = True
                    else:
                        bottom = False
                rx = self.random.randint(0, len(data[0]) - 1)
                ry = self.random.randint(0, len(data) - 1)

                ac.plot(x, y, data[ry][rx])

                x += 1


class RubberTileMouseAdapter(BrushTileMouseAdapter):
    def __init__(self, map_controller: 'MapController') -> None:
        super().__init__(map_controller)

    def update_map(self, x: int, y: int, _data: list[list[int]]) -> None:
        self.action_controller.plot(x, y, 0)


class MapController(ScrollableCanvas):
    def __init__(self,
                 rect: Rect,
                 font: Font,
                 map_actions_panel: MapActionsPanel,
                 tileset_controller: TilesetController,
                 actions_controller: ActionsController,
                 object_added_callback: Callable[[TiledObjectGroup, TiledObject], None],
                 object_selected_callback: Callable[[TiledObject], None],
                 selection_changed_callback: Callable[[list[Rect]], None]) -> None:
        super().__init__(rect)
        self.font = font

        self._tiled_layer: Optional[TiledTileLayer] = None
        self._object_layer: Optional[TiledObjectGroup] = None

        self.actions_controller = actions_controller
        actions_controller.tiled_map_callbacks.append(self._tiled_map_callback)
        actions_controller.tiled_layer_callbacks.append(self._tiled_layer_callback)
        actions_controller.object_layer_callbacks.append(self._object_layer_callback)
        actions_controller.current_object_callbacks.append(self._current_object_callback)

        self.arrows_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "arrows-small.png"))

        self.object_added_callback = object_added_callback
        self.object_selected_callback = object_selected_callback
        self.selection_changed_callback = selection_changed_callback

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
            MapAction.RUBBER_TILE: RubberTileMouseAdapter(self),
            MapAction.FILL_TILE: FillTileMouseAdapter(self),
            MapAction.RANDOM_FILL_TILE: RandomFillTileMouseAdapter(self)
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

        self._tiled_map: Optional[TiledMap] = None
        self.tileset_controller = tileset_controller
        self.map_actions_panel = map_actions_panel
        self.map_actions_panel.action_selected_callback = self._action_changed
        self._action = MapAction.BRUSH_TILE
        self._action_changed(map_actions_panel.action)
        self.mouse_over_rect: Optional[Rect] = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.overlay_surface: Optional[Surface] = None
        self.selection: list[Rect] = []
        self.selection_viewport_rects: list[Rect] = []
        self._selection_overlay: Optional[Surface] = None

        self.v_scrollbar.visible = False
        self.h_scrollbar.visible = False

    def _tiled_map_callback(self, tiled_map: TiledMap) -> None:
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
            self._selection_overlay = Surface((tiled_map.tilewidth, tiled_map.tileheight), pygame.SRCALPHA, 32)
            self._selection_overlay.fill((255, 255, 0, 32))

    def _current_layer_callback(self, current_layer: BaseTiledLayer) -> None:
        self._current_layer = current_layer

    def _tiled_layer_callback(self, tiled_layer: TiledTileLayer) -> None:
        self._tiled_layer = tiled_layer
        self._action_changed(self._action)

    def _object_layer_callback(self, object_layer: TiledObjectGroup) -> None:
        self._object_layer = object_layer
        self._action_changed(self._action)

    def _current_object_callback(self, current_object: Optional[TiledObject]) -> None:
        self.select_object(current_object)

    def _action_changed(self, action: MapAction) -> None:
        self._action = action
        if self._mouse_adapter is not None:
            self._mouse_adapter.deselected()

        if self._tiled_layer is not None:
            self.map_actions_panel.object_layer = False
            if action.object_layer != self.map_actions_panel.object_layer:
                self._action = MapAction.SELECT_TILE
            self._mouse_adapter = self._mouse_tile_adapters[self._action]
            self.tile_selection_changed()
        elif self._object_layer is not None:
            self.map_actions_panel.object_layer = True
            if action.object_layer != self.map_actions_panel.object_layer:
                self._action = MapAction.SELECT_OBJECT
            self._mouse_adapter = self._mouse_object_adapters[self._action]
            self.tile_selection_changed()
        else:
            self._mouse_adapter = self._null_mouse_adapter
        self._mouse_adapter.selected()

    @property
    def tiled_map(self) -> TiledMap:
        return self._tiled_map

    @property
    def tiled_layer(self) -> Optional[TiledTileLayer]:
        return self._tiled_layer

    @property
    def object_layer(self) -> Optional[TiledObjectGroup]:
        return self._object_layer

    def scrollbars_moved(self, dx: int, dy: int) -> None:
        self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
        for r in self.selection_viewport_rects:
            r.move_ip(dx, dy)

    def is_in_selection(self, x: int, y: int) -> bool:
        if len(self.selection) == 0:
            return True

        for s in self.selection:
            if s.collidepoint(x, y):
                return True
        return False

    def calc_mouse_to_tile(self, x: int, y: int) -> tuple[int, int]:
        self.mouse_x = x
        self.mouse_y = y
        tilemap = self.tiled_map
        tile_x = ((x - self.rect.x - self.h_scrollbar.offset) // tilemap.tilewidth)
        tile_y = ((y - self.rect.y - self.v_scrollbar.offset) // tilemap.tileheight)
        return tile_x, tile_y

    def calc_mouse_over_rect(self, x: int, y: int) -> None:
        if (self.overlay_surface is None or self._tiled_layer is None
                or self._action not in [MapAction.BRUSH_TILE, MapAction.RANDOM_BRUSH_TILE, MapAction.FILL_TILE, MapAction.RANDOM_FILL_TILE, MapAction.RUBBER_TILE]):
            self.mouse_over_rect = None
            return

        tilemap = self.tiled_map
        tile_x, tile_y = self.calc_mouse_to_tile(x, y)
        if 0 <= tile_x < tilemap.width and 0 <= tile_y < tilemap.height:
            x = self.rect.x + tile_x * tilemap.tilewidth + self.h_scrollbar.offset
            y = self.rect.y + tile_y * tilemap.tileheight + self.v_scrollbar.offset
            if self._action == MapAction.BRUSH_TILE or self._action == MapAction.FILL_TILE:
                selection = self.tileset_controller.selection
                w = len(selection) * tilemap.tilewidth if selection is not None else tilemap.tilewidth
                h = len(selection[0]) * tilemap.tileheight if selection is not None else tilemap.tileheight
            else:
                w = tilemap.tilewidth
                h = tilemap.tileheight
            self.mouse_over_rect = Rect(x, y, w, h)
        else:
            self.mouse_over_rect = None

    def tile_selection_changed(self) -> None:
        selection = self.tileset_controller.selection
        if selection is not None:
            tileset = self.actions_controller.current_tileset
            if self._action == MapAction.BRUSH_TILE or self._action == MapAction.FILL_TILE:
                self.overlay_surface = Surface((len(selection[0]) * tileset.tilewidth, len(selection) * tileset.tileheight), pygame.SRCALPHA, 32)
                for y in range(len(selection)):
                    for x in range(len(selection[0])):
                        self.overlay_surface.blit(self.tiled_map.images[selection[y][x]], (x * tileset.tilewidth, y * tileset.tileheight))
                self.overlay_surface.set_alpha(128)
                self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
            elif self._action == MapAction.RANDOM_BRUSH_TILE or self._action == MapAction.RANDOM_FILL_TILE:
                self.overlay_surface = Surface((tileset.tilewidth, tileset.tileheight), pygame.SRCALPHA, 32)
                self.overlay_surface.blit(self.tiled_map.images[selection[0][0]], (0, 0))
                self.overlay_surface.set_alpha(128)
                self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
            else:
                self.overlay_surface = Surface((tileset.tilewidth, tileset.tileheight), pygame.SRCALPHA, 32)
                self.overlay_surface.set_alpha(128)
                self.calc_mouse_over_rect(self.mouse_x, self.mouse_y)
        else:
            self.mouse_over_rect = None
            self.overlay_surface = None

    # Actions to be called externally

    def select_all(self) -> None:
        if self._tiled_map is not None:
            self.selection = [
                Rect(0, 0, self._tiled_map.width, self._tiled_map.height)
            ]
            self.selection_viewport_rects = [
                Rect(
                    self.rect.x + self.h_scrollbar.offset,
                    self.rect.y + self.v_scrollbar.offset,
                    self._tiled_map.width * self._tiled_map.tilewidth,
                    self._tiled_map.height * self._tiled_map.tileheight)
            ]
            self.selection_changed_callback(self.selection)

    def select_none(self) -> None:
        self.selection = []
        self.selection_viewport_rects = []
        self.selection_changed_callback(self.selection)

    def delete_tiles(self) -> None:
        if self._tiled_layer is not None:
            for s in self.selection:
                for y in range(s.y, s.bottom):
                    for x in range(s.x, s.right):
                        self._tiled_layer.data[y][x] = 0

    def plot(self, x: int, y: int, gid: int) -> None:
        if self.is_in_selection(x, y):
            self.actions_controller.plot(x, y, gid)

    def deselect_object(self) -> None:
        if isinstance(self._mouse_adapter, SelectObjectMouseAdapter):
            cast(SelectObjectMouseAdapter, self._mouse_adapter).hide_buttons()

    def select_object(self, obj: TiledObject) -> None:
        if obj is None:
            return

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
        r.move_ip(self.rect.x + x_offset, self.rect.y + y_offset)
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
            tiled_map = self._tiled_map
            colour = tiled_map.backgroundcolor if tiled_map.backgroundcolor else (0, 0, 0)
            pygame.draw.rect(surface, colour, self.rect)
            for layer in tiled_map.layers:
                if layer.visible:
                    if isinstance(layer, TiledObjectGroup):
                        self._draw_object_layer(layer, surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)
                    else:
                        layer.draw(surface, self.rect, self.h_scrollbar.offset, self.v_scrollbar.offset)

            if self.mouse_over_rect is not None:
                surface.blit(self.overlay_surface, self.mouse_over_rect)
                pygame.draw.rect(surface, (255, 255, 255), self.mouse_over_rect, width=1)

            for s in self.selection:
                for y in range(s.y, s.bottom):
                    for x in range(s.x, s.right):
                        surface.blit(self._selection_overlay,
                                     (self.rect.x + x * tiled_map.tilewidth + self.h_scrollbar.offset,
                                      self.rect.y + y * tiled_map.tilewidth + self.v_scrollbar.offset))
            for r in self.selection_viewport_rects:
                pygame.draw.rect(surface, (128, 128, 0), r, width=1)

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

    def mouse_up(self, x: int, y: int, button: int, modifier: int) -> bool:
        if not super().mouse_up(x, y, button, modifier):
            return self._mouse_adapter.mouse_up(x, y, button, modifier)

    def mouse_down(self, x: int, y: int, button: int, modifier: int) -> bool:
        if not super().mouse_down(x, y, button, modifier):
            return self._mouse_adapter.mouse_down(x, y, button, modifier)

    def mouse_move(self, x: int, y: int, modifier) -> bool:
        if (self._action == MapAction.SELECT_OBJECT
                and cast(SelectObjectMouseAdapter, self._mouse_adapter).mouse_is_down
                and cast(SelectObjectMouseAdapter, self._mouse_adapter).selected_object is not None):
            return self._mouse_adapter.mouse_move(x, y, modifier)
        if not super().mouse_move(x, y, modifier):
            return self._mouse_adapter.mouse_move(x, y, modifier)

    def mouse_in(self, x: int, y: int) -> bool:
        if not super().mouse_in(x, y):
            self.calc_mouse_over_rect(x, y)
        return True

    def mouse_out(self, x: int, y: int) -> bool:
        super().mouse_out(x, y)
        self.actions_controller.fix_change()
        self._mouse_adapter.mouse_out(x, y)
        return True
