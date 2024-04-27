from typing import Union, Optional, Tuple

import pygame
from pygame import Surface, Rect
from pytmx import TiledMap, TiledTileLayer, TiledObjectGroup, load_pygame
from pytmx.pytmx import TiledGroupLayer

offscreen_rendering = False


class Level:
    def __init__(self, map: TiledMap) -> None:
        self.map = map
        self.viewport: Optional[Rect] = None
        self.level_part = 1
        self.tile_width = map.tilewidth
        self.tile_height = map.tileheight
        self.layers: list[Union[TiledTileLayer, TiledObjectGroup]] = map.layers
        self.layer_group: Optional[TiledGroupLayer] = None
        self.background_layer: Optional[TiledTileLayer] = None
        self.main_layer: Optional[TiledTileLayer] = None
        self.foreground_layer: Optional[TiledTileLayer] = None
        self.over_layer: Optional[TiledTileLayer] = None
        self.objects_layer: Optional[TiledObjectGroup] = None

        self.offscreen_surface = Surface(self.viewport.size, pygame.HWSURFACE)
        self.last_x_offset = -1
        self.last_y_offset = -1

    @classmethod
    def load_level(cls, filename: str) -> 'Level':
        tmx_data = load_pygame(filename)

        level = Level(tmx_data)
        level.level_part = 1
        return level

    @property
    def level_part(self) -> int:
        return self._level_part

    @level_part.setter
    def level_part(self, part: int) -> None:
        self._level_part = part

        self.layer_group = next((
            l for l in self.map.layers
            if isinstance(l, TiledGroupLayer) and l.name.endswith(f"_{part}")
        ))

        self.viewport = Rect(*(int(v.strip()) for v in self.layer_group.properties["viewport"].split(",")))

        self.layers = [
            l for l in self.map.layers
            if (isinstance(l, TiledTileLayer) or isinstance(l, TiledObjectGroup)) and l.name.endswith(f"_{part}")
        ]
        for layer in self.layers:
            if layer.name.startswith("background"):
                self.background_layer = layer
            elif layer.name.startswith("main"):
                self.main_layer = layer
            elif layer.name.startswith("foreground"):
                self.foreground_layer = layer
            elif layer.name.startswith("over"):
                self.over_layer = layer
            elif layer.name.startswith("object"):
                self.objects_layer = layer

    def draw(self, surface: Surface, x_offset: int, y_offset: int) -> None:
        def render_all(surface: Surface, x_offset: int, y_offset: int) -> None:
            for layer in self.layers:
                if isinstance(layer, TiledObjectGroup):
                    for object in layer:
                        surface.blit(object.image, (object.x - x_offset, object.y - y_offset))
                else:
                    for x, y, image in layer.tiles():
                        surface.blit(image, (x * self.tile_width - x_offset, y * self.tile_height - y_offset))

        if offscreen_rendering:
            if self.last_x_offset != x_offset or self.last_y_offset != y_offset:
                self.last_x_offset = x_offset
                self.last_y_offset = y_offset

                self.offscreen_surface.fill((0, 224, 0))
                render_all(self.offscreen_surface, x_offset, y_offset)
            surface.blit(self.offscreen_surface, (0, 0))
        else:
            render_all(surface, x_offset, y_offset)
