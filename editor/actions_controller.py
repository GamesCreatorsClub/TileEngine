from typing import Optional, cast, Callable

from engine.tmx import TiledMap, TiledObjectGroup, BaseTiledLayer, TiledTileLayer, TiledObject, TiledTileset


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
