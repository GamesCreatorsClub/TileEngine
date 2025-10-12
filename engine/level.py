import math
import os.path
from itertools import chain
from typing import Union, Optional, cast, Any, Tuple

import pygame
from pygame import Surface, Rect

from engine.collision_result import CollisionResult
from engine.level_context import LevelContext
from engine.player import Player
from engine.utils import clip
from engine.tmx import TiledMap, TiledTileLayer, TiledObjectGroup, TiledObject, TiledGroupLayer, TileFlags, BaseTiledLayer
from engine.walking_animation import Orientation, WalkingAnimation

offscreen_rendering = True


class ObjectByNameWrapper:
    def __init__(self, objects: dict[TiledObject, Rect]) -> None:
        self.objects = objects

    def __getitem__(self, key: str) -> TiledObject:
        for obj in self.objects:
            if obj.name == key:
                return obj
        raise KeyError(f"No object with name {key}")

    def __setitem__(self, key: str, value: TiledObject) -> None:
        raise NotImplemented()

    def __delitem__(self, key: str, value: TiledObject) -> None:
        raise NotImplemented()


class Level:
    @classmethod
    def load_levels(cls, screen_size: Rect, *filenames: Union[str, dict[str, str]], **named_filenames) -> dict[str, 'Level']:
        def load_file(name: str, filename: str) -> dict[str, 'Level']:

            filename = filename.replace("\\", "/")
            filename = filename.replace("/", os.path.sep)

            tmx_data = TiledMap()
            tmx_data.load(filename)

            if list(tmx_data.layers)[0].name.startswith("group_"):
                return {f"{name}_{i}": Level(screen_size, tmx_data, i + 1) for i, l in enumerate([l for l in tmx_data.layers if l.name.startswith("group_")])}

            return {name: Level(screen_size, tmx_data)}

        def filename_to_name(filename: str) -> str:
            return filename.split(os.path.sep)[-1].split(".")[0]

        name_and_filename_dict = {
            filename_to_name(filename) if isinstance(filename, str) else filename[0]: filename if isinstance(filename, str) else filename[1]
            for filename in filenames
        } | named_filenames

        l = [load_file(name, filename) for name, filename in name_and_filename_dict.items()]

        return dict(chain(*map(dict.items, l)))

    def __init__(self, screen_rect: Rect, tiled_map: TiledMap, part_no: Optional[int] = None) -> None:
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
        self.required_x_offset = 0
        self.required_y_offset = 0
        self.offset_speed = 0
        self.background_colour = (0, 224, 0) if tiled_map.backgroundcolor is None else tiled_map.backgroundcolor

        self.layers: list[Union[TiledTileLayer, TiledObjectGroup]] = []
        self.background_layer: Optional[TiledTileLayer] = None
        self.main_layer: Optional[TiledTileLayer] = None
        self.foreground_layer: Optional[TiledTileLayer] = None
        self.over_layer: Optional[TiledTileLayer] = None
        self.objects_layer: Optional[TiledObjectGroup] = None

        self.objects: dict[TiledObject, Rect] = {}
        self.objects_by_name = ObjectByNameWrapper(self.objects)
        self.player_object: Optional[TiledObject] = None

        self.invalidated = True
        self.always = True

        self.level_context_class_str = tiled_map.properties["level_context"] if "level_context" in tiled_map.properties else None
        self.level_context: Optional[LevelContext] = None

        # initialise level
        self.group = next((
            layer for layer in self.map.layers
            if self.part_no is not None and isinstance(layer, TiledGroupLayer) and layer.name.endswith(f"_{self.part_no}")
        ), tiled_map)

        if "viewport" in self.group.properties:
            self.viewport = Rect(*(int(v.strip()) for v in self.group.properties["viewport"].split(",")))
        else:
            self.viewport = screen_rect
        self.off_screen_viewport = screen_rect

        self.offscreen_surface = Surface(self.viewport.size, pygame.HWSURFACE).convert_alpha()

        del self.layers[:]

        layers: list[BaseTiledLayer] = [
            layer for layer in self.group.layers
            if self.part_no is None or (isinstance(layer, TiledTileLayer) or isinstance(layer, TiledObjectGroup)) and layer.name.endswith(f"_{self.part_no}")
        ]
        self.background_layer: Optional[TiledTileLayer] = None
        self.main_layer: Optional[TiledTileLayer] = None
        self.foreground_layer: Optional[TiledTileLayer] = None
        self.over_layer: Optional[TiledTileLayer] = None
        self.objects_layer: Optional[TiledObjectGroup] = None

        for layer in layers:
            if layer.name.startswith("background"):
                self.background_layer = cast(TiledTileLayer, layer)
            elif layer.name.startswith("main"):
                self.main_layer = cast(TiledTileLayer, layer)
            elif layer.name.startswith("foreground"):
                self.foreground_layer = cast(TiledTileLayer, layer)
            elif layer.name.startswith("over"):
                self.over_layer = cast(TiledTileLayer, layer)
            elif layer.name.startswith("object"):
                self.objects_layer = cast(TiledObjectGroup, layer)
                self.objects.update({o: o.rect for o in self.objects_layer.objects if o.name != "player"})

        if self.background_layer is not None:
            self.layers.append(self.background_layer)
        if self.main_layer is not None:
            self.layers.append(self.main_layer)

        if self.objects_layer is not None:
            self.layers.append(self.objects_layer)
            self.player_object = next((o for o in self.objects_layer.objects if o.name == "player" or o.type == "player"), None)
            if self.player_object.type != "player":
                self.player_object.type = "player"
            if self.player_object is None:
                raise ValueError("Missing player object")

            self.player_object.visible = False
            self.update_map_position(self.player_object.rect.center)

            self._update_object_animations()
        else:
            raise ValueError("Object layer cannot be None")

        if self.foreground_layer is not None:
            self.layers.append(self.foreground_layer)
        if self.over_layer is not None:
            self.layers.append(self.over_layer)

        self.on_collision_tiles_properties: dict[int, dict[str, Any]] = {}  # gid to tile properties where tile properties has 'on_collision' in
        for tile_id in self.map.tiles:
            properties = self.map.tiles[tile_id].properties
            if "on_collision" in properties:
                self.on_collision_tiles_properties[tile_id] = properties

        self.on_animate_objects: list[TiledObject] = [
            obj for obj in self.objects if "on_animate" in obj.properties
        ]

    def _update_object_animations(self) -> None:
        def sorter(t1: tuple) -> int:
            return t1[0]

        object_gids: dict[int, dict[Orientation, list[Tuple[int, int]]]] = {}
        for tile_id in self.map.tiles:

            properties = self.map.tiles[tile_id].properties
            if len(properties) > 0:
                gid = tile_id
                for obj in self.objects_layer.objects:
                    if obj.type in properties:
                        if obj.id not in object_gids:
                            object_gids[obj.id] = {
                                Orientation.LEFT: [],
                                Orientation.RIGHT: [],
                                Orientation.UP: [],
                                Orientation.DOWN: []
                            }

                        orientation_str = properties[obj.type]
                        if orientation_str.startswith("left"):
                            pos = int(orientation_str[5:]) if orientation_str.startswith("left,") else 0
                            object_gids[obj.id][Orientation.LEFT].append((pos, gid))
                        elif orientation_str == "left":
                            object_gids[obj.id][Orientation.LEFT].append((0, gid))
                        elif orientation_str.startswith("right"):
                            pos = int(orientation_str[6:]) if orientation_str.startswith("right,") else 0
                            object_gids[obj.id][Orientation.RIGHT].append((pos, gid))
                        elif orientation_str == "right":
                            object_gids[obj.id][Orientation.RIGHT].append((0, gid))
                        elif orientation_str.startswith("up,"):
                            object_gids[obj.id][Orientation.UP].append((int(orientation_str[3:]), gid))
                        elif orientation_str == "up":
                            object_gids[obj.id][Orientation.UP].append((0, gid))
                        elif orientation_str.startswith("down,"):
                            object_gids[obj.id][Orientation.DOWN].append((int(orientation_str[5:]), gid))
                        elif orientation_str == "down":
                            object_gids[obj.id][Orientation.DOWN].append((0, gid))

        for obj_id in object_gids:
            obj = self.objects_layer.objects_id_map[obj_id]

            object_gids[obj_id][Orientation.LEFT].sort(key=sorter)
            left: list[int] = [t[1] for t in object_gids[obj_id][Orientation.LEFT]]
            object_gids[obj_id][Orientation.RIGHT].sort(key=sorter)
            right: list[int] = [t[1] for t in object_gids[obj_id][Orientation.RIGHT]]
            object_gids[obj_id][Orientation.UP].sort(key=sorter)
            up: list[int] = [t[1] for t in object_gids[obj_id][Orientation.UP]]
            object_gids[obj_id][Orientation.DOWN].sort(key=sorter)
            down: list[int] = [t[1] for t in object_gids[obj_id][Orientation.DOWN]]

            if len(left) > len(right):
                right += [self.map.register_gid(left[i], TileFlags(True, False, False)) for i in range(len(left) - len(right))]

            if len(right) > len(left):
                left += [self.map.register_gid(right[i], TileFlags(True, False, False)) for i in range(len(right) - len(left))]

            original_tiled_gid = obj.gid

            walking_animation = WalkingAnimation(obj)
            walking_animation.left_animation[:] = left
            walking_animation.right_animation[:] = right
            walking_animation.up_animation[:] = up
            walking_animation.down_animation[:] = down

            if original_tiled_gid in up:
                walking_animation.orientation = Orientation.UP
            elif original_tiled_gid in down:
                walking_animation.orientation = Orientation.DOWN
            elif original_tiled_gid in right:
                walking_animation.orientation = Orientation.RIGHT
            else:
                walking_animation.orientation = Orientation.LEFT

            if len(walking_animation.left_animation) == 0: walking_animation.left_animation.append(obj.tile)
            if len(walking_animation.right_animation) == 0: walking_animation.right_animation.append(obj.tile)
            if len(walking_animation.up_animation) == 0: walking_animation.up_animation.append(obj.tile)
            if len(walking_animation.down_animation) == 0: walking_animation.down_animation.append(obj.tile)

            obj["walking_animation"] = walking_animation

    def __eq__(self, other) -> bool:
        return self.map.filename == other.map.filename and self.part_no == other.part_no

    def __hash__(self) -> int:
        return self.map.filename.__hash__() ^ (self.part_no if self.part_no is not None else 0)

    def start(self, player: Player) -> None:
        player.tiled_object = self.player_object

        player.restricted_rect.update(0, 0, self.map.pixel_width, self.map.pixel_height)
        self.player_object.visible = True

    def stop(self) -> None:
        self.player_object.visible = False

    def remove_object(self, obj: TiledObject) -> None:
        if obj in self.objects:
            del self.objects[obj]
            del self.objects_layer.objects_id_map[obj.id]

    def objects_at_position(self, pos: tuple) -> list[TiledObject]:
        screen_pos = Rect(0, 0, 0, 0)
        res = []
        for obj in self.objects:
            screen_pos.update(obj.rect)
            screen_pos.move_ip(-self.x_offset, -self.y_offset)
            if screen_pos.collidepoint(pos[0], pos[1]):
                res.append(obj)
        return res

    def render_to(self, surface: Surface, xo: int, yo: int) -> None:
        for layer in self.layers:
            if layer.visible:
                # if offscreen_rendering:
                layer.draw(surface, self.off_screen_viewport, xo, yo)

    def draw(self, surface: Surface) -> None:
        with clip(surface, self.viewport) as clip_rect:
            if offscreen_rendering:
                if self.always or self.invalidated:
                    self.invalidated = False
                    self.offscreen_surface.fill(self.background_colour)
                    self.render_to(self.offscreen_surface, -self.x_offset, -self.y_offset)
                surface.blit(self.offscreen_surface, self.viewport.topleft)
            else:
                self.render_to(surface, clip_rect.x - self.x_offset, clip_rect.y - self.y_offset)

    def update_map_position(self, xy: tuple[int, int], speed: int = 0) -> None:
        def place(screen_half: int, player_pos: float, map_width: int) -> int:
            player_pos = int(player_pos)
            offset = player_pos - screen_half
            if offset < 0: offset = 0
            if offset + 2 * screen_half > map_width: offset = map_width - 2 * screen_half
            return offset

        if self.map_rect.width < self.viewport.width:
            xo = -(self.viewport.width - self.map_rect.width) // 2
        else:
            xo = place(self.viewport.width // 2, xy[0], self.map_rect.width)

        if self.map_rect.height < self.viewport.height:
            yo = -(self.viewport.height - self.map_rect.height) // 2
        else:
            yo = place(self.viewport.height // 2, xy[1], self.map_rect.height)

        if xo != self.x_offset or yo != self.y_offset:
            self.invalidated = True

        self.offset_speed = speed

        self.required_x_offset = int(xo)
        self.required_y_offset = int(yo)
        if speed <= 0:
            self.x_offset = int(xo)
            self.y_offset = int(yo)
        else:
            self.move_offset()

    def move_offset(self) -> None:
        xo = self.required_x_offset
        yo = self.required_y_offset
        speed = self.offset_speed

        d = math.sqrt((self.x_offset - xo) * (self.x_offset - xo) + (self.y_offset - yo) * (self.y_offset - yo))
        if d > 0:
            ratio = speed / d if speed < d else 1
            self.x_offset = int(xo) if abs(xo - self.x_offset) < 1 else int(self.x_offset + (xo - self.x_offset) * ratio)
            self.y_offset = int(yo) if abs(yo - self.y_offset) < 1 else int(self.y_offset + (yo - self.y_offset) * ratio)

    def collect_collided(self, rect: Rect, collision_result: CollisionResult) -> 'CollisionResult':
        collision_result.total = 0

        tiled_map = self.map
        background_layer = self.background_layer
        main_layer = self.main_layer
        level_map = self.map
        t_w = level_map.tilewidth
        t_h = level_map.tileheight

        t_col = rect.x // t_w
        t_row = rect.y // t_h
        start_col = t_col

        t_x = t_col * t_w
        t_y = t_row * t_h

        try:
            while t_y + t_h >= rect.y and t_y < rect.bottom and t_row < self.map.height:
                while t_x + t_w > rect.x and t_x < rect.right and t_col < self.map.width:
                    collision_result.rects[collision_result.total].update(t_x, t_y, t_w, t_h)
                    collision_result.gids[collision_result.total] = main_layer.data[t_row][t_col]
                    collision_result.total += 1

                    background_gid = background_layer.data[t_row][t_col]
                    if background_gid in tiled_map.tiles and "colliders" in tiled_map.tiles[background_gid].properties:
                        colliders: list[TiledObject] = tiled_map.tiles[background_gid].properties["colliders"]
                        collided_rect = next((r for r in map(lambda o: o.rect.move(t_x, t_y), colliders) if rect.colliderect(r)), None)
                        if collided_rect is not None:
                            collision_result.rects[collision_result.total].update(collided_rect)
                            collision_result.gids[collision_result.total] = background_gid
                            collision_result.total += 1

                    t_col += 1
                    t_x = t_col * t_w
                t_col = start_col
                t_row += 1
                t_x = t_col * t_w
                t_y = t_row * t_h

        except IndexError as e:
            raise IndexError(f"[{t_row}][{t_col}]", e)

        return collision_result
