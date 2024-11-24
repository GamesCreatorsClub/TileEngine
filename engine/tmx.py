import gzip
import logging
import os
import struct
import time
import zlib
from abc import ABC
from base64 import b64decode
from collections import defaultdict, ChainMap, namedtuple
from copy import deepcopy
from typing import Any, Optional, Callable, NamedTuple, Union, TypeVar, Iterable, cast
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import pygame
from pygame import Surface, Rect, Color
from pygame.transform import flip, rotate

from engine.collision_result import CollisionResult

from engine.utils import NestedDict


logger = logging.getLogger(__name__)

GID_TRANS_FLIP_HORIZONTALLY = 1 << 31
GID_TRANS_FLIP_VERTICALLY = 1 << 30
GID_TRANS_ROTATE = 1 << 29
GID_MASK = GID_TRANS_FLIP_HORIZONTALLY | GID_TRANS_FLIP_VERTICALLY | GID_TRANS_ROTATE

TiledTileAnimation = namedtuple('TiledTileAnimation', ["tileid", "duration"])
F = namedtuple('F', ["type", "visible"])


class TiledClassType:
    def __init__(self, name: str, members: list[dict]) -> None:
        self.name = name
        for member in members:
            setattr(self, member["name"], member["value"])


def convert_to_bool(value: str) -> bool:
    value = str(value).strip()
    if value:
        value = value.lower()[0]
        if value in ("1", "y", "t"):
            return True
        if value in ("-", "0", "n", "f"):
            return False
    else:
        return False
    raise ValueError(f"cannot parse {value} as bool")


def resolve_to_class(value: str, custom_types: dict) -> TiledClassType:
    return deepcopy(custom_types[value])


TYPES = defaultdict(lambda: str)
TYPES.update(
    {
        "backgroundcolor": str,
        "bold": convert_to_bool,
        "color": str,
        "columns": int,
        "compression": str,
        "draworder": str,
        "duration": int,
        "encoding": str,
        "firstgid": int,
        "fontfamily": str,
        "format": str,
        "gid": int,
        "halign": str,
        "height": float,
        "hexsidelength": float,
        "id": int,
        "italic": convert_to_bool,
        "kerning": convert_to_bool,
        "margin": int,
        "name": str,
        "nextobjectid": int,
        "offsetx": int,
        "offsety": int,
        "opacity": float,
        "orientation": str,
        "pixelsize": float,
        "points": str,
        "probability": float,
        "renderorder": str,
        "rotation": float,
        "source": str,
        "spacing": int,
        "staggeraxis": str,
        "staggerindex": str,
        "strikeout": convert_to_bool,
        "terrain": str,
        "tile": int,
        "tilecount": int,
        "tiledversion": str,
        "tileheight": int,
        "tileid": int,
        "tilewidth": int,
        "trans": str,
        "type": str,
        "underline": convert_to_bool,
        "valign": str,
        "value": str,
        "version": str,
        "visible": convert_to_bool,
        "width": float,
        "wrap": convert_to_bool,
        "x": float,
        "y": float,
        "infinite": convert_to_bool,
        "nextlayerid": int,
    }
)

PROPERTY_TYPES = {
    "bool": convert_to_bool,
    "color": str,
    "file": str,
    "float": float,
    "int": int,
    "object": int,
    "string": str,
    "class": resolve_to_class,
    "enum": str,
}

TiledElementType = TypeVar('TiledElementType')


class NodeType:
    def __init__(
            self,
            factory_method: Optional[
                Union[
                    Callable[[TiledElementType, Element], None],  # Correct type
                    Callable[[Element], None]  # For incorrect type deduction in PyCharm
                ]] = None,
            type_constructor: Optional[Union[Callable[[TiledElementType], Any], TiledElementType]] = None,
            destination: Optional[str] = None
    ) -> None:
        self.factory_method = factory_method
        self.type_constructor = type_constructor
        self.destination = destination


class TileFlags(NamedTuple):
    flipped_horizontally: bool
    flipped_vertically: bool
    flipped_diagonally: bool


