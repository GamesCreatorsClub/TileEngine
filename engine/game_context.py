import importlib
import math
import pygame
from abc import ABC
from itertools import chain
from typing import Optional, Union, cast, Callable, Any, ChainMap

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
from engine.utils import is_close, Size
from engine.tmx import TiledObject

PlayerOrObject = Union[Player, TiledObject]


def in_context(target: Union[Callable, property]) -> Callable:
    if isinstance(target, property):
        target.fget.context_object = True
    else:
        target.context_object = True
    return target


class GameContext(ABC):
    def __init__(self,
                 levels: dict[Union[str, int], Level],
                 left_keys: set = frozenset({pygame.K_LEFT, pygame.K_a}),
                 right_keys: set = frozenset({pygame.K_RIGHT, pygame.K_d}),
                 up_keys: set = frozenset({pygame.K_UP, pygame.K_w}),
                 down_keys: set = frozenset({pygame.K_DOWN, pygame.K_s}),
                 jump_keys: set = frozenset(),
                 gravity_x: float = 0.0,
                 gravity_y: float = 0.0) -> None:

        self._closure_objects_attribute_names = []
        self.visible_levels: dict[Level, LevelTransition] = {}
        self.player = Player()
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = levels
        self.allow_moving = True
        self.allow_colliding = True
        self.player_input_allowed = True
        self.properties: dict[str, Any] = {}

        self.gravity_x = gravity_x
        self.gravity_y = gravity_y

        self.up_keys = up_keys
        self.down_keys = down_keys
        self.left_keys = left_keys
        self.right_keys = right_keys
        self.jump_keys = jump_keys  # {pygame.K_SPACE}

        self.mouse_pressed_pos: Optional[tuple] = None

        self.current_level_context: Optional[LevelContext] = None

        self.base_closure = {
            "Rect": Rect,
            "Player": Player,
            "MoveViewport": MoveViewport,
            "context": self,
            "properties": self.properties,
            "game": self,
            "level": self.level,
            "player": self.player,
            "math": math,
            "pygame": pygame,
            "objects": self.level.objects_by_name,
            "objs": self.level.objects_by_name
        }

        self.closure = self.base_closure
        self._screen_size: Optional[Size] = None

    @property
    def screen_size(self) -> Optional[Size]:
        return self._screen_size

    def _set_screen_size(self, size: Size) -> None:
        self._screen_size = size

    @screen_size.setter
    def screen_size(self, size: Union[Size, tuple[int, int]]) -> None:
        if isinstance(size, Size):
            self._set_screen_size(size)
        else:
            self._set_screen_size(Size(size[0], size[1]))

    def _execute_script(self, script: str, local_env: dict[str, Any]) -> None:
        try:
            exec(script, self.closure, local_env)
        except Exception as e:
            raise Exception(f"Couldn't execute script, got error {e}\n{script}", e)

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
            "level": level,
            **self.base_closure,
            **closure_objects,
            **({name: getattr(level.level_context, name) for name in dir(level.level_context) if hasattr(getattr(level.level_context, name), "context_object")} if level.level_context is not None else {})
        }

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        if self.player_input_allowed:
            player = self.player
            walking_animation = player["walking_animation"]
            player_moved_horizontally = False

            left = any(current_keys[k] for k in self.left_keys)
            right = any(current_keys[k] for k in self.right_keys)
            if left and right:
                player.vx = 0
            elif left:
                walking_animation.turn_left()
                player.vx = -player.speed
            elif right:
                walking_animation.turn_right()
                player.vx = player.speed
            else:
                if self.gravity_x == 0:
                    player.vx = 0

            if player.vx != 0:
                player_moved_horizontally = self.move_object(player, player.vx, 0, test_collisions=True)

            # Normal movement along Y axis
            player_moved_vertically = False
            up = any(current_keys[k] for k in self.up_keys)
            down = any(current_keys[k] for k in self.down_keys)
            jump = any(current_keys[k] for k in self.jump_keys)
            if (jump or up) and down:
                player.vy = 0
                player.jump = 0
            elif jump:
                if (player.jump == 0 and player.on_the_ground) or 0 < player.jump <= player.jump_threshold:
                    player.jump += 1
                    player.vy += -player.jump_strength + 4 * player.jump / player.jump_threshold
                    walking_animation.turn_up()  # TODO turn_jump??
            elif up:
                walking_animation.turn_up()
                player.vy = -player.speed
            elif down:
                walking_animation.turn_down()
                player.vy = player.speed
                player.jump = 0
            else:
                player.jump = 0
                if self.gravity_y == 0:
                    player.vy = 0

            if player.vy != 0:
                player_moved_vertically = self.move_object(player, 0, player.vy, test_collisions=True)

            if len(self.jump_keys):
                if player_moved_vertically:
                    if player.vy < 0:
                        player.on_the_ground = False
                elif player.vy > 0:
                    player.on_the_ground = not player_moved_vertically
                    if not player_moved_vertically:
                        player.hit_velocity = player.vy
                        player.vy = 0

            player.vx = player.vx + self.gravity_x
            player.vy = player.vy + self.gravity_y

            player_moved = player_moved_horizontally or player_moved_vertically
            if player_moved:
                walking_animation.animate_walk()
                self.level.update_map_position(self.player.rect.center)
                self.level.invalidated = True
            else:
                walking_animation.stop_walk()

    def process_mouse_down(self, pos: tuple) -> None:
        self.mouse_pressed_pos = pos
        objs = self.level.objects_at_position(pos)
        for obj in objs:
            if "on_click" in obj.properties:
                self._execute_script(obj.properties["on_click"], {"obj": obj, "pos": pos})

    def process_mouse_up(self, _pos: tuple) -> None:
        self.mouse_pressed_pos = None

    @property
    @in_context
    def tiles_by_name(self) -> ChainMap[str, int]:
        return self.level.map.tiles_by_name

    @property
    @in_context
    def object_by_name(self) -> ChainMap[str, TiledObject]:
        return self.level.map.object_by_name

    @in_context
    def distance_from_player(self, obj: TiledObject) -> float:
        dx = self.player.rect.x - obj.rect.x
        dy = self.player.rect.y - obj.rect.y
        return math.sqrt(dx * dx + dy * dy)

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

        if "on_create" in level.map.properties and "_on_create_executed" not in level.map.properties:
            self._execute_script(level.map.properties["on_create"], {"level": level})
            level.map.properties["_on_create_executed"] = True

        if "on_show" in level.map.properties:
            self._execute_script(level.map.properties["on_show"], {"level": level})

        for obj in self.level.objects:
            if "on_create" in obj.properties:
                self._execute_script(obj.properties["on_create"], {"obj": obj, "level": level})
            if obj.has_create_image():
                obj.create_image_from_property_value()

        if "gravity" in level.map.properties:
            gravity_string = level.map.properties["gravity"]
            if "," in gravity_string:
                x_s, y_s = [s.strip() for s in gravity_string.split(",")]
                self.gravity_x = float(x_s)
                self.gravity_y = float(y_s)
            else:
                self.gravity_y = float(gravity_string)

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
    ) -> tuple[tuple[Union[int, float], Union[int, float]], Optional[CollisionResult]]:

        level = self.level

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

    def test_collisions_with_objects(self, next_rect: Rect, obj: PlayerOrObject, with_objects: dict[TiledObject, Rect]) -> bool:
        object_has_moved = True

        collisions = next_rect.collidedictall(with_objects, values=1)

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
                    elif collided_object.pushable:
                        self.push_object(obj, collided_object)
                        object_has_moved = False if not self.allow_moving else object_has_moved
                    elif collided_object.solid:
                        self.prevent_moving()
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

        return object_has_moved

    @in_context
    def move_object(self, obj: PlayerOrObject, x: float, y: float, test_collisions: bool = False, absolute: bool = False) -> bool:
        def test_if_obj_is_player(object_has_moved: bool) -> None:
            if object_has_moved:
                if obj == self.player:
                    self.level.update_map_position(self.player.rect.center)
                self.level.invalidated = True

        next_rect = obj.next_rect
        next_rect.update(obj.rect)

        if absolute:
            next_rect.x = x
            next_rect.y = y
        else:
            level = self.level
            level_map = level.map

            next_rect.x = min(max(0, int(next_rect.x + x)), level.width - level_map.tilewidth)
            next_rect.y = min(max(0, int(next_rect.y + y)), level.height - level_map.tileheight)

        if isinstance(obj, Player):
            if (next_rect.x < obj.restricted_rect.x
               or next_rect.y < obj.restricted_rect.y
               or next_rect.right > obj.restricted_rect.right
               or next_rect.bottom > obj.restricted_rect.bottom):
                return False

        next_pos, collided_result = self.check_next_position(obj, obj.rect, next_rect)

        next_rect.topleft = next_pos

        object_has_moved = True

        if test_collisions:
            object_has_moved = self.test_collisions_with_objects(next_rect, obj, self.level.objects)

        if object_has_moved:
            if obj == self.player:
                object_has_moved = self.player.move_to(next_rect.topleft)
            else:
                obj.x = next_rect.x
                obj.y = next_rect.y

        if collided_result is None:
            test_if_obj_is_player(object_has_moved)
            return object_has_moved

        gid, tile_rect = next(((gid, r) for gid, r in collided_result.collided_rects() if gid in self.level.on_collision_tiles_properties), (0, None))
        if tile_rect:
            if tile_rect:
                self.on_tile_collision(self.level.on_collision_tiles_properties[gid], tile_rect, obj, next_rect)

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
            scriptlet = obj.properties["on_animate"]
            self._execute_script(scriptlet, {"elapsed_ms": elapsed_ms, "this": obj, "obj": obj})

    def on_tile_collision(self, tile_properties, tile_rect: Rect, obj: PlayerOrObject, next_rect: Rect) -> None:
        try:
            scriptlet = tile_properties["on_collision"]
            self._execute_script(scriptlet, {"obj": obj, "next_rect": next_rect, "tile": tile_properties, "tile_rect": tile_rect})
        finally:
            self.currently_colliding_object = None

    def on_collision(self, this: PlayerOrObject, obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True

        try:
            scriptlet = obj.properties["on_collision"]
            self._execute_script(scriptlet, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_enter(self, this: PlayerOrObject, obj: TiledObject) -> None:
        self.currently_colliding_object = obj

        self.allow_moving = True
        self.allow_colliding = True

        try:
            scriptlet = obj.properties["on_enter"]
            self._execute_script(scriptlet, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_leave(self, this: PlayerOrObject, obj: TiledObject) -> None:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_leave"]
            self._execute_script(scriptlet, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def _undo_collisions(self, obj: Union[Player, TiledObject]) -> None:
        for collided_obj in obj.collisions:
            collided_obj.collisions.remove(self.player)
        obj.collisions.clear()

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
    def select_level(self, name: str, keep_others: bool = False) -> None:
        if not keep_others:
            self.visible_levels.clear()
        self._undo_collisions(self.player)
        self.level.player_object.visible = False
        self.level.invalidated = True

        level = self.all_levels[name]
        self.set_level(level)
        self.prevent_moving()

    @in_context
    def next_level(self, keep_others: bool = False) -> None:
        if not keep_others:
            self.visible_levels.clear()
        self._undo_collisions(self.player)
        self.level.player_object.visible = False
        self.level.invalidated = True

        _, next_level = self._find_next_level()
        self.set_level(next_level)
        self.prevent_moving()

    @in_context
    def previous_level(self, keep_others: bool = False) -> None:
        if not keep_others:
            self.visible_levels.clear()
        self.level.player_object.visible = False
        self.level.invalidated = True

        _, next_level = self._find_prev_level()
        self.set_level(next_level)
        next_level.start(self.player)
        self.prevent_moving()

    @in_context
    def teleport_to_object(self, who: PlayerOrObject, obj_name: str) -> None:
        for obj in self.level.objects:
            if obj.name == obj_name:
                x = obj.rect.centerx
                y = obj.rect.centery
                self.move_object(who, x, y, absolute=True)
                print(f"Teleported {who.name} to {x}, {y}")
                self.prevent_moving()
                self.level.invalidated = True
                return

    @in_context
    def push_object(self, this: TiledObject, obj: TiledObject, test_collisions: bool = True) -> None:
        walking_object = obj["walking_animation"] if "walking_animation" in obj else None

        dx = 0
        dy = 0
        if obj.rect.x < this.next_rect.x < obj.rect.right:
            dx = this.next_rect.x - obj.rect.right
            if walking_object is not None: walking_object.turn_left()
        elif obj.rect.right > this.next_rect.right > obj.rect.x:
            dx = this.next_rect.right - obj.rect.x
            if walking_object is not None: walking_object.turn_right()

        if obj.rect.y < this.next_rect.y < obj.rect.bottom:
            dy = this.next_rect.y - obj.rect.bottom
            if walking_object is not None: walking_object.turn_up()
        elif obj.rect.bottom > this.next_rect.bottom > obj.rect.y:
            dy = this.next_rect.bottom - obj.rect.y
            if walking_object is not None: walking_object.turn_down()

        if abs(dx) > 0 and abs(dy) > 0:
            if abs(dx) < abs(dy):
                dy = 0
            else:
                dx = 0

        self.move_object(obj, dx, dy, test_collisions)
        if walking_object is not None: walking_object.animate_walk()
        self.prevent_moving()

    @in_context
    def record_position(self, obj: TiledObject) -> None:
        obj.properties["startx"] = obj.x
        obj.properties["starty"] = obj.y

    @in_context
    def move_object_away(self, this: TiledObject, obj: TiledObject, at_distance: float, test_collisions: bool = False, above_everything: bool = True) -> None:
        dx = this.rect.x - obj.rect.x
        dy = this.rect.y - obj.rect.y
        d = math.sqrt(dx * dx + dy * dy)
        factor = d / at_distance
        new_dx = dx * factor
        new_dy = dy * factor

        if above_everything:
            this.x += dx - new_dx
            this.y += dy - new_dy
        else:
            self.move_object(this, dx - new_dx, dy - new_dy, test_collisions)

    @in_context
    def move_object_towards(self, this: TiledObject, obj: TiledObject, speed: float, test_collisions: bool = False, above_everything: bool = True) -> None:
        dx = this.rect.x - obj.rect.x
        dy = this.rect.y - obj.rect.y
        d = math.sqrt(dx * dx + dy * dy)
        if d >= 1.0:
            factor = (d - speed) / d
            new_dx = dx * factor
            new_dy = dy * factor

            if above_everything:
                this.next_rect.update(this.rect)
                this.next_rect.x -= dx - new_dx
                this.next_rect.y -= dy - new_dy
                if obj == self.player:
                    object_moved = self.test_collisions_with_objects(obj.rect, obj, {this: this.rect})
                else:
                    # TODO - this means object collided with another object
                    object_moved = True
                if object_moved:
                    this.rect.update(this.next_rect)
            else:
                self.move_object(this, new_dx - dx, new_dy - dy, test_collisions)
