from typing import Optional, cast, Callable, Any

from pygame import Color

from engine.tmx import TiledMap, TiledObjectGroup, BaseTiledLayer, TiledTileLayer, TiledObject, TiledTileset, TiledElement


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

        # for callback in self.selected_layer_callbacks:
        #     callback(current_layer)

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

    def plot(self, x: int, y: int, gid: int) -> None:
        self._tiled_layer.data[y][x] = gid

    def move_object(self, obj: TiledObject, x: int, y: int) -> None:
        obj.x = x
        obj.y = y

    def resize_object(self, obj: TiledObject, width: int, height: int) -> None:
        obj.width = width
        obj.height = height

    def add_object(self, obj: TiledObject) -> None:
        obj.id = max(map(lambda o: o.id, self._object_layer.objects_id_map.values())) + 1

        self._object_layer.objects_id_map[obj.id] = obj

    def delete_object(self, obj: TiledObject) -> None:
        layer = cast(TiledObjectGroup, obj.parent)
        del layer.objects_id_map[obj.id]

    def add_element_property(self, element: TiledElement, key: str, value: Any) -> None:
        element.properties[key] = value

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

    def delete_element_property(self, element: TiledElement, key: str) -> None:
        del element.properties[key]

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