class TiledElement:
    ATTRIBUTES = {"id": F(int, False), "name": F(str, True)}

    def __init__(self, parent: Optional['TiledElement'] = None) -> None:
        self.parent = parent
        self.properties: dict[str, Any] = {}
        self.id: int = 0
        self.name: str = ""

    def __getitem__(self, key: str) -> Any:
        return self.properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.properties[key] = value

    def __delitem(self, key: str) -> None:
        del self.properties[key]

    # def __getattr__(self, item: str) -> Any:
    #     try:
    #         return self.properties[item]
    #     except KeyError:
    #         if self.properties.get("name", None):
    #             raise AttributeError(f"Element {self.name} has no property {item}")
    #         else:
    #             raise AttributeError(f"Element has no property {item}")

    @staticmethod
    def _parse_xml_properties(node: Element) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for subnode in node.findall("property"):
            cls = None
            if "type" in subnode.keys():
                cls = PROPERTY_TYPES[subnode.get("type")]

            name = subnode.get("name")

            if "class" == subnode.get("type"):
                raise NotImplemented("Class being type of property")
            else:
                if cls is None:
                    properties[name] = subnode.get("value") or subnode.text
                else:
                    properties[name] = cls(subnode.get("value"))
        return properties

    def _parse_xml_to_properties(self, node: Element) -> None:
        properties = self._parse_xml_properties(node)
        self.properties.update(properties)
        for key in properties:
            if hasattr(self, key):
                setattr(self, key, properties[key])

    def _parse_xml(self, node: Element) -> None:
        for key, value in node.items():
            casted_value = TYPES[key](value)
            if hasattr(self, key):
                setattr(self, key, casted_value)
            else:
                logger.debug(f"Object {self} does not have attr {key}")

        types = self.NODE_TYPES

        for child_node in list(node):
            if child_node.tag in types:
                node_type = types[child_node.tag]

                if node_type.factory_method:
                    cast(Callable[[TiledElement, Element], None], node_type.factory_method)(self, child_node)
                elif node_type.type_constructor:
                    obj = cast(TiledElement, node_type.type_constructor(self))
                    obj._parse_xml(child_node)
                    if node_type.destination is not None:
                        if hasattr(self, node_type.destination):
                            destination = getattr(self, node_type.destination)
                            if isinstance(destination, list):
                                destination.append(obj)
                            elif isinstance(destination, dict):
                                name = obj.name
                                destination[name] = obj
                            elif isinstance(destination, Callable):
                                destination(obj)
                            else:
                                setattr(self, node_type.destination, obj)
                        else:
                            raise KeyError(f"Cannot set {child_node.tag} on {self}")
                else:
                    pass
            else:
                raise KeyError(f"Cannot set {child_node.tag} on {self} - no type defined")

    NODE_TYPES: dict[str, NodeType] = {"properties": NodeType(_parse_xml_to_properties, None, None)}


class TiledSubElement(TiledElement):
    def __init__(self, parent: Optional['TiledElement'] = None) -> None:
        super().__init__(parent)

        if parent:
            tiled_map = parent
            while not isinstance(tiled_map, TiledMap):
                tiled_map = tiled_map.parent

            self.map: Optional[TiledMap] = tiled_map


class BaseTiledLayer(TiledSubElement, ABC):
    ATTRIBUTES = TiledElement.ATTRIBUTES | {"visible": F(bool, True)}

    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.visible: bool = True


