from typing import Union, Optional

import pygame
from pygame import Surface, Rect

import pytmx.pytmx
from engine.player import Player, Orientation
from game.utils import clip
from pytmx import TiledMap, TiledTileLayer, TiledObjectGroup, load_pygame
from pytmx.pytmx import TiledGroupLayer

offscreen_rendering = False


class Level:
    def __init__(self, tiled_map: TiledMap) -> None:
        self.map = tiled_map
        self.viewport: Optional[Rect] = None
        self._level_part = 1
        self.tile_width = tiled_map.tilewidth
        self.tile_height = tiled_map.tileheight
        self.layers: list[Union[TiledTileLayer, TiledObjectGroup]] = tiled_map.layers
        self.group: Optional[TiledGroupLayer] = None
        self.background_layer: Optional[TiledTileLayer] = None
        self.main_layer: Optional[TiledTileLayer] = None
        self.foreground_layer: Optional[TiledTileLayer] = None
        self.over_layer: Optional[TiledTileLayer] = None
        self.objects_layer: Optional[TiledObjectGroup] = None
        self.width = tiled_map.width * self.tile_width
        self.height = tiled_map.height * self.tile_height

        self.offscreen_surface: Optional[Surface] = None
        self.last_x_offset = -1
        self.last_y_offset = -1

    @classmethod
    def load_level(cls, filename: str) -> 'Level':
        tmx_data = load_pygame(filename)

        return Level(tmx_data)

    @property
    def level_part(self) -> int:
        return self._level_part

    def set_level_part(self, part: int, player: Player) -> None:
        self._level_part = part

        self.group = next((
            layer for layer in self.map.layers
            if isinstance(layer, TiledGroupLayer) and layer.name.endswith(f"_{part}")
        ))

        self.viewport = Rect(*(int(v.strip()) for v in self.group.properties["viewport"].split(",")))
        self.offscreen_surface = Surface(self.viewport.size, pygame.HWSURFACE)

        del self.layers[:]

        layers = [
            layer for layer in self.group.layers
            if (isinstance(layer, TiledTileLayer) or isinstance(layer, TiledObjectGroup)) and layer.name.endswith(f"_{part}")
        ]
        self.background_layer = None
        self.main_layer = None
        self.foreground_layer = None
        self.over_layer = None
        self.objects_layer = None

        for layer in layers:
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

        if self.background_layer is not None:
            self.layers.append(self.background_layer)
        if self.main_layer is not None:
            self.layers.append(self.main_layer)

        if self.objects_layer is not None:
            self.layers.append(self.objects_layer)
            player_object = next((o for o in self.objects_layer if o.name == "player"), None)
            if player_object is None:
                raise ValueError("Missing player object")

            player.orientation = Orientation.LEFT
            player.tiled_object = player_object
            original_tiled_gid = self.map.tiledgidmap[player_object.gid]
            decoded_tiled_gid, flags = pytmx.pytmx.decode_gid(original_tiled_gid)
            for _, f in self.map.gidmap[original_tiled_gid]:
                if f.flipped_horizontally:
                    player.orientation = Orientation.RIGHT

            def image_gid(original_tiled_gid: int, tile_flags: pytmx.TileFlags) -> int:
                gid_flag_tuple = original_tiled_gid, tile_flags
                if gid_flag_tuple not in self.map.imagemap:
                    return self.map.register_gid(original_tiled_gid, tile_flags)

                gid, _ = self.map.imagemap[gid_flag_tuple]
                return gid

            for tile_flags, orientation in [(pytmx.TileFlags(0, 0, 0), Orientation.LEFT), (pytmx.TileFlags(1, 0, 0), Orientation.RIGHT)]:
                gid = image_gid(original_tiled_gid, tile_flags)

                if orientation == Orientation.LEFT:
                    player.left_animation = [gid]
                else:
                    player.right_animation = [gid]

                gid = image_gid(original_tiled_gid + 1, tile_flags)

                if orientation == Orientation.LEFT:
                    player.left_animation.append(gid)
                else:
                    player.right_animation.append(gid)

            self.map.update_images()

        else:
            raise ValueError("Object layer cannot be None")

        if self.foreground_layer is not None:
            self.layers.append(self.foreground_layer)
        if self.over_layer is not None:
            self.layers.append(self.over_layer)

        return

    def draw(self, surface: Surface, x_offset: int, y_offset: int) -> None:

        with clip(surface, self.viewport) as clip_rect:
            xo = clip_rect.x - x_offset
            yo = clip_rect.y - y_offset

            def render_all(surface: Surface) -> None:
                for layer in self.layers:
                    if isinstance(layer, TiledObjectGroup):
                        for obj in layer:
                            if obj.image:
                                surface.blit(obj.image, (obj.x + xo, obj.y + yo))
                    else:
                        for x, y, image in layer.tiles():
                            surface.blit(image, (x * self.tile_width + xo, y * self.tile_height + yo))

            if offscreen_rendering:
                if self.last_x_offset != x_offset or self.last_y_offset != y_offset:
                    self.last_x_offset = x_offset
                    self.last_y_offset = y_offset

                    self.offscreen_surface.fill((0, 224, 0))
                    render_all(self.offscreen_surface)
                surface.blit(self.offscreen_surface, (0, 0))
            else:
                render_all(surface)
