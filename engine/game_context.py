from typing import Optional, Union, cast, Generator, Any, Callable

from pygame import Rect

from engine.engine import Engine
from engine.level import Level
from engine.player import Player
from engine.transitions.fade_in import FadeIn
from engine.transitions.move_viewport import MoveViewport
from game.utils import is_close
from pytmx import TiledObject


def in_context(function: Callable) -> Callable:
    function.context_object = True
    return function


class GameContext:
    closure_objects = {}

    def __init__(self, engine: Engine) -> None:
        self.player = Player()
        self.engine = engine
        self.engine.player = self.player
        self.engine.move_player = self.move_player
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = {}

        # closure_objects_1 = {k[2:]: getattr(self, k) for k in dir(self) if k.startswith("l_")}
        # closure_objects = {name[2:]: method for name, method in GameContext.__dict__.items() if hasattr(method, "context_object")}
        closure_objects = {name: getattr(self, name) for name in dir(GameContext) if hasattr(getattr(self, name), "context_object")}
        self.closure = {
            "Rect": Rect,
            "Player": Player,
            "MoveViewport": MoveViewport,
            "engine": engine,
            "context": self,
            **closure_objects
        }

    def set_level(self, level: Level) -> None:
        self.level = level
        self.engine.current_level = level

    def gids_for_rect(self, rect: Rect) -> list[int]:
        main_layer = self.level.main_layer
        level_map = self.level.map
        t_w = level_map.tilewidth
        t_h = level_map.tileheight

        t_col = rect.x // t_w
        t_row = rect.y // t_h
        start_col = t_col

        t_x = t_col * t_w
        t_y = t_row * t_h

        res = []
        try:
            while t_y + t_h >= rect.y and t_y < rect.bottom:
                while t_x + t_w > rect.x and t_x < rect.right:
                    res.append(main_layer.data[t_row][t_col])
                    t_col += 1
                    t_x = t_col * t_w
                t_col = start_col
                t_row += 1
                t_x = t_col * t_w
                t_y = t_row * t_h
        except IndexError as e:
            raise IndexError(f"[{t_row}][{t_col}]", e)

        return res

    def check_next_position(
            self,
            current_rect: Rect,
            next_rect: Rect,
            dx: float, dy: float) -> tuple[tuple[Union[int, float], Union[int, float]], Union[None, tuple[int]]]:

        def select_collided_rects(gids: list[int]) -> Generator[int, Any, None]:
            return (g for g in gids if g > 0)

        next_rect.x += dx
        next_rect.y += dy

        level = self.level
        if next_rect.x >= 0 and next_rect.y >= 0 and \
                next_rect.right < level.width and \
                next_rect.top < level.height:

            gids = self.gids_for_rect(next_rect)
            if next(select_collided_rects(gids), 0) == 0:
                return next_rect.topleft, None

        lx = current_rect.x
        ly = current_rect.y
        rx = next_rect.x
        ry = next_rect.y
        r = Rect((0, 0), next_rect.size)
        changed = False
        collided_background = []
        while not is_close(lx, rx, ly, ry):
            changed = True
            mx = rx + (lx - rx) / 2
            my = ry + (ly - ry) / 2
            r.x = mx
            r.y = my

            middle_collides = not (next_rect.x >= 0 and next_rect.y >= 0 and
                                   next_rect.right < level.width and
                                   next_rect.top < level.height)

            if not middle_collides:
                gids = self.gids_for_rect(r)
                collided_background = select_collided_rects(gids)
                middle_collides = next(collided_background, 0) != 0

            if middle_collides:
                rx = mx
                ry = my
            else:
                lx = mx
                ly = my

        if changed and (int(next_rect.x) != int(lx) or int(next_rect.y) != int(ly)):
            next_rect.x = lx
            next_rect.y = ly
            return next_rect.topleft, tuple(collided_background)
        return next_rect.topleft, tuple()

    def move_player(self, dx: float, dy: float) -> bool:
        player = self.player
        next_rect = player.next_rect

        next_pos, collided_tiles = self.check_next_position(player.rect, player.next_rect, dx, dy)

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

        if collided_tiles is None:
            return player_has_moved

        tiled_map = self.level.map
        drop_tile_id = next((g for g in collided_tiles if g in tiled_map.tile_properties and "drop" in tiled_map.tile_properties[g]), 0)
        if drop_tile_id != 0:
            self.player.vy = 2
            next_rect.y += self.player.vy
            if (next_rect.x + self.player.rect.width // 2) % tiled_map.tilewidth < tiled_map.tilewidth // 2:
                next_rect.x += 1

            return self.player.move_to(next_rect.topleft)

        return False

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
    def add_coins(self, coins: int) -> None:
        print(f"Adding {coins} coins")
        self.player.coins += coins

    @in_context
    def show_next_level_part(self) -> None:
        level = self.all_levels[self.level_no + 1]
        self.remove_object(self.currently_colliding_object)
        self.engine.show_level(level, FadeIn(level))

    @in_context
    def next_level(self) -> None:
        self.level.player_object.visible = False
        self.level.invalidated = True
        next_level = self.all_levels[self.level_no + 1]
        self.level = next_level
        self.engine.current_level = next_level
        next_level.start(self.player)
