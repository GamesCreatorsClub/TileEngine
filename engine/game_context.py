import importlib
from typing import Optional, Union, cast, Callable

import pygame
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
from pytmx import TiledObject


def in_context(function: Callable) -> Callable:
    function.context_object = True
    return function


class GameContext:
    closure_objects = {}

    def __init__(self) -> None:
        self.visible_levels: dict[Level, LevelTransition] = {}
        self.player = Player()
        self.player_collision = CollisionResult()
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = {}

        self.current_level_context: Optional[LevelContext] = None

        self.xo = 0
        self.yo = 0

        closure_objects = {name: getattr(self, name) for name in dir(GameContext) if hasattr(getattr(self, name), "context_object")}
        self.base_closure = {
            "Rect": Rect,
            "Player": Player,
            "MoveViewport": MoveViewport,
            "context": self,
            **closure_objects
        }

        self.closure = self.base_closure

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

    def process_keys(self, _previous_keys: ScancodeWrapper, current_keys: ScancodeWrapper) -> None:
        player = self.player
        player_moved_horizotanlly = False
        if current_keys[pygame.K_LEFT] and current_keys[pygame.K_RIGHT]:
            player.vx = 0
        elif current_keys[pygame.K_LEFT]:
            self.player.turn_left()
            player.vx = -player.player_speed
            # player_moved = self.move_player(-player.player_speed, 0)
        elif current_keys[pygame.K_RIGHT]:
            self.player.turn_right()
            player.vx = player.player_speed
        else:
            player.vx = 0

        if player.vx != 0:
            player_moved_horizotanlly = self.move_player(player.vx, 0)

        if current_keys[pygame.K_UP] and current_keys[pygame.K_DOWN]:
            player.jump = 0
        elif current_keys[pygame.K_UP]:
            if (player.jump == 0 and player.on_the_ground) or 0 < player.jump <= player.jump_treshold:
                player.jump += 1
                player.vy += -5 + 4 * player.jump / player.jump_treshold
        elif current_keys[pygame.K_DOWN]:
            player.jump = 0
        else:
            player.jump = 0

        player.vy = player.vy + 2  # 2 is gravity

        player_moved_vertically = self.move_player(0, player.vy)
        if player_moved_vertically:
            if player.vy < 0:
                player.on_the_ground = False
        elif player.vy > 0:
            player.on_the_ground = not player_moved_vertically
            if not player_moved_vertically:
                player.hit_velocity = player.vy
                player.vy = 0
        player_moved = player_moved_horizotanlly or player_moved_vertically

        if player_moved:
            self.player.animate_walk()
            self.level.update_map_position(self.player.rect)
            self.level.invalidated = True
        else:
            self.player.stop_walk()

    def check_next_position(
            self,
            current_rect: Rect,
            next_rect: Rect,
            dx: float, dy: float) -> tuple[tuple[Union[int, float], Union[int, float]], Optional[CollisionResult]]:

        level = self.level
        level_map = level.map

        next_rect.x = min(max(0, next_rect.x + dx), level.width - level_map.tilewidth)
        next_rect.y = min(max(0, next_rect.y + dy), level.width - level_map.tilewidth)

        cr = self.player_collision.collect(next_rect, level)

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

            cr.collect(r, level)

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

        return next_rect.topleft, None

    def move_player(self, dx: float, dy: float) -> bool:
        player = self.player
        next_rect = player.next_rect

        next_pos, collided_result = self.check_next_position(player.rect, player.next_rect, dx, dy)

        next_rect.topleft = next_pos

        collisions = next_rect.collidedictall(self.level.objects)

        player_has_moved = True

        player_collisions = set(player.collisions)
        for collision in collisions:
            collided_object: TiledObject = cast(TiledObject, collision[0])
            if collided_object in player_collisions:
                player_collisions.remove(collided_object)
            else:
                if "on_enter" in collided_object.properties:
                    # TODO get return value and see if there's way to prevent movement
                    r = self.on_enter(player, collided_object)
                    player_has_moved = False if r is not None and not r else player_has_moved
                collided_object.collisions.add(player)
                player.collisions.add(collided_object)

            if "on_collision" in collided_object.properties:
                r = self.on_collision(self.player, collided_object)
                player_has_moved = False if r is not None and not r else player_has_moved

        for collided_object in player_collisions:
            if player in collided_object.collisions:
                collided_object.collisions.remove(player)
            if "on_leave" in collided_object.properties:
                r = self.on_leave(self.player, collided_object)
                player_has_moved = False if r is not None and not r else player_has_moved

        player_has_moved = self.player.move_to(next_rect.topleft) if player_has_moved else False

        if collided_result is None:
            return player_has_moved

        tiled_map = self.level.map
        _, drop_rect = next(((g, r) for g, r in collided_result.collided_rects() if g in tiled_map.tile_properties and "drop" in tiled_map.tile_properties[g]), (0, None))
        if drop_rect:
            self.player.vy = 2
            next_rect.y += self.player.vy
            next_rect.x += (drop_rect.midtop[0] - next_rect.midtop[0])

            return self.player.move_to(next_rect.topleft)

        return player_has_moved

    def on_collision(self, this: Union[Player, TiledObject], obj: TiledObject) -> Optional[bool]:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_collision"]
            return exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_enter(self, this: Union[Player, TiledObject], obj: TiledObject) -> Optional[bool]:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_enter"]
            return exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def on_leave(self, this: Union[Player, TiledObject], obj: TiledObject) -> Optional[bool]:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_leave"]
            return exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

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
    def next_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True
        next_level = self.all_levels[self.level_no + 1]
        self.set_level(next_level)
        next_level.start(self.player)
