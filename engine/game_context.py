from typing import Optional, Union, cast

from pygame import Rect

from engine.engine import Engine
from engine.level import Level
from engine.player import Player
from game.utils import is_close
from pytmx import TiledObject


class GameContext:
    def __init__(self, engine: Engine) -> None:
        self.player = Player()
        self.engine = engine
        self.engine.player = self.player
        self.engine.move_player = self.move_player
        self.level_no = 1
        self.level: Optional[Level] = None
        self.currently_colliding_object = None
        self.all_levels = {}

        self.closure = {k[2:]: getattr(self, k) for k in dir(self) if k.startswith("l_")}

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
        next_rect.x += dx
        next_rect.y += dy

        level = self.level
        if next_rect.x >= 0 and next_rect.y >= 0 and \
                next_rect.right < level.width and \
                next_rect.top < level.height:

            gids = self.gids_for_rect(next_rect)
            if next((g for g in gids if g > 0), 0) == 0:
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
                collided_background = (g for g in gids if g > 0)
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

        collision = next_rect.collidedict(self.level.objects)

        if collision is not None:
            collided_object: TiledObject = cast(TiledObject, collision[0])
            if "on_collision" in collided_object.properties:
                self.on_collision(self.player, collided_object)

        player_has_moved = self.player.move_to(next_rect.topleft)
        if player_has_moved:
            self.level.invalidated = True

        if collided_tiles is None:
            return True

        return False

    def on_collision(self, this: Union[Player, TiledObject], obj: TiledObject) -> None:
        self.currently_colliding_object = obj
        try:
            scriptlet = obj.properties["on_collision"]
            exec(scriptlet, self.closure, {"this": this, "obj": obj})
        finally:
            self.currently_colliding_object = None

    def l_remove_object(self, obj: TiledObject) -> None:
        self.level.remove_object(obj)

    def l_remove_collided_object(self) -> None:
        self.l_remove_object(self.currently_colliding_object)

    def l_add_coins(self, coins: int) -> None:
        print(f"Adding {coins} coins")
        self.player.coins += coins

    def l_show_next_level_part(self) -> None:
        self.l_remove_object(self.currently_colliding_object)
        self.engine.show_level(self.all_levels[self.level_no + 1])
