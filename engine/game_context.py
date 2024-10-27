import importlib
from abc import ABC, abstractmethod
from itertools import chain
from typing import Optional, Union, cast, Callable, Any

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


PlayerOrObject = Union[Player, TiledObject]


def in_context(target: Union[Callable, property]) -> Callable:
    if isinstance(target, property):
        target.fget.context_object = True
    else:
        target.context_object = True
    return target


class GameContext(ABC):
    def __init__(self, levels: dict[Union[str, int], Level]) -> None:
        self._closure_objects_attribute_names = []
        self.visible_levels: dict[Level, LevelTransition] = {}
        self.player = Player()
        self.player_collision = CollisionResult()
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = levels
        self.allow_moving = True
        self.allow_colliding = True
        self.player_input_allowed = True

        self.mouse_pressed_pos: Optional[tuple] = None

        self.current_level_context: Optional[LevelContext] = None

        self.base_closure = {
            "Rect": Rect,
            "Player": Player,
            "MoveViewport": MoveViewport,
            "context": self,
            "game": self,
            "player": self.player
        }

        self.closure = self.base_closure

    def _add_attribute_name(self, name: str) -> None:
        self._closure_objects_attribute_names.append(name)

    def calculate_closure(self, level: Level) -> dict[str, Any]:
        closure_objects = {
            name: getattr(self, name)
            for name in chain(dir(self), self._closure_objects_attribute_names)
            if (name in self._closure_objects_attribute_names or
                hasattr(
                    getattr(self, name),
                    "context_object"
                ) or (
                    hasattr(self, name)
                    and isinstance(getattr(self, name), property)
                    and hasattr(getattr(self, name).fget, "context_object")
                ) or (
                    hasattr(type(self), name)
                    and isinstance(getattr(type(self), name), property)
                    and hasattr(getattr(type(self), name).fget, "context_object")
                ))
        }
        return {
            **self.base_closure,
            **closure_objects,
            **({name: getattr(level.level_context, name) for name in dir(level.level_context) if hasattr(getattr(level.level_context, name), "context_object")} if level.level_context is not None else {})
        }

    @abstractmethod
    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        pass

    def process_mouse_down(self, pos: tuple) -> None:
        self.mouse_pressed_pos = pos
        objs = self.level.objects_at_position(pos)
        for obj in objs:
            if "on_click" in obj.properties:
                exec(obj.properties["on_click"], self.closure, {"pos": pos})

    def process_mouse_up(self, _pos: tuple) -> None:
        self.mouse_pressed_pos = None

    @in_context
    def set_player_input_allowed(self, allowed) -> None:
        self.player_input_allowed = allowed

    def set_level(self, level: Level) -> None:
        self.level = level

        level.start(self.player)

        if self.level not in self.visible_levels:
            self.visible_levels[level] = RenderDirect(level)

        if level.level_context_class_str is not None:
            module_name = ".".join(level.level_context_class_str.split(".")[:-1])
            class_name = level.level_context_class_str.split(".")[-1]

            module = importlib.import_module(module_name)
            class_ = getattr(module, class_name)
            level.level_context = class_(self)

        self.closure = self.calculate_closure(level)

        # Default resets
        self.player_input_allowed = True

        if "on_show" in level.map.properties:
            exec(level.map.properties["on_show"], self.closure, {"level": level})

    def show_level(self, level: Level, level_transition: Optional[LevelTransition] = None, activate: bool = False) -> None:
        if level not in self.visible_levels:
            if level_transition is None:
                level_transition = RenderDirect(level)
            self.visible_levels[level] = level_transition
        if activate:
            self.set_level(level)

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
            obj: PlayerOrObject,
            current_rect: Rect,
            next_rect: Rect,
            x: float, y: float,
            absolute: bool = False
    ) -> tuple[tuple[Union[int, float], Union[int, float]], Optional[CollisionResult]]:

        level = self.level
        level_map = level.map

        if absolute:
            next_rect.x = x
            next_rect.y = y
        else:
            next_rect.x = min(max(0, next_rect.x + x), level.width - level_map.tilewidth)
            next_rect.y = min(max(0, next_rect.y + y), level.width - level_map.tilewidth)

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

    @in_context
    def move_object(self, obj: PlayerOrObject, x: float, y: float, test_collisions: bool = False, absolute: bool = False) -> bool:
        def test_if_obj_is_player(object_has_moved: bool) -> None:
            if obj == self.player:
                self.level.update_map_position(self.player.rect)
            if object_has_moved:
                self.level.invalidated = True

        next_rect = obj.next_rect
        next_rect.update(obj.rect)

        next_pos, collided_result = self.check_next_position(obj, obj.rect, obj.next_rect, x, y, absolute=absolute)

        next_rect.topleft = next_pos

        object_has_moved = True

        if test_collisions:
            collisions = next_rect.collidedictall(self.level.objects)

            obj_collisions = set(obj.collisions)
            for collision in collisions:
                collided_object: TiledObject = cast(TiledObject, collision[0])
                if collided_object.visible and collided_object != obj:
                    self.allow_colliding = True
                    self.allow_moving = True

                    if collided_object in obj_collisions:
                        obj_collisions.remove(collided_object)
                    else:
                        if "on_enter" in collided_object.properties:
                            self.on_enter(obj, collided_object)
                            object_has_moved = False if not self.allow_moving else object_has_moved

                    if object_has_moved and self.allow_colliding:
                        collided_object.collisions.add(obj)
                        obj.collisions.add(collided_object)

                        if "on_collision" in collided_object.properties:
                            self.on_collision(obj, collided_object)
                            object_has_moved = False if not self.allow_moving else object_has_moved
                    else:
                        object_has_moved = False

            for collided_object in obj_collisions:
                if obj in collided_object.collisions:
                    collided_object.collisions.remove(obj)
                    obj.collisions.remove(collided_object)
                if "on_leave" in collided_object.properties:
                    self.on_leave(self.player, collided_object)

        if object_has_moved:
            if obj == self.player:
                object_has_moved = self.player.move_to(next_rect.topleft)
            else:
                obj.x = next_rect.x
                obj.y = next_rect.y

        if collided_result is None:
            test_if_obj_is_player(object_has_moved)
            return object_has_moved

        g, tile_rect = next(((g, r) for g, r in collided_result.collided_rects() if g in self.level.on_collision_tiles_properties), (0, None))
        if tile_rect:
            if tile_rect:
                self.on_tile_collision(self.level.on_collision_tiles_properties[g], tile_rect, obj, next_rect)

            if obj == self.player:
                object_has_moved = self.player.move_to(next_rect.topleft)
                test_if_obj_is_player(object_has_moved)
                return object_has_moved

            obj.x = next_rect.x
            obj.y = next_rect.y
            test_if_obj_is_player(True)
            return True

        test_if_obj_is_player(object_has_moved)
        return object_has_moved

    def animate(self, elapsed_ms: int) -> None:
        for obj in self.level.on_animate_objects:
            scriplet = obj.properties["on_animate"]
            exec(scriplet, self.closure, {"elapsed_ms": elapsed_ms, "this": obj})

    def on_tile_collision(self, tile, tile_rect: Rect, obj: PlayerOrObject, next_rect: Rect) -> None:
        try:
            scriptlet = tile["on_collision"]
            exec(scriptlet, self.closure, {"obj": obj, "next_rect": next_rect, "tile": tile, "tile_rect": tile_rect})
        finally:
            self.currently_colliding_object = None

    def on_collision(self, this: PlayerOrObject, obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True

        try:
            scriptlet = obj.properties["on_collision"]
            exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_enter(self, this: PlayerOrObject, obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True
        self.allow_colliding = True

        try:
            scriptlet = obj.properties["on_enter"]
            exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_leave(self, this: PlayerOrObject, obj: TiledObject) -> None:
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
    def is_player(self, obj: PlayerOrObject) -> bool:
        return isinstance(obj, Player)

    @in_context
    def remove_object(self, obj: TiledObject) -> None:
        self.level.remove_object(obj)

    @in_context
    def remove_collided_object(self) -> None:
        self.remove_object(self.currently_colliding_object)

    def _find_next_level(self) -> tuple[str, Level]:
        current_key, _ = next(filter(lambda t: t[1] == self.level, self.all_levels.items()))
        all_keys = [k for k in self.all_levels.keys()]
        index = all_keys.index(current_key)
        next_key = all_keys[index + 1]
        return next_key, self.all_levels[next_key]

    def _find_prev_level(self) -> tuple[str, Level]:
        current_key, _ = next(filter(lambda t: t[1] == self.level, self.all_levels.items()))
        all_keys = [k for k in self.all_levels.keys()]
        index = all_keys.index(current_key)
        next_key = all_keys[index - 1]
        return next_key, self.all_levels[next_key]

    @in_context
    def show_next_level(self) -> None:
        _, level = self._find_next_level()
        self.remove_object(self.currently_colliding_object)
        self.show_level(level, FadeIn(level))

    @in_context
    def show_previous_level(self) -> None:
        _, level = self._find_prev_level()
        self.remove_object(self.currently_colliding_object)
        self.show_level(level, FadeIn(level))

    @in_context
    def next_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True

        _, next_level = self._find_next_level()
        self.set_level(next_level)
        next_level.start(self.player)

    @in_context
    def previous_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True

        _, next_level = self._find_prev_level()
        self.set_level(next_level)
        next_level.start(self.player)

    @in_context
    def teleport_to_object(self, who: PlayerOrObject, obj_name: str) -> None:
        for obj in self.level.objects:
            if obj.name == obj_name:
                x = obj.rect.x + (obj.rect.width - who.rect.width) // 2
                y = obj.rect.y + (obj.rect.height - who.rect.height) // 2
                self.move_object(who, x, y, absolute=True)
                print(f"Teleported to {x}, {y}")
                self.prevent_moving()
                return
