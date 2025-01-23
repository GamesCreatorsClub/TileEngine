from typing import Optional

from pygame import Rect, Surface
from pygame.font import Font

from editor.actions_controller import ActionsController
from editor.pygame_components import Component
from engine.tmx import TiledTileset, TiledObjectGroup, TiledTileLayer


class InfoPanel(Component):
    def __init__(self,
                 rect: Rect,
                 font: Font,
                 actions_controller: ActionsController) -> None:
        super().__init__(rect)
        self.actions_controller = actions_controller
        self.font = font
        self.layer_text: Optional[Surface] = None
        self.tileset_text: Optional[Surface] = None
        self.actions_controller.current_tileset_callbacks.append(self._current_tileset_callback)
        self.actions_controller.object_layer_callbacks.append(self._object_layer_callback)
        self.actions_controller.tiled_layer_callbacks.append(self._tiled_layer_callback)
        self._object_layer: Optional[TiledObjectGroup] = None
        self._tiled_layer: Optional[TiledTileLayer] = None

    def _current_tileset_callback(self, tileset: Optional[TiledTileset]) -> None:
        if tileset is None:
            self.tileset_text = None
        else:
            self.tileset_text = self.font.render("Tileset: " + tileset.name, False, (0, 0, 0))

    def _update_layer_name(self) -> None:
        if self._tiled_layer is not None:
            self.layer_text = self.font.render("Layer: " + self._tiled_layer.name, True, (0, 0, 0))
        elif self._object_layer is not None:
            self.layer_text = self.font.render("Layer: " + self._object_layer.name, True, (0, 0, 0))
        else:
            self.layer_text = None

    def _object_layer_callback(self, object_layer: Optional[TiledObjectGroup]) -> None:
        self._object_layer = object_layer
        self._update_layer_name()

    def _tiled_layer_callback(self, tiled_layer: Optional[TiledTileLayer]) -> None:
        self._tiled_layer = tiled_layer
        self._update_layer_name()

    def draw(self, surface: Surface) -> None:
        if self.layer_text is not None:
            surface.blit(self.layer_text, (self.rect.x, self.rect.y))
        if self.tileset_text is not None:
            surface.blit(self.tileset_text, (self.rect.x, self.rect.y + self.font.get_height()))
