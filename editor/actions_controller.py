import time
from abc import ABC
from enum import Enum
from typing import Optional, cast, Callable, Any

from pygame import Color

from engine.tmx import TiledMap, TiledObjectGroup, BaseTiledLayer, TiledTileLayer, TiledObject, TiledTileset, TiledElement


MAX_UNDO = 20


class ChangeKind(Enum):
    NONE = (False, )
    CHANGE_TILED_LAYER = (True, )
    MOVE_AND_RESIZE_OBJECT = (True,)
    ADD_OBJECT = (False, )
    DELETE_OBJECT = (False, )
    ADD_PROPERTY = (False, )
    UPDATE_PROPERTY = (False, )
    DELETE_PROPERTY = (False, )
    UPDATE_ATTRIBUTE = (False, )

    def __new__(cls, cumulative: bool):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    def __init__(self, cumulative: bool) -> None:
        self.cumulative = cumulative


class Change(ABC):
    def __init__(self, kind: ChangeKind, action_controller: 'ActionsController') -> None:
        self.kind = kind
        self.action_controller = action_controller
        self.fixed = False

    def prepare(self, previous: Optional['Change']) -> None:
        pass

    def fix(self) -> None:
        pass

    def undo(self) -> None:
        pass

    def redo(self) -> None:
        pass


class NoChange(Change):
    def __init__(self, action_controller: 'ActionsController') -> None:
        super().__init__(ChangeKind.NONE, action_controller)


class TiledTileLayerChange(Change):
    def __init__(self, action_controller: 'ActionsController') -> None:
        super().__init__(ChangeKind.CHANGE_TILED_LAYER, action_controller)
        self.layer: Optional[TiledTileLayer] = None
        self.before_data: list[list[int]] = [[]]
        self.after_data: list[list[int]] = [[]]

    def prepare(self, previous: Optional['TiledTileLayerChange']) -> None:
        self.layer = self.action_controller.tiled_layer
        if previous is not None:
            self.before_data = previous.after_data
        else:
            self.before_data = [row.copy() for row in self.layer.data]

    def fix(self) -> None:
        self.after_data = [row.copy() for row in self.layer.data]
        self.fixed = True

    def undo(self) -> None:
        for i in range(len(self.layer.data)):
            self.layer.data[i][:] = self.before_data[i]

    def redo(self) -> None:
        for i in range(len(self.layer.data)):
            self.layer.data[i][:] = self.after_data[i]


class MoveAndResizeObjectChange(Change):
    def __init__(self, action_controller: 'ActionsController', obj: TiledObject) -> None:
        super().__init__(ChangeKind.MOVE_AND_RESIZE_OBJECT, action_controller)
        self.obj = obj
        self.previous_x = 0
        self.previous_y = 0
        self.previous_w = 0
        self.previous_h = 0
        self.next_x = 0
        self.next_y = 0
        self.next_w = 0
        self.next_h = 0

    def prepare(self, _: Optional['MoveObjectChange']) -> None:
        self.previous_x = self.obj.x
        self.previous_y = self.obj.y
        self.previous_w = self.obj.width
        self.previous_h = self.obj.height

    def fix(self) -> None:
        self.next_x = self.obj.x
        self.next_y = self.obj.y
        self.next_w = self.obj.width
        self.next_h = self.obj.height

    def undo(self) -> None:
        self.obj.x = self.previous_x
        self.obj.y = self.previous_y
        self.obj.width = self.previous_w
        self.obj.height = self.previous_h

    def redo(self) -> None:
        self.obj.x = self.next_x
        self.obj.y = self.next_y
        self.obj.width = self.next_w
        self.obj.height = self.next_h


