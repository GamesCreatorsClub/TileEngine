import gzip
import logging
import os
import struct
import zlib
from abc import ABC
from base64 import b64decode
from collections import defaultdict, ChainMap
from copy import deepcopy
from typing import Any, Optional, Callable, NamedTuple, Union, TypeVar, Iterable, cast
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import pygame
from pygame import Surface, Rect
from pygame.transform import flip, rotate

from engine.collision_result import CollisionResult

logger = logging.getLogger(__name__)

GID_TRANS_FLIP_HORIZONTALLY = 1 << 31
GID_TRANS_FLIP_VERTICALLY = 1 << 30
GID_TRANS_ROTATE = 1 << 29
GID_MASK = GID_TRANS_FLIP_HORIZONTALLY | GID_TRANS_FLIP_VERTICALLY | GID_TRANS_ROTATE


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
            factory_method: Optional[Callable[[TiledElementType, Element], None]] = None,
            type_constructor: Optional[Union[Callable[[TiledElementType], Any], TiledElementType]] = None,
            destination: Optional[str] = None
    ) -> None:
        self.factory_method: Optional[Callable[[TiledElementType, Element], None]] = factory_method
        self.type_constructor: Optional[Union[Callable[[TiledElementType], Any], TiledElementType]] = type_constructor
        self.destination: Optional[str] = destination


class TileFlags(NamedTuple):
    flipped_horizontally: bool
    flipped_vertically: bool
    flipped_diagonally: bool


class TiledElement:
    def __init__(self, parent: Optional['TiledElement'] = None) -> None:
        self.parent = parent
        self.properties: dict[str, Any] = {}
        self.id = 0
        self.name = ""

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

    def _parse_xml_to_properties(self: TiledElementType, node: Element) -> None:
        self.properties.update(self._parse_xml_properties(node))

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
                    node_type.factory_method(self, child_node)
                elif node_type.type_constructor:
                    obj = node_type.type_constructor(self)
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
                                setattr(self, destination, obj)
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

        tiled_map = parent
        while not isinstance(tiled_map, TiledMap):
            tiled_map = tiled_map.parent

        self.map: TiledMap = tiled_map


class BaseTiledLayer(TiledSubElement, ABC):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.name = ""
        self.visible = True


class TiledTileLayer(BaseTiledLayer):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.width = 0
        self.height = 0
        self.data: list[list[int]] = [[]]

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

    def iter_data(self) -> Iterable[tuple[int, int, int]]:
        """Yields X, Y, GID tuples for each tile in the layer.

        Returns:
            Iterable[Tuple[int, int, int]]: Iterator of X, Y, GID tuples for each tile in the layer.

        """
        for y, row in enumerate(self.data):
            for x, gid in enumerate(row):
                yield x, y, gid

    def tiles(self):
        """Yields X, Y, Image tuples for each tile in the layer.

        Yields:
            ???: Iterator of X, Y, Image tuples for each tile in the layer

        """
        images = self.map.images
        for x, y, gid in [i for i in self.iter_data() if i[2]]:
            yield x, y, images[gid]

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
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self.gid: int = 0
        self.visible: bool = True

        self.rect = Rect(0, 0, 0, 0)
        self.next_rect = Rect(0, 0, 0, 0)
        self.collisions = set()
        self.collision_result: Optional[CollisionResult] = None

    @property
    def x(self) -> float: return self.rect.x

    @x.setter
    def x(self, v: float) -> None: self.rect.x = v

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

    def _parse_xml(self, node: Element) -> None:
        super()._parse_xml(node)
        if self.gid > 0:
            self.gid = self.map.register_raw_gid(self.gid)

            if self.gid in self.map.tile_properties:
                properties = self.map.tile_properties[self.gid]
                if properties is not None:
                    self.properties = properties | self.properties

        if self.map.invert_y and self.gid > 0:
            self.y -= self.height

    @property
    def image(self):
        if self.gid:
            return self.map.images[self.gid]
        return None


class TiledObjectGroup(TiledSubElement):
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


