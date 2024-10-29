import math

from typing import Union, ChainMap, Optional

from pygame.font import Font

from engine.level import Level
from engine.tmx import TiledObject
from engine.utils import Size, Position
from game.overlays.inventory import Inventory
from game.overlays.text_area import TextArea
from game.top_down_game_context import TopDownGameContext
from pygame import Surface, Color, Rect

from engine.game_context import in_context


def sgn(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    d = a - b
    return -1 if d < 0 else (1 if d > 0 else 0)


class RPGGameContext(TopDownGameContext):
    def __init__(self, levels: dict[Union[str, int], Level], font: Font, small_font: Font) -> None:
        super().__init__(levels)
        self.font = font
        self.font_height = font.get_linesize()
        self.small_font = small_font
        self.inventory_visible = True
        self._inventory: Inventory = Inventory(self, small_font)
        self.text_area = TextArea(font)
        self.hello = "hello"
        self._add_attribute_name("hello")

    def _set_screen_size(self, size: Size) -> None:
        super()._set_screen_size(size)
        self.text_area.position = Position(20, size.height - self.text_area.size.height - 10)
        self.text_area.size = Size(size.width - 40, self.text_area.size.height)

    def set_level(self, level: Level) -> None:
        super().set_level(level)

        tiled_map = self.level.map

        width = max(tiled_map.images[gid].get_rect().width + 1 for gid in range(tiled_map.maxgid) if tiled_map.images[gid]) + 8
        height = max(tiled_map.images[gid].get_rect().width + 1 for gid in range(tiled_map.maxgid) if tiled_map.images[gid]) + 8

        self._inventory.set_size((width, height))

    @property
    @in_context
    def tiles_by_name(self) -> ChainMap[str, int]:
        return self.level.map.tiles_by_name

    @in_context
    @property
    def inventory(self) -> Inventory:
        return self._inventory

    @in_context
    def add_coins(self, coins: int) -> None:
        if "coin" in self._inventory:
            coin_obj = self._inventory["coin"]
            for _ in range(coins):
                self._inventory["coin"] = coin_obj

    @in_context
    def set_inventory_visibility(self, visible: bool) -> None:
        self.inventory_visible = visible

    @in_context
    def say(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        self.text_area.say(text, colour, expires_in)

    @in_context
    def say_once(self, text: str, colour: Optional[Color] = None, expires_in: float = 0.0) -> None:
        self.text_area.say_once(text, colour, expires_in)

    @in_context
    def distance_from_player(self, obj: TiledObject) -> float:
        dx = self.player.rect.x - obj.rect.x
        dy = self.player.rect.y - obj.rect.y
        return math.sqrt(dx * dx + dy * dy)

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
    def add_object_to_inventory(self, obj: TiledObject) -> None:
        self.remove_object(obj)
        k = obj.name
        self.inventory[k] = obj
        self.prevent_colliding()

    @in_context
    def give_object(self, obj_name: str) -> None:
        for o in self.level.objects:
            if o.name == obj_name:
                self.remove_object(o)
                self.add_object_to_inventory(o)
                return