class ActionsController:
    def __init__(self) -> None:
        self._tiled_map: Optional[TiledMap] = None
        self._selected_layer: Optional[BaseTiledLayer] = None
        self._tiled_layer: Optional[TiledTileLayer] = None
        self._object_layer: Optional[TiledObjectGroup] = None
        self._current_object: Optional[TiledObject] = None
        self._current_tileset: Optional[TiledTileset] = None

        self.tiled_map_callbacks: list[Callable[[Optional[TiledMap]], None]] = []
        # self.selected_layer_callbacks: list[Callable[[Optional[BaseTiledLayer]], None]] = []
        self.tiled_layer_callbacks: list[Callable[[Optional[TiledTileLayer]], None]] = []
        self.object_layer_callbacks: list[Callable[[Optional[TiledObjectGroup]], None]] = []
        self.current_object_callbacks: list[Callable[[Optional[TiledObject]], None]] = []
        self.current_tileset_callbacks: list[Callable[[Optional[TiledTileset]], None]] = []

        self.undo_redo_callbacks: list[Callable[[bool, bool], None]] = []

        self._no_change = NoChange(self)

        self.change_kind = ChangeKind.NONE
        self.current_unfixed_change: Optional[Change] = None
        self.last_change_timestamp = 0.0
        self.changes: list[Change] = []
        self.pointer = 0

    @property
    def tiled_map(self) -> TiledMap:
        return self._tiled_map

    @tiled_map.setter
    def tiled_map(self, tiled_map: Optional[TiledMap]) -> None:
        new_tiled_map = self._tiled_map != tiled_map
        self._tiled_map = tiled_map
        if tiled_map is not None:
            if new_tiled_map:
                self.current_object = None
        else:
            self.current_tileset = None
            self.current_object = None

        for callback in self.tiled_map_callbacks:
            callback(tiled_map)

        if tiled_map is not None:
            if new_tiled_map:
                self.current_tileset = tiled_map.tilesets[0] if len(tiled_map.tilesets) > 0 else None

    @property
    def current_layer(self) -> BaseTiledLayer:
        return self._selected_layer

    @current_layer.setter
    def current_layer(self, current_layer: BaseTiledLayer) -> None:
        self._selected_layer = current_layer
        if isinstance(current_layer, TiledTileLayer):
            self._tiled_layer = cast(TiledTileLayer, current_layer)
            self._object_layer = None
        elif isinstance(current_layer, TiledObjectGroup):
            self._tiled_layer = None
            self._object_layer = cast(TiledObjectGroup, current_layer)

        for callback in self.tiled_layer_callbacks:
            callback(self._tiled_layer)

        for callback in self.object_layer_callbacks:
            callback(self._object_layer)

    @property
    def tiled_layer(self) -> Optional[TiledTileLayer]:
        return self._tiled_layer

    @property
    def object_layer(self) -> Optional[TiledTileLayer]:
        return self._object_layer

    @property
    def current_object(self) -> Optional[TiledObject]:
        return self._current_object

    @current_object.setter
    def current_object(self, current_object: Optional[TiledObject]) -> None:
        self._current_object = current_object
        for callback in self.current_object_callbacks:
            callback(current_object)

    @property
    def current_tileset(self) -> Optional[TiledTileset]:
        return self._current_tileset

    @current_tileset.setter
    def current_tileset(self, current_tileset: Optional[TiledTileset]) -> None:
        self._current_tileset = current_tileset
        for callback in self.current_tileset_callbacks:
            callback(current_tileset)

    def _add_change(self, change: Change) -> None:
        self.fix_change()

        if self.pointer < len(self.changes):
            del self.changes[self.pointer:]
        if len(self.changes) > MAX_UNDO:
            del self.changes[0]
        print(f"Added change for {change.kind}")
        previous = None if len(self.changes) == 0 else self.changes[-1]
        previous = previous if previous is not None and previous.kind == change.kind else None
        change.prepare(previous)
        self.changes.append(change)
        self.pointer = len(self.changes)

        self.change_kind = change.kind
        self.current_unfixed_change = change if not change.fixed else None
        print(f"New change {change.kind} {len(self.changes)} ptr {self.pointer}, unfixed={'' if self.current_unfixed_change is None else self.current_unfixed_change.kind}")

        for callback in self.undo_redo_callbacks:
            callback(self.pointer > 0, False)

    def action_tick(self) -> None:
        if self.change_kind.cumulative and self.last_change_timestamp + 2 < time.time():
            self.fix_change()

    def fix_change(self) -> None:
        if self.current_unfixed_change is not None:
            print(f"Fixed change change {self.current_unfixed_change.kind} {len(self.changes)} ptr {self.pointer}, unfixed={'' if self.current_unfixed_change is None else self.current_unfixed_change.kind}")

            self.current_unfixed_change.fix()
            self.current_unfixed_change = None
        self.change_kind = ChangeKind.NONE

    def undo(self) -> None:
        if self.pointer > 0:
            if not self.changes[self.pointer - 1].fixed:
                self.changes[self.pointer - 1].fix()

            self.pointer -= 1
            self.changes[self.pointer].undo()
            print(f"Undo change {self.changes[self.pointer].kind} {len(self.changes)} ptr {self.pointer}, unfixed={'' if self.current_unfixed_change is None else self.current_unfixed_change.kind}")
            for callback in self.undo_redo_callbacks:
                callback(self.pointer > 0, self.pointer < len(self.changes))
        self.change_kind = ChangeKind.NONE

    def redo(self) -> None:
        self.fix_change()

        if self.pointer < len(self.changes):
            self.changes[self.pointer].redo()
            self.pointer += 1
            print(f"Redo change {self.changes[self.pointer - 1].kind} {len(self.changes)} ptr {self.pointer}, unfixed={'' if self.current_unfixed_change is None else self.current_unfixed_change.kind}")
            for callback in self.undo_redo_callbacks:
                callback(self.pointer > 0, self.pointer < len(self.changes))
        self.change_kind = ChangeKind.NONE

    # Actions

    def create_new_map(self) -> None:
        tiled_map = TiledMap()
        tiled_map.tilewidth = 16
        tiled_map.tileheight = 16
        tiled_map.width = 64
        tiled_map.height = 64
        foreground_layer = TiledTileLayer(tiled_map)
        foreground_layer.id = 1
        foreground_layer.name = "foreground"
        objects_layer = TiledObjectGroup(tiled_map)
        objects_layer.id = 2
        objects_layer.name = "objects"
        main_layer = TiledTileLayer(tiled_map)
        main_layer.id = 3
        main_layer.name = "main"
        background_layer = TiledTileLayer(tiled_map)
        background_layer.id = 4
        background_layer.name = "background"

        tiled_map.add_layer(foreground_layer)
        tiled_map.add_layer(objects_layer)
        tiled_map.add_layer(main_layer)
        tiled_map.add_layer(background_layer)

        self.tiled_map = tiled_map
        del self.changes[:]
        self.pointer = 0
        self.current_unfixed_change = None
        self.change_kind = ChangeKind.NONE

    def plot(self, x: int, y: int, gid: int) -> None:
        if self.change_kind != ChangeKind.CHANGE_TILED_LAYER:
            self._add_change(TiledTileLayerChange(self))

        self._tiled_layer.data[y][x] = gid
        self.last_change_timestamp = time.time()

    def move_object(self, obj: TiledObject, x: int, y: int) -> None:
        if self.change_kind != ChangeKind.MOVE_AND_RESIZE_OBJECT:
            self._add_change(MoveAndResizeObjectChange(self, obj))

        obj.x = x
        obj.y = y
        self.last_change_timestamp = time.time()

    def resize_object(self, obj: TiledObject, width: int, height: int) -> None:
        if self.change_kind != ChangeKind.MOVE_AND_RESIZE_OBJECT:
            self._add_change(MoveAndResizeObjectChange(self, obj))
        obj.width = width
        obj.height = height
        self.last_change_timestamp = time.time()

    def add_object(self, obj: TiledObject) -> None:
        obj.id = max(map(lambda o: o.id, self._object_layer.objects_id_map.values())) + 1

        self._object_layer.objects_id_map[obj.id] = obj

        self.last_change_timestamp = time.time()

    def delete_object(self, obj: TiledObject) -> None:
        layer = cast(TiledObjectGroup, obj.parent)
        del layer.objects_id_map[obj.id]

        self.last_change_timestamp = time.time()

    def add_element_property(self, element: TiledElement, key: str, value: Any) -> None:
        element.properties[key] = value

        self.last_change_timestamp = time.time()

    def update_element_property(self, element: TiledElement, key: str, value: Any) -> None:
        current_value = element.properties[key]
        if current_value is None:
            element.properties[key] = value
        elif isinstance(current_value, bool):
            element.properties[key] = bool(value)
        elif isinstance(current_value, int):
            element.properties[key] = int(value)
        elif isinstance(current_value, float):
            element.properties[key] = float(value)
        else:
            element.properties[key] = value

        self.last_change_timestamp = time.time()

    def delete_element_property(self, element: TiledElement, key: str) -> None:
        del element.properties[key]

        self.last_change_timestamp = time.time()

    def update_element_attribute(self, element: TiledElement, key: str, value: str) -> None:
        attrs = type(element).ATTRIBUTES
        typ = attrs[key].type if key in attrs else type(getattr(element, key))

        if typ is None:
            setattr(element, key, value)
        elif typ is bool:
            setattr(element, key, bool(value))
        elif typ is int:
            setattr(element, key, int(value))
        elif typ is float:
            setattr(element, key, float(value))
        elif typ is Color:
            if value == "":
                setattr(element, key, None)
            elif len(value) >= 7 and value[0] == "(" and value[-1] == ")":
                s = [f"{int(s.strip()):02x}" for s in value[1:-1].split(",")]
                if len(s) == 3:
                    setattr(element, key, "#" + "".join(s))
                    return
            print(f"Got incorrect color value '{value}'")
        else:
            setattr(element, key, value)

        self.last_change_timestamp = time.time()