class TiledTileset(TiledElement):
    def __init__(self, parent: TiledElement) -> None:
        super().__init__(parent)
        self._source: str = ""
        self._parent_dir = os.path.dirname(cast(TiledMap, self.parent).filename)

        self.firstgid = 0
        self.image: Optional[Surface] = None
        self.tile_properties: dict[int, dict[str, Any]] = {}

        self.offset = (0, 0)

        # defaults from the specification
        self.firstgid = 0
        self.name = None
        self.tilewidth = 0
        self.tileheight = 0
        self.spacing = 0
        self.margin = 0
        self.tilecount = 0
        self.columns = 0

        # image properties
        self.trans = None
        self.width = 0
        self.height = 0

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, filename: str) -> None:
        self._source = filename
        self.load(self._source)

    def load(self, filename: str) -> None:
        self._source = filename

        full_filename = os.path.join(self._parent_dir, filename)
        self._parse_xml(ElementTree.parse(full_filename).getroot())

    def _load_image(self, image_element: Element) -> None:
        filename = image_element.get("source")
        _width = int(image_element.get("width"))
        _height = int(image_element.get("width"))
        full_filename = os.path.join(os.path.join(self._parent_dir, os.path.dirname(self._source)), filename)
        self.image = pygame.image.load(full_filename)
        image_rect = self.image.get_rect()

    def _tile(self, tile_element: Element) -> None:
        id_ = int(tile_element.get("id")) + self.firstgid
        properties: dict[str, Any] = {}
        properties_node = tile_element.find("properties")
        if properties_node:
            properties.update(self._parse_xml_properties(properties_node))
        for obj_group_node in tile_element.findall("objectgroup"):
            objectgroup = TiledObjectGroup(self)
            objectgroup.parent_tile_id = id_
            objectgroup._parse_xml(obj_group_node)
            properties["colliders"] = objectgroup
        if len(properties) > 0:
            self.tile_properties[id_] = properties

    def _tileoffset(self, tileoffset_element: Element) -> None:
        self.offset = (int(tileoffset_element.get("x")), int(tileoffset_element.get("y")))

    def get_image(self, gid) -> Surface:
        gid = gid - self.firstgid
        y = (gid // self.columns)
        x = (gid - y * self.columns)
        return self.image.subsurface(Rect(x * self.tilewidth, y * self.tileheight, self.tilewidth, self.tileheight))

    NODE_TYPES = TiledElement.NODE_TYPES | {
        "image": NodeType(_load_image, None, None),
        "tile": NodeType(_tile, None, None),
        "tileoffset": NodeType(_tileoffset, None, None),
        "wangsets": NodeType(None, None, None)
    }


class TiledMap(TiledElement):
    NODE_TYPES = TiledElement.NODE_TYPES | {
        "tileset": NodeType(None, TiledTileset, "add_tileset"),
        "layer": NodeType(None, TiledTileLayer, "add_layer"),
        "objectgroup": NodeType(None, TiledObjectGroup, "add_layer"),
    }

    def __init__(self, invert_y: bool = True) -> None:
        super().__init__()
        self.filename: Optional[str] = None

        self.invert_y = invert_y

        self.layer_id_map: dict[int, BaseTiledLayer] = {}
        self.tilesets: list[TiledTileset] = []
        self._tileset_properties: ChainMap[int, dict[str, Any]] = ChainMap()

        self.version = "0.0"
        self.tiledversion = ""
        self.orientation = "orthogonal"
        self.renderorder = "right-down"
        self.width = 0  # width of map in tiles
        self.height = 0  # height of map in tiles
        self.tilewidth = 0  # width of a tile in pixels
        self.tileheight = 0  # height of a tile in pixels
        self.hexsidelength = 0
        self.staggeraxis = None
        self.staggerindex = None
        self.background_color = None

        self.nextobjectid = 0
        self.nextlayerid = 0
        self.maxgid = 0

        self.infinite = False
        self.images: list[Surface] = []

    @property
    def layers(self) -> Iterable[BaseTiledLayer]:
        return self.layer_id_map.values()

    @property
    def tile_properties(self) -> ChainMap[int, dict[str, Any]]:
        return self._tileset_properties

    def add_layer(self, layer: BaseTiledLayer) -> None:
        self.layer_id_map[layer.id] = layer

    def add_tileset(self, tileset: TiledTileset) -> None:
        self.tilesets.append(tileset)
        self._tileset_properties = ChainMap(*[ts.tile_properties for ts in self.tilesets])

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