class TiledTileLayer(BaseTiledLayer):
    ATTRIBUTES = BaseTiledLayer.ATTRIBUTES | {
        "width": F(int, True), "height": F(int, True), "animate_layer": F(bool, True)
    }

    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.width: int = 0
        self.height: int = 0
        self.data: list[list[int]] = [[]]
        self.animate_layer: bool = False

    def _parse_xml_data(self, data_node: Element) -> None:
        encoding = data_node.get("encoding", None)
        compression = data_node.get("compression", None)
        if encoding == "base64":
            if compression == "gzip":
                data = gzip.decompress(b64decode(data_node.text))
            elif compression == "zlib":
                data = zlib.decompress(b64decode(data_node.text))
            else:
                data = b64decode(data_node.text)
            data = list(struct.unpack("<%dL" % (len(data) // 4), data))
        elif encoding == "csv":
            data = [int(i) for i in data_node.text.split(",")]
        else:
            raise NotImplemented(f"Unknown encoding for data {encoding}")

        columns = int(self.width)
        for i in range(len(data)):
            if i > 0:
                data[i] = self.map.register_raw_gid(data[i])

        self.data = [data[i: i + columns] for i in range(0, len(data), columns)]
        self.animate_layer = self._check_if_animated_gids()

    def _check_if_animated_gids(self) -> bool:
        for row in self.data:
            for gid in row:
                if gid in self.map.tile_animations:
                    return True
        return False

    def iter_data(self) -> Iterable[tuple[int, int, int]]:
        """Yields X, Y, GID tuples for each tile in the layer.

        Returns:
            Iterable[Tuple[int, int, int]]: Iterator of X, Y, GID tuples for each tile in the layer.

        """
        for y, row in enumerate(self.data):
            for x, gid in enumerate(row):
                yield x, y, gid

    def tiles(self, current_time: Optional[float] = None):
        """Yields X, Y, Image tuples for each tile in the layer.

        Yields:
            ???: Iterator of X, Y, Image tuples for each tile in the layer

        """
        current_time = current_time if current_time is not None else time.time()
        time_ms = int(current_time * 1000)

        images = self.map.images

        if self.animate_layer:
            for x, y, gid in [i for i in self.iter_data() if i[2]]:
                if gid in self.map.tile_animations:
                    gid = self.map.tile_animations[gid].get_gid(time_ms)
                yield x, y, images[gid]
        else:
            for x, y, gid in [i for i in self.iter_data() if i[2]]:
                yield x, y, images[gid]

    def draw(self, surface: Surface, viewport: Rect, xo: int, yo: int, current_time: Optional[float] = None) -> None:
        current_time = current_time if current_time is not None else time.time()
        time_ms = int(current_time * 1000)

        images = self.map.images
        width = self.map.width
        height = self.map.height
        tilewidth = self.map.tilewidth
        tileheight = self.map.tileheight

        dy = -yo // tileheight
        oy = yo % tileheight if yo >= 0 else -(-yo % tileheight)

        start_dx = -xo // tilewidth
        ox = xo % tilewidth if xo >= 0 else -(-xo % tilewidth)

        if self.animate_layer:
            for y in range(viewport.y + oy, viewport.bottom + tileheight, tileheight):
                if 0 <= dy < height:
                    dx = start_dx
                    for x in range(viewport.x + ox, viewport.right + tilewidth, tilewidth):
                        if 0 <= dx < width:
                            gid = self.data[dy][dx]
                            if gid > 0:
                                if gid in self.map.tile_animations:
                                    gid = self.map.tile_animations[gid].get_gid(time_ms)
                                surface.blit(images[gid], (x, y))
                        dx += 1
                dy += 1
        else:
            for y in range(viewport.y + oy, viewport.bottom + tileheight, tileheight):
                if 0 <= dy < height:
                    dx = start_dx
                    for x in range(viewport.x + ox, viewport.right + tilewidth, tilewidth):
                        if 0 <= dx < width:
                            gid = self.data[dy][dx]
                            if gid > 0:
                                surface.blit(images[gid], (x, y))
                        dx += 1
                dy += 1

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "data": NodeType(_parse_xml_data, None, None),
    }


class TiledGroupLayer(BaseTiledLayer):
    def __init__(self, tiled_map: 'TiledMap') -> None:
        super().__init__(tiled_map)

        self.layers: list[BaseTiledLayer] = []


class TiledObject(TiledSubElement):
    NODE_TYPES = TiledElement.NODE_TYPES | {
        "ellipse": NodeType(None, None, None),
    }
    ATTRIBUTES = TiledElement.ATTRIBUTES | {
        "gid": F(int, True), "visible": F(bool, True),
        "solid": F(bool, True), "pushable": F(bool, True),
        "x": F(float, True), "y": F(float, True), "width": F(int, True), "height": F(int, True)
    }

    def __init__(self, parent: Optional[TiledElement]) -> None:
        super().__init__(parent)
        self.properties: dict[str, Any] = NestedDict()
        self._gid: int = 0
        self.visible: bool = True
        self.solid: bool = False
        self.pushable: bool = False

        self.rect = Rect(0, 0, 0, 0)
        self.next_rect = Rect(0, 0, 0, 0)
        self.collisions = set()
        self.collision_result: Optional[CollisionResult] = None

    @property
    def x(self) -> float: return self.rect.x

    @x.setter
    def x(self, v: float) -> None:
        self.rect.x = v

    @property
    def y(self) -> float: return self.rect.y

    @y.setter
    def y(self, v: float) -> None: self.rect.y = v

    @property
    def width(self) -> float: return self.rect.width

    @width.setter
    def width(self, v: float) -> None: self.rect.width = v

    @property
    def height(self) -> float: return self.rect.height

    @height.setter
    def height(self, v: float) -> None: self.rect.height = v

    @property
    def gid(self) -> int:
        return self._gid

    @gid.setter
    def gid(self, new_gid: int) -> None:
        self.set_gid(new_gid)

    @property
    def tile(self) -> int:
        return self._gid

    @tile.setter
    def tile(self, gid: int) -> None:
        if gid > 0:
            gid = self.map.register_raw_gid(gid)
        self._gid = gid

    def set_gid(self, gid: int) -> None:
        if gid > 0:
            gid = self.map.register_raw_gid(gid)

            if gid in self.map.tile_properties:
                properties = self.map.tile_properties[gid]
                if properties is not None:
                    self.properties.over = properties
                else:
                    self.properties.over = {}
        self._gid = gid

    def _parse_xml(self, node: Element) -> None:
        super()._parse_xml(node)

        if self.map.invert_y and self.gid > 0:
            self.y -= self.height

    @property
    def image(self) -> Optional[Surface]:
        gid = self.gid
        if gid:
            if gid in self.map.tile_animations:
                time_ms = int(time.time() * 1000)
                gid = self.map.tile_animations[gid].get_gid(time_ms)
            return self.map.images[gid]
        return None


class TiledObjectGroup(BaseTiledLayer):

    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.parent_tile_id: Optional[int] = None
        self.objects_id_map: dict[int, TiledObject] = {}

    @property
    def objects(self) -> Iterable[TiledObject]:
        return self.objects_id_map.values()

    def add_object(self, obj: TiledObject):
        if obj.id == 0:
            obj.id = (max(obj.id for obj in self.objects_id_map.values()) + 1) if len(self.objects_id_map) > 0 else 1
        self.objects_id_map[obj.id] = obj

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "object": NodeType(None, TiledObject, "add_object"),
    }


class TiledTerrain(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.tile: int = -1


class TiledWangTile(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.wangid: str = ""

    @property
    def tileid(self) -> int:
        return self.id

    @tileid.setter
    def tileid(self, id_: Union[str, int]) -> None:
        if isinstance(id_, str):
            id_ = int(id_)
        self.id = id_


class TiledWangColor(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.color: str = ""
        self.tile: int = -1
        self.probability: float = 1


class TiledWangSet(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.wangcolors: list[TiledWangColor] = []
        self.wangtiles: list[TiledWangTile] = []

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "wangtile": NodeType(None, TiledWangTile, "wangtiles"),
        "wangcolor": NodeType(None, TiledWangColor, "wangcolors")
    }


class TiledWangSets(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.wangset_by_name: dict[str, TiledWangSet] = {}

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "wangset": NodeType(None, TiledWangSet, "wangset_by_name")
    }


class TiledTileAnimations:
    def __init__(self) -> None:
        self.frames: list[TiledTileAnimation] = []
        self.total_animation_len = 0

    def add_frame(self, frame: TiledTileAnimation) -> None:
        self.frames.append(frame)
        self.total_animation_len += frame.duration

    def get_gid(self, time_ms: int) -> int:
        r = time_ms % self.total_animation_len
        for frame in self.frames:
            r -= frame.duration
            if r <= 0:
                return frame.tileid
        return self.frames[-1].tileid


class TiledTileset(TiledElement):
    ATTRIBUTES = TiledElement.ATTRIBUTES | {
        "firstgid": F(int, False), "name": F(str, True), "tilewidth": F(int, True), "tileheight": F(int, True),
        "spacing": F(int, True), "margin": F(int, True), "tilecount": F(int, False), "columns": F(int, True),
        "width": F(int, True), "height": F(int, True)
    }

    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self._parent_dir = os.path.dirname(cast(TiledMap, self.parent).filename)

        self._source_filename: str = ""
        self._source_image_filename: str = ""
        self.image_surface: Optional[Surface] = None
        self.tile_properties: dict[int, dict[str, Any]] = {}
        self.tile_terrain: dict[int, str] = {}
        self.tiles_by_name: dict[str: int] = {}
        self.terrain: list[TiledTerrain] = []
        self.wangsets: Optional[TiledWangSets] = None
        self.tile_animations: dict[int, TiledTileAnimations] = {}

        self.offset: tuple[int, int] = (0, 0)

        # defaults from the specification
        self.firstgid: int = 0
        self.name: Optional[str] = None
        self.tilewidth: int = 0
        self.tileheight: int = 0
        self.spacing: int = 0
        self.margin: int = 0
        self.tilecount: int = 0
        self.columns: int = 0

        # image properties
        self.trans = None
        self.width: int = 0
        self.height: int = 0

    @property
    def image(self) -> str:
        return self._source_image_filename

    @image.setter
    def image(self, filename: str) -> None:
        self._source_image_filename = filename
        self.load(self._source_image_filename)

    @property
    def source(self) -> str:
        return self._source_filename

    @source.setter
    def source(self, filename: str) -> None:
        self.load(filename)

    def load(self, filename: str) -> None:
        self._source_filename = filename

        filename = filename.replace("\\", "/")
        filename = filename.replace("/", os.path.sep)

        full_filename = os.path.join(self._parent_dir, filename)
        self._parse_xml(ElementTree.parse(full_filename).getroot())

    def _load_image(self, image_element: Element) -> None:
        self._source_image_filename = image_element.get("source")
        _width = int(image_element.get("width"))
        _height = int(image_element.get("width"))
        full_filename = os.path.join(os.path.join(self._parent_dir, os.path.dirname(self._source_filename)), self._source_image_filename)
        self.image_surface = pygame.image.load(full_filename)
        # image_rect = self.image_surface.get_rect()

    def _tile(self, tile_element: Element) -> None:
        id_ = int(tile_element.get("id")) + self.firstgid
        terrain = tile_element.get("terrain")
        if terrain is not None:
            self.tile_terrain[id_] = terrain
        properties: dict[str, Any] = {}
        properties_node = tile_element.find("properties")
        if properties_node:
            properties.update(self._parse_xml_properties(properties_node))
        for obj_group_node in tile_element.findall("objectgroup"):
            objectgroup = TiledObjectGroup(self)
            objectgroup.parent_tile_id = id_
            objectgroup._parse_xml(obj_group_node)
            properties["colliders"] = objectgroup.objects
        if len(properties) > 0:
            self.tile_properties[id_] = properties
            if "name" in properties:
                self.tiles_by_name[properties["name"]] = id_
        animation_node = tile_element.find("animation")
        if animation_node:
            animations = TiledTileAnimations()
            self.tile_animations[id_] = animations
            for frame_node in animation_node.findall("frame"):
                frame_tileid = int(frame_node.get("tileid")) + self.firstgid
                duration = int(frame_node.get("duration"))
                animations.add_frame(TiledTileAnimation(frame_tileid, duration))

    def _tileoffset(self, tileoffset_element: Element) -> None:
        self.offset = (int(tileoffset_element.get("x")), int(tileoffset_element.get("y")))

    def _add_terrain_types(self, terrain_types_element: Element) -> None:
        for terrain_node in terrain_types_element.findall("terrain"):
            terrain = TiledTerrain(self)
            terrain.name = terrain_node.get("name")
            terrain.tile = terrain_node.get("tile")
            self.terrain.append(terrain)

    def get_image(self, gid) -> Surface:
        gid = gid - self.firstgid
        y = (gid // self.columns)
        x = (gid - y * self.columns)
        return self.image_surface.subsurface(Rect(x * self.tilewidth, y * self.tileheight, self.tilewidth, self.tileheight))

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "image": NodeType(_load_image, None, None),
        "tile": NodeType(_tile, None, None),
        "tileoffset": NodeType(_tileoffset, None, None),
        "wangsets": NodeType(None, TiledWangSets, "wangsets"),
        "terraintypes": NodeType(_add_terrain_types, None, None),
    }


class TiledMap(TiledElement):
    NODE_TYPES = TiledElement.NODE_TYPES | {
        "tileset": NodeType(None, TiledTileset, "add_tileset"),
        "layer": NodeType(None, TiledTileLayer, "add_layer"),
        "objectgroup": NodeType(None, TiledObjectGroup, "add_layer"),
    }

    ATTRIBUTES = TiledElement.ATTRIBUTES | {
        "version": F(str, False), "tiledversion": F(str, False),
        "orientation": F(str, False), "renderorder": F(str, False),
        "width": F(int, True), "height": F(int, True), "tilewidth": F(int, True), "tileheight": F(int, True),
        "hexsidelength": F(int, False), "staggeraxis": F(str, False), "staggerindex": F(int, False),
        "backgroundcolor": F(Color, True),
        "nextobjectid": F(int, False), "nextlayerid": F(int, False), "maxgid": F(int, False),
        "infinite": F(bool, False)
    }

    def __init__(self, invert_y: bool = True) -> None:
        super().__init__()
        self.filename: Optional[str] = None

        self.invert_y = invert_y

        self.layer_id_map: dict[int, BaseTiledLayer] = {}
        self.tilesets: list[TiledTileset] = []
        self.tile_properties: ChainMap[int, dict[str, Any]] = ChainMap()
        self.tiles_by_name: ChainMap[str, int] = ChainMap()
        self.tile_animations: ChainMap[int, TiledTileAnimations] = ChainMap()

        self.version: str = "0.0"
        self.tiledversion: str = ""
        self.orientation: str = "orthogonal"
        self.renderorder: str = "right-down"
        self.width: int = 0  # width of map in tiles
        self.height: int = 0  # height of map in tiles
        self.tilewidth: int = 0  # width of a tile in pixels
        self.tileheight: int = 0  # height of a tile in pixels
        self.hexsidelength: int = 0
        self.staggeraxis: Optional[str] = None
        self.staggerindex: Optional[int] = None
        self._backgroundcolor: Optional[tuple[int, int, int]] = None

        self.nextobjectid: int = 0
        self.nextlayerid: int = 0
        self.maxgid: int = 0

        self.infinite: bool = False
        self.images: list[Surface] = []

    @property
    def backgroundcolor(self) -> Optional[tuple[int, int, int]]:
        return self._backgroundcolor

    @backgroundcolor.setter
    def backgroundcolor(self, colour: str) -> None:
        if not colour.startswith('#'):
            raise ValueError(f"Unsupported value {colour}")
        self._backgroundcolor = int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)

    @property
    def layers(self) -> Iterable[BaseTiledLayer]:
        return self.layer_id_map.values()

    def add_layer(self, layer: BaseTiledLayer) -> None:
        self.layer_id_map[layer.id] = layer

    def add_tileset(self, tileset: TiledTileset) -> None:
        self.tilesets.append(tileset)
        self.tile_properties = ChainMap(*[ts.tile_properties for ts in self.tilesets])
        self.tiles_by_name = ChainMap(*[ts.tiles_by_name for ts in self.tilesets])
        self.tile_animations = ChainMap(*[ts.tile_animations for ts in self.tilesets])

        tilesets_maxgid = tileset.firstgid + tileset.tilecount
        self.maxgid = max(self.maxgid, tilesets_maxgid)
        if len(self.images) < self.maxgid:
            self.images += [None] * (self.maxgid - len(self.images))
        for i in range(tileset.tilecount):
            self.images[tileset.firstgid + i] = tileset.get_image(i + tileset.firstgid)

    def load(self, filename: str) -> None:
        self.filename = filename
        self._parse_xml(ElementTree.parse(filename).getroot())

    def save(self, filename: str) -> None:
        pass

    def register_raw_gid(self, gid: int) -> int:
        if gid < self.maxgid:
            return gid

        g = gid & ~GID_MASK

        return self.register_gid(g, TileFlags(
            flipped_horizontally=gid & GID_TRANS_FLIP_HORIZONTALLY == GID_TRANS_FLIP_HORIZONTALLY,
            flipped_vertically=gid & GID_TRANS_FLIP_VERTICALLY == GID_TRANS_FLIP_VERTICALLY,
            flipped_diagonally=gid & GID_TRANS_ROTATE == GID_TRANS_ROTATE
        ))

    def register_gid(self, existing_gid, tile_flags: TileFlags) -> int:
        new_gid = self.maxgid
        self.maxgid += 1
        self.images += [None]

        gid_image = self.images[existing_gid]

        if tile_flags.flipped_diagonally:
            gid_image = flip(rotate(gid_image, 270), True, False)
        if tile_flags.flipped_horizontally or tile_flags.flipped_vertically:
            gid_image = flip(gid_image, tile_flags.flipped_horizontally, tile_flags.flipped_vertically)

        self.images[new_gid] = gid_image
        return new_gid


if __name__ == '__main__':
    tiled_map = TiledMap()

    tiled_map.load("assets/side_scroller/level1.tmx")

    print(tiled_map)
