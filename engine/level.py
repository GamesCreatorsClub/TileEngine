from typing import Union, Optional

import pygame
from pygame import Surface, Rect

import pytmx.pytmx
from engine.player import Player, Orientation
from game.utils import clip
from pytmx import TiledMap, TiledTileLayer, TiledObjectGroup, TiledObject, TiledGroupLayer, load_pygame

offscreen_rendering = True


class Level:
    @classmethod
    def load_levels(cls, filename: str) -> list['Level']:
        tmx_data = load_pygame(filename)

        return [Level(tmx_data, i + 1) for i, l in enumerate([l for l in tmx_data.layers if l.name.startswith("group_")])]

    def __init__(self, tiled_map: TiledMap, part_no: int) -> None:
        self.map = tiled_map
        self.tile_width = tiled_map.tilewidth
        self.tile_height = tiled_map.tileheight
        self.width = tiled_map.width * self.tile_width
        self.height = tiled_map.height * self.tile_height

        self.map_rect = Rect(0, 0, 0, 0)
        self.map_rect.width = tiled_map.width * tiled_map.tilewidth
        self.map_rect.height = tiled_map.height * tiled_map.tileheight

        self.part_no = part_no

        self.viewport: Optional[Rect] = None
        self.x_offset = 0
        self.y_offset = 0

        self.layers: list[Union[TiledTileLayer, TiledObjectGroup]] = []
        self.background_layer: Optional[TiledTileLayer] = None
        self.main_layer: Optional[TiledTileLayer] = None
        self.foreground_layer: Optional[TiledTileLayer] = None
        self.over_layer: Optional[TiledTileLayer] = None
        self.objects_layer: Optional[TiledObjectGroup] = None

        self.objects: dict[TiledObject, Rect] = {}
        self.player_object: Optional[TiledObject] = None
        self.player_orientation = Orientation.RIGHT
        self.player_left_animation: list[int] = []
        self.player_right_animation: list[int] = []

        self.invalidated = True

        # initialise level
        # def init(self) -> None:
        self.group = next((
            layer for layer in self.map.layers
            if isinstance(layer, TiledGroupLayer) and layer.name.endswith(f"_{self.part_no}")
        ))

        self.viewport = Rect(*(int(v.strip()) for v in self.group.properties["viewport"].split(",")))
        self.offscreen_surface = Surface(self.viewport.size, pygame.HWSURFACE).convert_alpha()

        del self.layers[:]

        layers = [
            layer for layer in self.group.layers
            if (isinstance(layer, TiledTileLayer) or isinstance(layer, TiledObjectGroup)) and layer.name.endswith(f"_{self.part_no}")
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
                self.objects = {o: o.rect for o in self.objects_layer if o.name != "player"}

        if self.background_layer is not None:
            self.layers.append(self.background_layer)
        if self.main_layer is not None:
            self.layers.append(self.main_layer)

        if self.objects_layer is not None:
            self.layers.append(self.objects_layer)
            self.player_object = next((o for o in self.objects_layer if o.name == "player"), None)
            if self.player_object is None:
                raise ValueError("Missing player object")

            self.player_object.visible = False
            self.update_map_position(self.player_object.rect)

            original_tiled_gid = self.map.tiledgidmap[self.player_object.gid]
            # # decoded_tiled_gid, flags = pytmx.pytmx.decode_gid(original_tiled_gid)

            self.player_orientation = Orientation.LEFT
            for _, f in self.map.gidmap[original_tiled_gid]:
                if f.flipped_horizontally:
                    self.player_orientation = Orientation.RIGHT

            def image_gid(original_tiled_gid: int, tile_flags: pytmx.TileFlags) -> int:
                gid_flag_tuple = original_tiled_gid, tile_flags
                if gid_flag_tuple not in self.map.imagemap:
                    return self.map.register_gid(original_tiled_gid, tile_flags)

                gid, _ = self.map.imagemap[gid_flag_tuple]
                return gid

            for tile_flags, orientation in [(pytmx.TileFlags(0, 0, 0), Orientation.LEFT), (pytmx.TileFlags(1, 0, 0), Orientation.RIGHT)]:
                gid = image_gid(original_tiled_gid, tile_flags)

                if orientation == Orientation.LEFT:
                    self.player_left_animation = [gid]
                else:
                    self.player_right_animation = [gid]

                gid = image_gid(original_tiled_gid + 1, tile_flags)

                if orientation == Orientation.LEFT:
                    self.player_left_animation.append(gid)
                else:
                    self.player_right_animation.append(gid)

            self.map.update_images()

        else:
            raise ValueError("Object layer cannot be None")

        if self.foreground_layer is not None:
            self.layers.append(self.foreground_layer)
        if self.over_layer is not None:
            self.layers.append(self.over_layer)

    def __eq__(self, other) -> bool:
        return self.map.filename == other.map.filename and self.part_no == other.part_no

    def __hash__(self) -> int:
        return self.map.filename.__hash__() ^ self.part_no

    def start(self, player: Player) -> None:
        player.tiled_object = self.player_object
        player.orientation = self.player_orientation
        player.left_animation = self.player_left_animation
        player.right_animation = self.player_right_animation
        self.player_object.visible = True

    def stop(self) -> None:
        self.player_object.visible = False

    def remove_object(self, obj: TiledObject) -> None:
        if obj in self.objects:
            del self.objects[obj]
            self.objects_layer.remove(obj)

    def render_to(self, surface: Surface, xo: int, yo: int) -> None:
        tile_width = self.tile_width
        tile_height = self.tile_height
        for layer in self.layers:
            if isinstance(layer, TiledObjectGroup):
                for obj in layer:
                    if obj.image and obj.visible:
                        surface.blit(obj.image, (obj.x + xo, obj.y + yo))
            else:
                for x, y, image in layer.tiles():
                    surface.blit(image, (x * tile_width + xo, y * tile_height + yo))

    def draw(self, surface: Surface) -> None:
        with clip(surface, self.viewport) as clip_rect:
            if offscreen_rendering[0]:
                if self.invalidated:
                    self.invalidated = False
                    self.offscreen_surface.fill((0, 224, 0))
                    self.render_to(self.offscreen_surface, -self.x_offset, -self.y_offset)
                surface.blit(self.offscreen_surface, self.viewport.topleft)
            else:
                self.render_to(surface, clip_rect.x - self.x_offset, clip_rect.y - self.y_offset)

    def update_map_position(self, player_rect: Rect) -> None:
        def place(screen_half: int, player_pos: float, map_width: int) -> int:
            player_pos = int(player_pos)
            offset = player_pos - screen_half
            if offset < 0: offset = 0
            if offset + 2 * screen_half > map_width: offset = map_width - 2 * screen_half
            return offset

        xo = place(self.viewport.width // 2, player_rect.x, self.map_rect.width)
        yo = place(self.viewport.height // 2, player_rect.y, self.map_rect.height)
        if xo != self.x_offset or yo != self.y_offset:
            self.invalidated = True

        self.x_offset = xo
        self.y_offset = yo
