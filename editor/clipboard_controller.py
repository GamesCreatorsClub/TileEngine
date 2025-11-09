import re

from pygame import Rect
from typing import Optional, Any, Callable, cast

from abc import ABC

from editor.actions_controller import ActionsController
from engine.tmx import TiledElement, TiledTileLayer, TiledObject, TiledObjectGroup


class ObjectProperty:
    def __init__(self) -> None:
        self.element: Optional[TiledElement] = None
        self.key: str = ""


element_property = ObjectProperty()


class ClipboardContent(ABC):
    def __init__(self, clipboard_controller: 'ClipboardController') -> None:
        self.clipboard_controller = clipboard_controller

    def can_apply(self) -> bool:
        return False

    def apply(self) -> None:
        pass


class ObjectPropertyContent(ClipboardContent):
    def __init__(self, clipboard_controller: 'ClipboardController', element: TiledElement, key: str) -> None:
        super().__init__(clipboard_controller)
        self.element = element
        self.key = key
        self.value = element.properties[key]

    def can_apply(self) -> bool:
        return isinstance(self.clipboard_controller.action_controller.current_object, TiledElement)

    def apply(self) -> None:
        target = self.clipboard_controller.action_controller.current_object
        existing_element = self.key in target.properties
        target.properties[self.key] = self.value

        if existing_element:
            self.clipboard_controller.action_controller.update_element_property(
                target, self.key, self.value
            )
        else:
            self.clipboard_controller.action_controller.add_element_property(
                target, self.key, self.value
            )


class ObjectContent(ClipboardContent):
    def __init__(self, clipboard_controller: 'ClipboardController', tiled_object: TiledObject) -> None:
        super().__init__(clipboard_controller)
        self.tiled_object = tiled_object

    def can_apply(self) -> bool:
        return (isinstance(self.clipboard_controller.action_controller.current_object, TiledObject)
                or isinstance(self.clipboard_controller.action_controller.current_object, TiledObjectGroup))

    def apply(self) -> None:
        target = self.clipboard_controller.action_controller.current_object
        layer: TiledObjectGroup = cast(TiledObjectGroup, target) if isinstance(target, TiledObjectGroup) else cast(TiledObject, target).layer

        new_object = self.tiled_object.copy()
        new_object.parent = layer
        new_object.layer = layer

        name = self.tiled_object.name
        match = re.search(r'_(\d+)$', name)

        i = 0 if match is None else int(match.group()[1:])
        if i > 0:
            name = name[:-len(match.group())]
        while name + ("" if i == 0 else f"_{i}") in layer.object_by_name is not None:
            i += 1

        if i > 0:
            self.tiled_object.name = name + ("" if i == 0 else f"_{i}")

        self.clipboard_controller.action_controller.add_object(self.tiled_object, layer)


# class TileAreaContent(ClipboardContent):
#     def __init__(self, clipboard_controller: 'ClipboardController', area: list[list[int]]) -> None:
#         super().__init__(clipboard_controller)
#         self.area = area
#
#     def apply(self) -> None:
#         target = self.clipboard_controller.action_controller.current_object
#         existing_element = self.key in target.properties
#         target.properties[self.key] = self.value
#
#         if existing_element:
#             self.clipboard_controller.action_controller.update_element_property(
#                 target, self.key, self.value
#             )
#         else:
#             self.clipboard_controller.action_controller.add_element_property(
#                 target, self.key, self.value
#             )
#
#
class ClipboardController:
    def __init__(self, action_controller: ActionsController) -> None:
        self.action_controller = action_controller
        self._content: Optional[ClipboardContent] = None
        self._focused_element: Optional[Any] = None
        self.selection: list[Rect] = []
        self.clipboard_callbacks: list[Callable[[bool, bool, bool], None]] = []

    def _notify_clipboard_callbacks(self) -> None:
        for callback in self.clipboard_callbacks:
            callback(
                self.can_copy(),
                self.can_cut(),
                self.can_paste()
            )

    def clear(self) -> None:
        disable_paste = self._content is not None
        self._content = None
        if disable_paste:
            self._notify_clipboard_callbacks()

    def _set_content(self, content: ClipboardContent) -> None:
        enable_paste = self._content is None
        self._content = content
        if enable_paste:
            self._notify_clipboard_callbacks()

    @property
    def focused_element(self) -> Any:
        return self._focused_element

    @focused_element.setter
    def focused_element(self, focused_element: Any) -> None:
        self._focused_element = focused_element
        self._notify_clipboard_callbacks()

    def copy(self) -> None:
        if self._focused_element is not None:
            if self._focused_element == element_property:
                self._set_content(ObjectPropertyContent(self, element_property.element, element_property.key))
            elif isinstance(self._focused_element, TiledObject):
                self._set_content(ObjectContent(self, cast(TiledObject, self._focused_element).copy()))
            # elif isinstance(self._focused_element, TiledTileLayer):
            #     self._set_content(TileAreaContent(self, element_property.element, element_property.key))

    def cut(self) -> None:
        if self._focused_element is not None:
            if self._focused_element == element_property:
                self._set_content(ObjectPropertyContent(self, element_property.element, element_property.key))
                self.action_controller.delete_element_property(
                    element_property.element, element_property.key
                )

    def can_copy(self) -> bool:
        if self._focused_element is not None:
            if self._focused_element == element_property:
                return True
            elif isinstance(self._focused_element, TiledObject):
                return True
            elif isinstance(self._focused_element, TiledTileLayer):
                return len(self.selection) > 0
        return False

    def can_cut(self) -> bool:
        if self._focused_element is not None:
            if self._focused_element == element_property:
                return True
            elif isinstance(self._focused_element, TiledObject):
                return True
            elif isinstance(self._focused_element, TiledTileLayer):
                return len(self.selection) > 0
        return False

    def can_paste(self) -> bool:
        return self._content is not None and self._content.can_apply()

    def paste(self) -> None:
        if self._content is not None and self._content.can_apply():
            self._content.apply()

    def clear_selection(self) -> None:
        del self.selection[:]
        self._notify_clipboard_callbacks()

    def set_to_selection(self, selection: Rect) -> None:
        del self.selection[:]
        self.selection.append(selection)
        self._notify_clipboard_callbacks()

    def add_to_selection(self, selection: Rect) -> None:
        self.selection.append(selection)
        self._notify_clipboard_callbacks()
