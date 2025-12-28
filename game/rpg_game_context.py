# import math
# from pygame.key import ScancodeWrapper
#
# from typing import Union, Optional
#
# from pygame.font import Font
#
# from engine.level import Level
# from engine.tmx import TiledObject
# from engine.utils import Size, Position
# from game.overlays.inventory import Inventory
# from game.overlays.text_area import TextArea
# from pygame import Color
#
# from engine.game_context import in_context, GameContext
#
#
# def sgn(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
#     d = a - b
#     return -1 if d < 0 else (1 if d > 0 else 0)
#
#
# class RPGGameContext(GameContext):
#     def __init__(self, levels: dict[Union[str, int], Level], font: Font,
#                  small_font: Font,
#                  **kwargs) -> None:
#         super().__init__(levels, **kwargs)
#         self.inventory_visible = True
#         self._inventory: Inventory = Inventory(self, small_font)
#         self.hello = "hello"
#         self._add_attribute_name("hello")
#
#     def set_level(self, level: Level) -> None:
#         super().set_level(level)
#
#         tiled_map = self.level.map
#
#         width = max(tiled_map.images[gid].get_rect().width + 1 for gid in range(tiled_map.maxgid) if tiled_map.images[gid]) + 8
#         height = max(tiled_map.images[gid].get_rect().width + 1 for gid in range(tiled_map.maxgid) if tiled_map.images[gid]) + 8
#
#         self._inventory.set_size(Size(width, height))
#
#     @in_context
#     @property
#     def inventory(self) -> Inventory:
#         return self._inventory
#
#     @in_context
#     def add_coins(self, coins: int) -> None:
#         if "coin" in self._inventory:
#             coin_obj = self._inventory["coin"]
#             for _ in range(coins):
#                 self._inventory["coin"] = coin_obj
#
#     @in_context
#     def add_object_to_inventory(self, obj: TiledObject) -> None:
#         self.remove_object(obj)
#         k = obj.name
#         self.inventory[k] = obj
#         self.prevent_colliding()
#
#     @in_context
#     def give_object(self, obj_name: str) -> None:
#         for o in self.level.objects:
#             if o.name == obj_name:
#                 self.remove_object(o)
#                 self.add_object_to_inventory(o)
#                 return
#
#     @in_context
#     def set_inventory_visibility(self, visible: bool) -> None:
#         self.inventory_visible = visible
