import importlib
from abc import ABC, abstractmethod
from typing import Optional, Union, cast, Callable

from pygame import Rect, Surface
from pygame.key import ScancodeWrapper

from engine.collision_result import CollisionResult
from engine.level import Level
from engine.level_context import LevelContext
from engine.player import Player
from engine.transitions.fade_in import FadeIn
from engine.transitions.level_transition import LevelTransition
from engine.transitions.move_viewport import MoveViewport
from engine.transitions.render_direct import RenderDirect
from engine.utils import is_close
from engine.pytmx import TiledObject


def in_context(function: Callable) -> Callable:
    function.context_object = True
    return function


class GameContext(ABC):
    closure_objects = {}

    def __init__(self) -> None:
        self.visible_levels: dict[Level, LevelTransition] = {}
        self.player = Player()
        self.player_collision = CollisionResult()
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = {}
        self.allow_moving = True
        self.allow_colliding = True

        self.current_level_context: Optional[LevelContext] = None

        closure_objects = {name: getattr(self, name) for name in dir(GameContext) if hasattr(getattr(self, name), "context_object")}
        self.base_closure = {
            "Rect": Rect,
            "Player": Player,
            "MoveViewport": MoveViewport,
            "context": self,
            "player": self.player,
            **closure_objects
        }

        self.closure = self.base_closure

    @abstractmethod
    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        pass

    def set_level(self, level: Level) -> None:
        self.level = level

        if self.level not in self.visible_levels:
            self.visible_levels[level] = RenderDirect(level)

        module_name = ".".join(self.level.level_context_class_str.split(".")[:-1])
        class_name = self.level.level_context_class_str.split(".")[-1]

        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        level.level_context = class_(self)

        self.closure = {
            **self.base_closure,
            **{name: getattr(level.level_context, name) for name in dir(level.level_context) if hasattr(getattr(level.level_context, name), "context_object")}
        }

    def show_level(self, level: Level, level_transition: Optional[LevelTransition] = None) -> None:
        if level not in self.visible_levels:
            if level_transition is None:
                level_transition = RenderDirect(level)
            self.visible_levels[level] = level_transition

    def draw(self, surface: Surface) -> None:
        for level_transition in [lt for lt in self.visible_levels.values()]:
            replacement = level_transition.draw(surface)
            if replacement is not None:
                if replacement.remove:
                    del self.visible_levels[level_transition.level]
                else:
                    self.visible_levels[level_transition.level] = replacement

    def check_next_position(
            self,
            obj: Union[Player, TiledObject],
            current_rect: Rect,
            next_rect: Rect,
            dx: float, dy: float) -> tuple[tuple[Union[int, float], Union[int, float]], Optional[CollisionResult]]:

        level = self.level
        level_map = level.map

        next_rect.x = min(max(0, next_rect.x + dx), level.width - level_map.tilewidth)
        next_rect.y = min(max(0, next_rect.y + dy), level.width - level_map.tilewidth)

        if obj.collision_result is None:
            obj.collision_result = CollisionResult()
        cr = level.collect_collided(next_rect, obj.collision_result)

        if not cr.has_collided_gids():
            return next_rect.topleft, None

        lx = current_rect.x
        ly = current_rect.y
        rx = next_rect.x
        ry = next_rect.y
        r = Rect((0, 0), next_rect.size)
        changed = False
        while not is_close(lx, rx, ly, ry):
            changed = True
            mx = rx + (lx - rx) / 2
            my = ry + (ly - ry) / 2
            r.x = mx
            r.y = my

            level.collect_collided(r, cr)

            if cr.has_collided_gids():
                rx = mx
                ry = my
            else:
                lx = mx
                ly = my

        if changed and (int(next_rect.x) != int(lx) or int(next_rect.y) != int(ly)):
            next_rect.x = lx
            next_rect.y = ly
            return next_rect.topleft, cr

        return current_rect.topleft, None

    def move_object(self, obj: Union[Player, TiledObject], dx: float, dy: float, test_collisions: bool = False) -> bool:
        next_rect = obj.next_rect
        next_rect.update(obj.rect)

        next_pos, collided_result = self.check_next_position(obj, obj.rect, obj.next_rect, dx, dy)

        next_rect.topleft = next_pos

        object_has_moved = True

        if test_collisions:
            collisions = next_rect.collidedictall(self.level.objects)

            obj_collisions = set(obj.collisions)
            for collision in collisions:
                if collision != obj:
                    self.allow_colliding = True
                    self.allow_moving = True
                    collided_object: TiledObject = cast(TiledObject, collision[0])

                    if collided_object in obj_collisions:
                        obj_collisions.remove(collided_object)
                    else:
                        if "on_enter" in collided_object.properties:
                            self.on_enter(obj, collided_object)
                            object_has_moved = False if not self.allow_moving else object_has_moved

                    if self.allow_colliding:
                        collided_object.collisions.add(obj)
                        obj.collisions.add(collided_object)

                        if "on_collision" in collided_object.properties:
                            self.on_collision(obj, collided_object)
                            object_has_moved = False if not self.allow_moving else object_has_moved

            for collided_object in obj_collisions:
                if obj in collided_object.collisions:
                    collided_object.collisions.remove(obj)
                if "on_leave" in collided_object.properties:
                    self.on_leave(self.player, collided_object)

        if object_has_moved:
            if obj == self.player:
                object_has_moved = self.player.move_to(next_rect.topleft)
            else:
                obj.x = next_rect.x
                obj.y = next_rect.y

        if collided_result is None:
            return object_has_moved

        tiled_map = self.level.map
        g, tile_rect = next(((g, r) for g, r in collided_result.collided_rects() if g in tiled_map.tile_properties and "on_collision" in tiled_map.tile_properties[g]), (0, None))
        if tile_rect:
            if tile_rect:
                self.on_tile_collision(tiled_map.tile_properties[g], tile_rect, obj, next_rect)

            if obj == self.player:
                return self.player.move_to(next_rect.topleft)

            obj.x = next_rect.x
            obj.y = next_rect.y
            return True

        return object_has_moved

    def on_tile_collision(self, tile, tile_rect: Rect, obj: Union[Player, TiledObject], next_rect: Rect) -> None:
        try:
            scriptlet = tile["on_collision"]
            exec(scriptlet, self.closure, {"obj": obj, "next_rect": next_rect, "tile": tile, "tile_rect": tile_rect})
        finally:
            self.currently_colliding_object = None

    def on_collision(self, this: Union[Player, TiledObject], obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True

        try:
            scriptlet = obj.properties["on_collision"]
            exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_enter(self, this: Union[Player, TiledObject], obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True
        self.allow_colliding = True

        try:
            scriptlet = obj.properties["on_enter"]
            exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_leave(self, this: Union[Player, TiledObject], obj: TiledObject) -> None:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_leave"]
            return exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    @in_context
    def prevent_moving(self) -> None:
        self.allow_moving = False

    @in_context
    def prevent_colliding(self) -> None:
        self.allow_colliding = False

    @in_context
    def is_player(self, obj: Union[Player, TiledObject]) -> bool:
        return isinstance(obj, Player)

    @in_context
    def remove_object(self, obj: TiledObject) -> None:
        self.level.remove_object(obj)

    @in_context
    def remove_collided_object(self) -> None:
        self.remove_object(self.currently_colliding_object)

    @in_context
    def show_next_level(self) -> None:
        level = self.all_levels[self.level_no + 1]
        self.remove_object(self.currently_colliding_object)
        self.show_level(level, FadeIn(level))

    @in_context
    def show_previous_level(self) -> None:
        level = self.all_levels[self.level_no - 1]
        self.remove_object(self.currently_colliding_object)
        self.show_level(level, FadeIn(level))

    @in_context
    def next_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True
        next_level = self.all_levels[self.level_no + 1]
        self.set_level(next_level)
        next_level.start(self.player)

    @in_context
    def previous_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True
        next_level = self.all_levels[self.level_no - 1]
        self.set_level(next_level)
        next_level.start(self.player)
