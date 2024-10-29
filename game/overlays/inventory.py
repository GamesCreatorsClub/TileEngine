from typing import Iterator, Mapping, Sized, Any, Optional, Union

import pygame
from pygame import Surface, Color, Rect
from pygame.font import Font

from engine.game_context import GameContext
from engine.tmx import TiledObject
from engine.utils import Size


class InventoryObject:
    def __init__(self, gid: int, properties: Optional[dict[str, Any]] = None, tiled_object: Optional[TiledObject] = None) -> None:
        self.gid = gid
        self.tiled_object: Optional[TiledObject] = tiled_object
        self.properties: dict[str, Any] = {} if properties is None else properties

    @classmethod
    def from_obj(cls, tiled_object: TiledObject) -> 'InventoryObject':
        return InventoryObject(tiled_object.gid, tiled_object.properties if len(tiled_object.properties) > 0 else None, tiled_object=tiled_object)


class Inventory(Mapping[str, InventoryObject], Sized):
    def __init__(self,
                 game_context: GameContext,
                 small_font: Font,
                 box_colour: Color = pygame.Color("burlywood4"),
                 font_color: Color = pygame.Color("white")) -> None:
        self.game_context = game_context
        self.small_font = small_font
        self.box_colour = box_colour
        self.box_colour_transparent = pygame.Color(box_colour.r, box_colour.g, box_colour.b, 128)
        self.font_color = font_color
        self.dict: dict[str, list[InventoryObject]] = {}
        self.entry_images: dict[str, Surface] = {}
        self._free_entry_images: list[Surface] = []
        self.image_size: Size = Size(32, 32)

    def _init_image(self, image: Surface) -> None:
        image.fill(self.box_colour_transparent)
        pygame.draw.rect(image, self.box_colour, image.get_rect(), width=2)

    def _stamp_object(self, image: Surface, obj: InventoryObject) -> Surface:
        tile = self.game_context.level.map.images[obj.gid]
        r = tile.get_rect().copy()
        r.center = image.get_rect().center
        image.blit(tile, r)
        return image

    def _new_image(self) -> Surface:
        if len(self._free_entry_images) > 0:
            image = self._free_entry_images[0]
            del self._free_entry_images[0]
        else:
            image = Surface(self.image_size, pygame.SRCALPHA, 32).convert_alpha()
            self._init_image(image)
        return image

    def set_size(self, size: Size) -> bool:
        changed = False
        if not self.image_size or size.width != self.image_size.width or size.height != self.image_size.height:
            del self._free_entry_images[:]
            changed = True
            self.image_size = size
        return changed

    def count(self, key: str) -> int:
        if key in self.dict:
            return len(self.dict[key])
        return 0

    def __getitem__(self, key: str) -> InventoryObject:
        return self.dict[key][0]

    def __setitem__(self, key: str, obj: Union[TiledObject, InventoryObject]) -> None:
        if isinstance(obj, TiledObject):
            obj = InventoryObject.from_obj(obj)

        if key in self.dict:
            self.dict[key].append(obj)
            image = self.entry_images[key]
            image_rect = image.get_rect()
            self._init_image(image)
            self._stamp_object(image, obj)
            text_white = self.small_font.render(str(len(self.dict[key])), True, self.font_color).convert_alpha()
            text_black = self.small_font.render(str(len(self.dict[key])), True, self.box_colour).convert_alpha()
            text_rect = text_white.get_rect()
            image.blit(text_black, (image_rect.right - text_rect.width - 2, image_rect.bottom - text_rect.height - 2))
            image.blit(text_black, (image_rect.right - text_rect.width - 2, image_rect.bottom - text_rect.height))
            image.blit(text_black, (image_rect.right - text_rect.width, image_rect.bottom - text_rect.height - 2))
            image.blit(text_black, (image_rect.right - text_rect.width, image_rect.bottom - text_rect.height))
            image.blit(text_white, (image_rect.right - text_rect.width - 1, image_rect.bottom - text_rect.height - 1))

        else:
            self.dict[key] = [obj]
            image = self._new_image()
            self._stamp_object(image, obj)
            self.entry_images[key] = image

    def __delitem__(self, key: str) -> None:
        if key not in self.dict:
            raise KeyError(key)

        l = self.dict[key]
        del l[0]
        if len(l) == 0:
            del self.dict[key]
            if key in self.entry_images:
                image = self.entry_images[key]
                self._init_image(image)
                self._free_entry_images = image
                del self.entry_images[key]

    def __contains__(self, key: str) -> bool:
        return key in self.dict

    def __len__(self) -> int:
        return len(self.dict)

    def __iter__(self) -> Iterator[str]:
        return iter(self.dict)

    def draw(self, screen: Surface, place: Rect) -> None:
        if len(self) == 0:
            return

        rect = place.copy()
        for key in self:
            screen.blit(self.entry_images[key], rect)
            rect.y += self.image_size.height
