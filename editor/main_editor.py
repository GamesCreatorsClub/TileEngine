import traceback

from pathlib import Path
from zipfile import ZipFile

import functools

import os
import subprocess
import sys

import pygame
import tkinter as tk
from tkinter import messagebox, ttk

from tkinter import X, filedialog, LEFT, BOTH, TOP, BOTTOM

from typing import Optional, cast, Any, Callable
from sys import exit

from pygame import Surface, Rect, K_BACKSPACE

from editor.actions_controller import ActionsController, ChangeKind
from editor.clipboard_controller import ClipboardController, element_property
from editor.hierarchy import Hierarchy
from editor.info_panel import InfoPanel
from editor.main_window import MainWindow
from editor.mini_map_controller import MiniMap
from editor.new_tileset_popup import NewTilesetPopup
from editor.properties import Properties
from editor.map_controller import MapController
from editor.python_boilerplate import PythonBoilerplateDialog, PYTHON_FILE_PROPERTY
from editor.tileset_controller import TilesetController, TilesetActionsPanel
from editor.tooltip import ToolTip
from editor import resources_prefix
from editor.tk_utils import pack, bindtag, handle_exception_tk

from engine.tmx import TiledMap, TiledElement, TiledTileset, BaseTiledLayer, TiledObject, TiledObjectGroup, Tile, TiledTileLayer

MOUSE_DOWN_COUNTER = 1


class Editor:
    def __init__(self) -> None:
        self.macos = sys.platform == 'darwin'
        self.tk_control_modifier = "Command" if self.macos else "Control"

        self.running = True
        self.speed = 10
        self.screen: Optional[Surface] = None
        self.screen_rect: Optional[Rect] = None
        self.main_properties: Optional[Properties] = None
        self.custom_properties: Optional[Properties] = None
        self.hierarchy_view: Optional[Hierarchy] = None
        self.menu_panel: Optional[tk.Canvas] = None
        self.button_panel: Optional[tk.Canvas] = None
        self.add_property: Optional[tk.Button] = None
        self.remove_property: Optional[tk.Button] = None
        self.edit_property: Optional[tk.Button] = None
        self.tkinter_images: dict[str, tk.PhotoImage] = {}
        self.property_buttons: list[tk.Button] = []
        self.property_buttons_tooltips: list[ToolTip] = []
        self._tiled_object_known_properties: list[tuple[str, Callable[[], None]]] = [
            ("on_create", functools.partial(self._add_new_property_with_name, "on_create")),
            ("on_enter", functools.partial(self._add_new_property_with_name, "on_enter")),
            ("on_leave", functools.partial(self._add_new_property_with_name, "on_leave")),
            ("on_collision", functools.partial(self._add_new_property_with_name, "on_collision")),
            ("on_animate", functools.partial(self._add_new_property_with_name, "on_animate")),
        ]
        self._map_known_properties: list[tuple[str, Callable[[], None]]] = [
            ("on_create", functools.partial(self._add_new_property_with_name, "on_create")),
            ("on_show", functools.partial(self._add_new_property_with_name, "on_show")),
        ]

        self._selected_object: Optional[TiledElement] = None

        self.tk_window: Optional[tk.Frame] = None
        self.file_menu: Optional[tk.Menu] = None
        self.edit_menu: Optional[tk.Menu] = None
        self.map_menu: Optional[tk.Menu] = None
        self.run_menu: Optional[tk.Menu] = None
        self.help_menu: Optional[tk.Menu] = None

        self.run_button: Optional[tk.Button] = None

        self._tiled_map: Optional[TiledMap] = None

        self._current_element: Optional[TiledElement] = None
        self._current_tileset: Optional[TiledTileset] = None

        self.actions_controller = ActionsController()

        # Initialisation of other components

        # tk.Tk() and pygame.init() must be done in this order and before anything else (in tkinter world)
        self.root = tk.Tk()
        self.root.title("Editor")

        pygame.init()
        self.pygame_control_modifier = pygame.KMOD_META if self.macos else pygame.KMOD_CTRL

        self.open_tk_window(self.root)
        self.previous_keys = pygame.key.get_pressed()
        self.current_keys = pygame.key.get_pressed()
        self.setup_pygame()
        self.colour = pygame.Color("yellow")
        self.clock = pygame.time.Clock()

        # self.font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "editor", "raleway-medium-webfont.ttf"), 17)
        self.font = pygame.font.Font(os.path.join(resources_prefix.RESOURCES_PREFIX, "editor", "test_fixed.otf"), 17)

        self.actions_controller.tiled_map_callbacks.append(self._tiled_map_callback)
        self.actions_controller.current_object_callbacks.append(self._current_object_callback)
        self.actions_controller.undo_redo_callbacks.append(self._undo_redo_callback)
        self.actions_controller.element_attr_change_callbacks.append(self._element_attr_change_callback)
        self.actions_controller.element_property_change_callbacks.append(self._element_property_change_callback)
        self.actions_controller.add_object_callbacks.append(self._object_added_callback)
        self.actions_controller.delete_object_callbacks.append(self._object_deleted_callback)
        self.actions_controller.clean_flag_callbacks.append(self._clean_flag_callback)
        self.actions_controller.add_tileset_callbacks.append(self._add_tileset_callback)
        self.actions_controller.remove_tileset_callbacks.append(self._remove_tileset_callback)

        self.clipboard_controller = ClipboardController(self.actions_controller)
        self.clipboard_controller.clipboard_callbacks.append(self._clipboard_state_changed)

        self.viewport = Rect(0, 0, 1150, 900)

        # self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "editor", "icons.png"))

        self.main_window = MainWindow(self.viewport)

        self._new_map_button = self.main_window.toolbar.add_button(12, callback=self._create_new_map_action)
        self._load_map_button = self.main_window.toolbar.add_button(10, callback=self._load_file_action)
        self._save_map_button = self.main_window.toolbar.add_button(11, -11, callback=self._save_map_action)
        self.main_window.toolbar.add_spacer()
        self._redo_button = self.main_window.toolbar.add_button(13, -13, callback=self._undo_action)
        self._undo_button = self.main_window.toolbar.add_button(14, 34, callback=self._redo_action)
        self.main_window.toolbar.add_spacer()
        self._cut_button = self.main_window.toolbar.add_button(16, -16, callback=self._cut_action)
        self._copy_button = self.main_window.toolbar.add_button(15, -15, callback=self._copy_action)
        self._paste_button = self.main_window.toolbar.add_button(17, -17, callback=self._paste_action)
        self.main_window.toolbar.add_spacer()

        self._save_map_button.disabled = True
        self._redo_button.disabled = True
        self._undo_button.disabled = True
        self._cut_button.disabled = True
        self._copy_button.disabled = True
        self._paste_button.disabled = True

        self.main_window.tileset_controller = TilesetController(
            # Rect(right_column, toolbar_height, 300, 500),
            Rect(0, 0, 0, 0),
            None,
            self.actions_controller,
            self._tile_selected_callback,
            self._tileset_grid_toggle_callback
        )
        self.main_window.tileset_actions_toolbar = TilesetActionsPanel(
            # Rect(right_column, self.main_window.tileset_controller.rect.bottom + 10, 300, 32),
            Rect(0, 0, 0, 0),
            self.main_window.icon_surface,
            self._add_tileset_action,
            self._remove_tileset_action,
            self.main_window.tileset_controller.grid_on_off,
            self._add_tile_action,
            self._erase_tile_action
        )
        self.main_window.map_controller = MapController(
            # Rect(0, 0, right_column, self.viewport.height),
            # Rect(0, toolbar_height, right_column, self.viewport.height - toolbar_height),
            Rect(0, 0, 0, 0),
            self.font,
            self.main_window.toolbar,
            self.main_window.tileset_controller,
            self.actions_controller,
            self.clipboard_controller,
            self._object_added_callback,
            self._object_selected_callback,
            self._selection_changed_callback
        )
        self.main_window.mini_map = MiniMap(Rect(0, 0, 0, 0), self.actions_controller, self.main_window.map_controller)
        self.main_window.info_panel = InfoPanel(Rect(0, 0, 0, 0), self.font, self.actions_controller)
        self.main_window.finish_initialisation()

        self.key_modifier = 0
        self.mouse_x = 0
        self.mouse_y = 0

    def _add_new_property_with_name(self, property_name: str) -> None:
        self.custom_properties.add_new_property_with_name(property_name)

    def _update_property_buttons(self) -> None:
        if self.hierarchy_view.selected_object is not None:
            known_properties = []
            if isinstance(self.hierarchy_view.selected_object, TiledObject):
                known_properties = self._tiled_object_known_properties
            elif isinstance(self.hierarchy_view.selected_object, TiledMap):
                known_properties = self._map_known_properties

            for i, (name, callback) in enumerate(known_properties):
                disabled = name in self.hierarchy_view.selected_object.properties
                self.property_buttons[i].configure(
                    state="disabled" if disabled else "normal",
                    image=self.tkinter_images[name + ("-disabled" if disabled else "")],
                    command=callback
                )
                self.property_buttons_tooltips[i].disabled = disabled
                self.property_buttons_tooltips[i].text = f"Add {name} property"

            for i in range(len(self._tiled_object_known_properties), 5):
                self.property_buttons[i].configure(state="disabled", image=self.tkinter_images["empty-disabled"])
                self.property_buttons_tooltips[i].disabled = True

    def _clipboard_state_changed(self, copy: bool, cut: bool, paste: bool) -> None:
        self._copy_button.disabled = not copy
        self._cut_button.disabled = not cut
        self._paste_button.disabled = not paste

    def _tiled_map_callback(self, tiled_map: TiledMap) -> None:
        self._tiled_map = tiled_map
        self.file_menu.entryconfig("Save", state="normal")
        self.file_menu.entryconfig("Save as...", state="normal")

        self.map_menu.entryconfig("Add Tileset", state="normal")
        self.map_menu.entryconfig("Update Animations", state="normal")
        self.run_menu.entryconfig("Create Game", state="normal")

        self.main_window.map_controller.set_action_panel_visibility(True)
        self.hierarchy_view.set_map(tiled_map)
        self._update_property_buttons()

    def _current_object_callback(self, current_object: Optional[TiledObject]) -> None:
        self.edit_menu.entryconfig("Delete", state="normal" if current_object is not None else "disabled")

    def _current_tileset_callback(self, current_tileset: Optional[TiledTileset]) -> None:
        self._current_tileset = current_tileset

    def _undo_redo_callback(self, undos: bool, redos: bool) -> None:
        # print(f"Undo/redo changed {undos}, {redos}")
        self.edit_menu.entryconfig("Redo", state="normal" if redos else "disabled")
        self.edit_menu.entryconfig("Undo", state="normal" if undos else "disabled")
        self._undo_button.disabled = not redos
        self._redo_button.disabled = not undos

    def _element_attr_change_callback(self, element: TiledElement, _kind: ChangeKind, key: str, value: Any) -> None:
        if element == self.current_element:
            if key == "name":
                if isinstance(self._current_element, TiledObject):
                    self.hierarchy_view.update_object_name(cast(TiledObject, self._current_element))
                elif isinstance(self._current_element, BaseTiledLayer):
                    self.hierarchy_view.update_layer_name(cast(BaseTiledLayer, self._current_element))
            self.main_properties.update_value(key, value, no_callback=True)

    def _element_property_change_callback(self, element: TiledElement, kind: ChangeKind, key: str, value: Any) -> None:
        if element == self.current_element:
            if kind == ChangeKind.ADD_PROPERTY:
                self.custom_properties.update_properties(element.properties, type(element).OPTIONAL_CUSTOM_PROPERTIES)
            elif kind == ChangeKind.UPDATE_PROPERTY:
                if self.current_element.properties[key] != value:
                    self.custom_properties.update_value(key, value, True)
            elif kind == ChangeKind.DELETE_PROPERTY:
                self.custom_properties.update_properties(element.properties)
            self._update_property_buttons()

    def _add_tileset_callback(self, tileset: TiledTileset) -> None:
        self.hierarchy_view.set_map(self._tiled_map)
        self.hierarchy_view.selected_object = tileset
        self._update_property_buttons()

    def _remove_tileset_callback(self, tileset: TiledTileset) -> None:
        self.hierarchy_view.set_map(self._tiled_map)
        if self.hierarchy_view.selected_object == tileset:
            self.hierarchy_view.selected_object = None
        self._update_property_buttons()

    @property
    def current_element(self) -> Optional[TiledElement]:
        return self._current_element

    @current_element.setter
    def current_element(self, current_element: Optional[TiledElement]) -> None:
        self._current_element = current_element
        self.clipboard_controller.focused_element = current_element

        self.add_property.configure(state="normal" if current_element is not None else "disabled")

        if isinstance(current_element, BaseTiledLayer):
            self.actions_controller.current_layer = cast(BaseTiledLayer, current_element)
            # TODO Move to approporiate callback
            self.edit_menu.entryconfig("Delete", state="disabled")
        elif isinstance(current_element, TiledTileset):
            self.actions_controller.current_tileset = cast(TiledTileset, current_element)

            # TODO Move to approporiate callback
            self.edit_menu.entryconfig("Delete", state="disabled")
        elif isinstance(current_element, TiledObject):
            self.actions_controller.current_object = cast(TiledObject, current_element)
        else:
            # TODO Move to approporiate callback
            self.edit_menu.entryconfig("Delete", state="disabled")

        self._update_property_buttons()

    def _property_selection_callback(self, key: Optional[str]) -> None:
        element_property.key = key
        element_property.element = self.hierarchy_view.selected_object
        self.custom_properties.selection()
        self.clipboard_controller.focused_element = element_property

    def _object_added_callback(self, layer: TiledObjectGroup, obj: TiledObject) -> None:
        self.hierarchy_view.add_object(layer, obj)
        self.hierarchy_view.selected_object = obj
        self._update_property_buttons()
        self.root.update()
        self.main_properties.start_editing("name")

    def _object_deleted_callback(self, layer: TiledObjectGroup, obj: TiledObject) -> None:
        self.hierarchy_view.delete_object(layer, obj)
        self.hierarchy_view.selected_object = None
        self._update_property_buttons()
        self.root.update()

    def _object_selected_callback(self, obj: TiledObject) -> None:
        self.current_element = obj
        self.hierarchy_view.selected_object = obj
        self._update_property_buttons()

    def _selection_changed_callback(self, selection: list[Rect]) -> None:
        if len(selection) > 0:
            if len(selection) == 1:
                self.edit_menu.entryconfig("Cut", state="normal")
                self.edit_menu.entryconfig("Copy", state="normal")
            else:
                self.edit_menu.entryconfig("Cut", state="disabled")
                self.edit_menu.entryconfig("Copy", state="disabled")
            self.edit_menu.entryconfig("Delete", state="normal")
        else:
            self.edit_menu.entryconfig("Cut", state="disabled")
            self.edit_menu.entryconfig("Copy", state="disabled")
            self.edit_menu.entryconfig("Delete", state="disabled")

    def _set_selected_element(self, selected_element: Optional[TiledElement]) -> None:
        self.current_element = selected_element

    def _tile_selected_callback(self, data: Optional[list[list[int]]]) -> None:
        # TODO do we want to have it exposed in properties (hierarchy)?
        self.main_window.map_controller.tile_selection_changed()
        self.main_window.info_panel.tile_selection_changed(self.main_window.tileset_controller.selection)
        if len(data) == 1 and len(data[0]) == 1:
            # 1x1 selection
            gid = data[0][0]
            if gid in self._tiled_map.tiles:
                tile = self._tiled_map.tiles[gid]
                self._current_element = tile

                self.main_properties.update_properties(
                    {k: getattr(tile, k) for k in type(tile).ATTRIBUTES.keys()},
                    type(tile).ATTRIBUTES
                )
                self.custom_properties.update_properties(tile.properties, type(tile).OPTIONAL_CUSTOM_PROPERTIES)

    def _clean_flag_callback(self, clean_flag) -> None:
        if self._tiled_map.filename is not None and self._tiled_map.filename != "":
            filename = Path(self._tiled_map.filename).name
            pygame.display.set_caption(f"{'' if clean_flag else '* '} {filename}")
        else:
            pygame.display.set_caption("Editor")

        self._save_map_button.disabled = clean_flag

    def _quit_action(self, _event=None) -> None:
        self.running = False
        pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    @handle_exception_tk
    def _add_tileset_action(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Tileset file", "*.tsx"), ("PNG Image", "*.png"), ("JPeg Image", "*.jpg"), ("JPeg Image", "*.jpeg")))
        if filename != "":
            if filename.endswith(".tsx"):
                self.actions_controller.add_tileset(filename)
            else:
                image_filename = Path(filename)
                suggested_tsx_filename = image_filename.name
                suffix = image_filename.suffix

                suggested_tsx_filename = (suggested_tsx_filename[:-len(suffix)] if len(suffix) > 0 else suggested_tsx_filename) + ".tsx"

                tsx_filename = filedialog.asksaveasfilename(title="Save TSX file", initialfile=suggested_tsx_filename, filetypes=(("Tileset file", "*.tsx"),))
                if tsx_filename != "":
                    tileset = TiledTileset(self._tiled_map)
                    tileset.update_source_filename(tsx_filename, str(Path(self._tiled_map.filename).parent) if self._tiled_map.filename is not None and self._tiled_map.filename != "" else None)
                    tileset.update_source_image_filename(str(image_filename))

                    simple_filename = os.path.split(tsx_filename)[1]
                    i = simple_filename.rfind(".")
                    tileset.name = simple_filename[:i] if i > 0 else simple_filename

                    tileset.image_surface = pygame.image.load(str(image_filename))

                    def completed_callback(tilewidth: int, tileheight: int, columns: int, spacing: int, margin: int) -> None:
                        print(f"Create new TSX with")
                        print(f"tilewidth, tileheight {tileheight}, {tileheight}")
                        print(f"columns {columns}")
                        print(f"spacing, margin {spacing}, {margin}")
                        tileset.update_shape(tilewidth, tileheight, columns, spacing, margin)
                        tileset.save()
                        self.actions_controller.add_tileset(tsx_filename)

                    NewTilesetPopup(self.root,
                                    self.actions_controller,
                                    tsx_filename,
                                    self.macos,
                                    self.tkinter_images,
                                    tileset.image_surface.get_width(),
                                    completed_callback)

    def _remove_tileset_action(self) -> None:
        tileset_controller = self.main_window.tileset_controller
        self.actions_controller.remove_tileset(tileset_controller.tileset)

    def _tileset_grid_toggle_callback(self, grid_on: bool) -> None:
        self.main_window.tileset_actions_toolbar.grid_button.disabled = grid_on

    def _add_tile_action(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(
            ("png", "*.png"), ("jpg", "*.jpg"), ("jpeg", "*.jpeg"), ("gif", "*.gif")))
        if filename != "":
            tileset_controller = self.main_window.tileset_controller
            x, y = tileset_controller.selection_origin
            self.actions_controller.add_tile(filename, tileset_controller.tileset, x, y)

    def _erase_tile_action(self) -> None:
        tileset_controller = self.main_window.tileset_controller
        x, y = tileset_controller.selection_origin
        self.actions_controller.erase_tile(tileset_controller.tileset, x, y)

    @handle_exception_tk
    def _load_file_action(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        if filename != "":
            self.load_file(filename)

    @handle_exception_tk
    def _save_map_action(self, _event=None) -> None:
        if self._tiled_map.filename is None or self._tiled_map.filename == "":
            self._save_as_map_action()
        else:
            self._tiled_map.save(self._tiled_map.filename)
            filename = Path(self._tiled_map.filename).name
            pygame.display.set_caption(filename)
            self.actions_controller.mark_saved()

        self._update_run_state()

    @handle_exception_tk
    def _save_as_map_action(self, _event=None) -> None:
        filename = filedialog.asksaveasfilename(title="Save map", filetypes=(("Map file", "*.tmx"),))
        if filename != "":
            if not filename.endswith(".tmx"):
                filename = filename + ".tmx"
            self._tiled_map.filename = filename
            self._save_map_action()
        self._update_run_state()

    @handle_exception_tk
    def _cut_action(self, _event=None) -> None:
        self.clipboard_controller.cut()

    @handle_exception_tk
    def _copy_action(self, _event=None) -> None:
        self.clipboard_controller.copy()

    @handle_exception_tk
    def _paste_action(self, _event=None) -> None:
        self.clipboard_controller.paste()

    @handle_exception_tk
    def _redo_action(self, _event=None) -> None:
        self.main_window.map_controller.deselect_object()
        self.actions_controller.redo()

    @handle_exception_tk
    def _undo_action(self, _event=None) -> None:
        self.main_window.map_controller.deselect_object()
        self.actions_controller.undo()

    @handle_exception_tk
    def _select_all_action(self, _event=None) -> None:
        self.main_window.map_controller.select_all()

    @handle_exception_tk
    def _select_none_action(self, _event=None) -> None:
        self.main_window.map_controller.select_none()

    @handle_exception_tk
    def _create_new_map_action(self, _event=None) -> None:
        self.actions_controller.create_new_map()

    @handle_exception_tk
    def _run_map_action(self, _event=None) -> None:
        self.run_map()

    @handle_exception_tk
    def _create_boilerplate_map_action(self, _event=None) -> None:
        self.create_boilerplate_map()

    @handle_exception_tk
    def _update_animations(self, _event=None) -> None:
        for tiled_tileset in self._tiled_map.tilesets:
            tiled_tileset.update_animations()
        for tiled_layer in self._tiled_map.layers:
            if isinstance(tiled_layer, TiledTileLayer):
                tiled_layer.check_if_animated_gids()

    @handle_exception_tk
    def _delete_action(self, _event=None) -> None:
        if self.actions_controller.current_object is not None and self.actions_controller.object_layer is not None:
            obj = self.actions_controller.current_object
            self.actions_controller.delete_object(obj)
            layer = cast(TiledObjectGroup, obj.layer)
            self.hierarchy_view.delete_object(layer, obj)
            self.main_window.map_controller.deselect_object()
        elif self.actions_controller.tiled_layer is not None:
            self.main_window.map_controller.delete_tiles()
        else:
            print(f"No layer selected")

    def update_current_element_attribute(self, key: str, value: str) -> None:
        if self._current_element is not None:

            self.actions_controller.update_element_attribute(self._current_element, key, value)

            if isinstance(self._current_element, TiledTileset):
                cast(TiledTileset, self._current_element).dirty_data = True
            elif isinstance(self._current_element, Tile):
                cast(Tile, self._current_element).tiledset.dirty_data = True

            if key == "name":
                if isinstance(self._current_element, TiledObject):
                    self.hierarchy_view.update_object_name(cast(TiledObject, self._current_element))
                elif isinstance(self._current_element, BaseTiledLayer):
                    self.hierarchy_view.update_layer_name(cast(BaseTiledLayer, self._current_element))

    def add_current_element_property(self, key: str, value: str) -> None:
        if self._current_element is not None:
            self.actions_controller.add_element_property(self._current_element, key, value)
            if isinstance(self._current_element, TiledTileset):
                cast(TiledTileset, self._current_element).dirty_data = True
            elif isinstance(self._current_element, Tile):
                cast(Tile, self._current_element).tiledset.dirty_data = True

    def update_current_element_property(self, key: str, value: str) -> None:
        if self._current_element is not None:
            self.actions_controller.update_element_property(self._current_element, key, value)
            if isinstance(self._current_element, TiledTileset):
                cast(TiledTileset, self._current_element).dirty_data = True
            elif isinstance(self._current_element, Tile):
                cast(Tile, self._current_element).tiledset.dirty_data = True

    def delete_current_element_property(self, key: str) -> None:
        if self._current_element is not None:
            self.actions_controller.delete_element_property(self._current_element, key)
            if isinstance(self._current_element, TiledTileset):
                cast(TiledTileset, self._current_element).dirty_data = True
            elif isinstance(self._current_element, Tile):
                cast(Tile, self._current_element).tiledset.dirty_data = True

    @staticmethod
    def _do_nothing_action(_event=None) -> None:
        print("Do nothing!")

    def load_file(self, filename: str) -> None:
        tiled_map = TiledMap()
        tiled_map.load(filename)
        self.actions_controller.tiled_map = tiled_map
        self._update_run_state()

        filename = Path(self._tiled_map.filename).name
        pygame.display.set_caption(filename)
        self.actions_controller.mark_saved()
        for layer in tiled_map.layers:
            if isinstance(layer, TiledObjectGroup):
                object_layer = cast(TiledObjectGroup, layer)
                for obj in object_layer.objects:
                    if obj.has_create_image():
                        try:
                            obj.create_image_from_property_value()
                        except ValueError as e:
                            print(f"Failed to create images for {obj.name}; error {e}")

    def run_map(self) -> None:
        if PYTHON_FILE_PROPERTY in self._tiled_map.properties:
            python_file = self._tiled_map.properties[PYTHON_FILE_PROPERTY]
            map_file = self._tiled_map.filename if self._tiled_map.filename is not None and self._tiled_map.filename != "" else os.getcwd()
            map_file_dir = os.path.dirname(map_file)

            full_python_file = python_file if os.path.isabs(python_file) else os.path.join(map_file_dir, python_file)

            if not os.path.exists(full_python_file):
                tk.messagebox.showerror(title="Error", message=f"No {full_python_file} file")
                return

            python_file_dir = os.path.dirname(full_python_file)

            venv_dir = os.path.join(python_file_dir, "venv")
            if not os.path.exists(venv_dir):
                venv_dir = os.path.join(python_file_dir, ".venv")

            if os.path.exists(venv_dir):
                python_exec = os.path.join(venv_dir, "bin/python3")
            elif "PATH" in os.environ:
                paths = os.environ["PATH"].split(os.pathsep)

                def find_python() -> Optional[str]:
                    for p in paths:
                        full_python_path = os.path.join(p, "python3")
                        if os.path.exists(full_python_path):
                            return full_python_path
                        full_python_path = os.path.join(p, "python")
                        if os.path.exists(full_python_path):
                            return full_python_path
                        full_python_path = os.path.join(p, "python.exe")
                        if os.path.exists(full_python_path):
                            return full_python_path

                    return None

                python_exec = find_python()
                if python_exec is None:
                    tk.messagebox.showerror(title="Error", message=f"Cannot find python exec in PATH environment variable")
                    return
            else:
                tk.messagebox.showerror(title="Error", message=f"Cannot find python exec")
                return

            python_exec = os.path.abspath(python_exec)
            python_file = os.path.split(full_python_file)[1]
            python_file_dir = os.path.abspath(os.path.dirname(full_python_file))
            print(f"Running '{python_exec} {python_file}' in {python_file_dir}")
            subprocess.Popen([f"{python_exec}", python_file], cwd=python_file_dir)
            return
        else:
            tk.messagebox.showerror(title="Error", message="No 'python_file' property in the map")

    def _update_run_state(self) -> None:
        map_name = self._tiled_map.name

        has_python_file = PYTHON_FILE_PROPERTY in self._tiled_map.properties
        state = "normal" if has_python_file else "disabled"

        if map_name is not None:
            self.run_menu.entryconfig(0, label=f"Run '{map_name}'", state=state)
        else:
            self.run_menu.entryconfig(0, label=f"Run", state=state)

        self.run_button["state"] = state

    def create_boilerplate_map(self) -> None:
        if self._tiled_map.filename is not None and self._tiled_map.filename != "":
            PythonBoilerplateDialog(self.root, self._tiled_map, os.path.dirname(os.path.dirname(__file__)) if resources_prefix.STARTED_FROM_ZIP else None, self._update_run_state)
        else:
            tk.messagebox.showerror(title="Error", message=f"You must save the map first")

    def _add_tk_image(self, name: str) -> tk.PhotoImage:
        image = tk.PhotoImage(file=os.path.join(resources_prefix.RESOURCES_PREFIX, "editor", "images", name + ".png"))
        self.tkinter_images[name] = image
        return image

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        self.tk_control_modifier = "Command" if self.macos else "Control"

        root.geometry("300x900+10+30")
        root.protocol("WM_DELETE_WINDOW", self._quit_action)
        root.title("Edit object")

        self.tk_window = tk.Frame(root)
        self.tk_window.pack(side=LEFT, fill=BOTH, expand=True)

        self.menu_panel = tk.Canvas(self.tk_window)
        self.menu_panel.columnconfigure(2, weight=2)
        bindtag(self.tk_window, self.menu_panel)
        # self.hamburger_menu_image = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "editor", "hamburger-menu.png"))

        menu_button = pack(ttk.Menubutton(
            self.menu_panel,
            style="TButton",
            text="Menu",
            # image=self.hamburger_menu_image
        ), fill=X)

        menu = tk.Menu(menu_button)
        menu_button.menu = menu
        menu_button["menu"] = menu
        menu_button.grid(row=0, column=0, ipady=3, padx=3, pady=3, sticky=tk.W)

        self.run_button = ttk.Button(
            self.menu_panel,
            text="Run",
            state="disabled",
            command=self._run_map_action
        )
        self.run_button.grid(row=0, column=1, ipady=3, padx=3, pady=3, sticky=tk.W)

        pack(self.menu_panel, fill=X)

        self.file_menu = tk.Menu(menu, tearoff=0)
        self.file_menu.add_command(label="New", command=self._create_new_map_action, accelerator=f"{self.tk_control_modifier}+N")
        self.file_menu.add_command(label="Open", command=self._load_file_action)
        self.file_menu.add_command(label="Save", command=self._save_map_action, state="disabled", accelerator=f"{self.tk_control_modifier}+S")
        self.file_menu.add_command(label="Save as...", command=self._save_as_map_action, state="disabled", accelerator=f"Shift+{self.tk_control_modifier}+X")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self._quit_action, accelerator=f"{self.tk_control_modifier}+Q")
        menu.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(menu, tearoff=0)
        self.edit_menu.add_command(label="Redo", command=self._redo_action, state="disabled", accelerator=f"{self.tk_control_modifier}+Y")
        self.edit_menu.add_command(label="Undo", command=self._undo_action, state="disabled", accelerator=f"{self.tk_control_modifier}+Z")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self._cut_action, state="disabled", accelerator=f"{self.tk_control_modifier}+X")
        self.edit_menu.add_command(label="Copy", command=self._copy_action, state="disabled", accelerator=f"{self.tk_control_modifier}+C")
        self.edit_menu.add_command(label="Paste", command=self._paste_action, state="disabled", accelerator=f"{self.tk_control_modifier}+V")
        self.edit_menu.add_command(label="Delete", command=self._delete_action, state="disabled", accelerator="Delete")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Select All", command=self._select_all_action, state="disabled", accelerator=f"{self.tk_control_modifier}+A")
        self.edit_menu.add_command(label="Select None", command=self._select_none_action, state="disabled", accelerator=f"Shift+{self.tk_control_modifier}+A")

        menu.add_cascade(label="Edit", menu=self.edit_menu)

        self.map_menu = tk.Menu(menu, tearoff=0)
        self.map_menu.add_command(label="Add Tileset", command=self._add_tileset_action, state="disabled")
        self.map_menu.add_separator()
        self.map_menu.add_command(label="Update Animations", command=self._update_animations, state="disabled")

        menu.add_cascade(label="Map", menu=self.map_menu)

        self.run_menu = tk.Menu(menu, tearoff=0)
        self.run_menu.add_command(label="Run", command=self._run_map_action, state="disabled", accelerator="{self.control_modifier}+R")
        self.run_menu.add_command(label="Create Game", command=self._create_boilerplate_map_action, state="disabled")

        menu.add_cascade(label="Run", menu=self.run_menu)

        self.help_menu = tk.Menu(menu, tearoff=0)
        self.help_menu.add_command(label="Help Index", command=self._do_nothing_action, state="disabled")
        self.help_menu.add_command(label="About...", command=self._do_nothing_action, state="disabled")
        menu.add_cascade(label="Help", menu=self.help_menu)
        # root.config(menu=menu)

        root.bind_all(f"<{self.tk_control_modifier}-q>", self._quit_action)

        root.bind_all(f"<{self.tk_control_modifier}-n>", self._create_new_map_action)
        root.bind_all(f"<{self.tk_control_modifier}-s>", self._save_map_action)
        root.bind_all(f"<Shift-{self.tk_control_modifier}-s>", self._save_as_map_action)

        pack(tk.Label(self.tk_window, text="Hierarchy"), fill=X)
        self.hierarchy_view = Hierarchy(self.tk_window, self._set_selected_element)
        self.hierarchy_view.pack(side=TOP, fill=BOTH, expand=True)

        pack(tk.Label(self.tk_window, text="Properties"), fill=X)

        self.main_properties = Properties(
            self.tk_window, self.macos,
            self.tkinter_images,
            self.actions_controller,
            None, self.update_current_element_attribute, None, None)

        pack(tk.Label(self.tk_window, text=""), fill=X)
        pack(tk.Label(self.tk_window, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(self.tk_window,
                                            self.macos,
                                            self.tkinter_images,
                                            self.actions_controller,
                                            self.add_current_element_property,
                                            self.update_current_element_property,
                                            self.delete_current_element_property,
                                            self._property_selection_callback)

        self.button_panel = tk.Canvas(self.tk_window)
        self.button_panel.columnconfigure(1, weight=1)

        add_image = self._add_tk_image("add-icon")
        self._add_tk_image("add-icon-disabled")
        self._add_tk_image("remove-icon")
        remove_image = self._add_tk_image("remove-icon-disabled")
        self._add_tk_image("empty")
        self._add_tk_image("empty-disabled")
        self._add_tk_image("on_create")
        self._add_tk_image("on_create-disabled")
        self._add_tk_image("on_enter")
        self._add_tk_image("on_enter-disabled")
        self._add_tk_image("on_leave")
        self._add_tk_image("on_leave-disabled")
        self._add_tk_image("on_collision")
        self._add_tk_image("on_collision-disabled")
        self._add_tk_image("on_animate")
        self._add_tk_image("on_animate-disabled")
        self._add_tk_image("on_show")
        self._add_tk_image("on_show-disabled")

        self.add_property = tk.Button(self.button_panel, text="+", image=add_image, state="disabled", command=self.custom_properties.start_add_new_property)
        self.remove_property = tk.Button(self.button_panel, text="-", image=remove_image, state="disabled", command=self.custom_properties.remove_property)

        def create_known_property_button(property_name: str) -> tk.Button:
            return tk.Button(self.button_panel, text="-", image=self.tkinter_images[f"{property_name}-disabled"], state="disabled")

        self.edit_property = tk.Button(
            self.button_panel, text="edit", state="disabled",
            command=lambda: self.custom_properties.start_editing(self.custom_properties.selected_rowid)
        )

        self.property_buttons = [
            create_known_property_button("empty") for _ in range(5)
        ]
        self.property_buttons_tooltips = [ToolTip(self.property_buttons[i]) for i in range(5)]

        self.add_property.grid(row=0, column=0, pady=3, padx=1, sticky=tk.W)
        self.remove_property.grid(row=0, column=1, pady=3, padx=1, sticky=tk.W)
        for i, b in enumerate(self.property_buttons):
            b.grid(row=0, column=2 + i, pady=3, padx=1, sticky=tk.W)
        self.edit_property.grid(row=0, column=len(self.property_buttons) + 2, pady=1, padx=3, sticky=tk.W)

        pack(self.button_panel, side=BOTTOM, fill=X)

        self.hierarchy_view.init_properties_widgets(self.main_properties, self.custom_properties)
        self.custom_properties.update_buttons(
            self.add_property,
            self.remove_property,
            self.edit_property
        )

        self._bind_keys(self.tk_window)
        self._bind_keys(self.hierarchy_view)

        return root

    def _bind_keys(self, component) -> None:
        component.bind("<Delete>", self._delete_action)
        component.bind(f"<{self.tk_control_modifier}-x>", self._cut_action)
        component.bind(f"<{self.tk_control_modifier}-c>", self._copy_action)
        component.bind(f"<{self.tk_control_modifier}-v>", self._paste_action)
        component.bind(f"<{self.tk_control_modifier}-a>", self._select_all_action)
        component.bind(f"<Shift-{self.tk_control_modifier}-a>", self._select_none_action)
        component.bind(f"<{self.tk_control_modifier}-r>", self._run_map_action)
        component.bind(f"<{self.tk_control_modifier}-z>", self._undo_action)
        component.bind(f"<{self.tk_control_modifier}-y>", self._redo_action)

    def setup_pygame(self) -> None:
        if self.macos:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,58"
        else:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,30"

        self.screen = pygame.display.set_mode((1150, 900), pygame.RESIZABLE)
        self.screen_rect = self.screen.get_rect()
        pygame.display.set_caption("Editor")

    def pygame_loop(self) -> None:
        self.key_modifier = 0
        self.root.update()

        last_exception: Optional[BaseException] = None
        exception_count = 0

        has_focus = False
        mouse_down_counter = 0
        while self.running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._quit_action()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_down_counter = MOUSE_DOWN_COUNTER
                        self.main_window.mouse_down(self.mouse_x, self.mouse_y, event.button, self.key_modifier)
                        self.root.update()
                    elif event.type == pygame.MOUSEBUTTONUP:
                        mouse_down_counter = 0
                        self.main_window.mouse_up(self.mouse_x, self.mouse_y, event.button, self.key_modifier)
                        self.root.update()
                    elif event.type == pygame.MOUSEMOTION:
                        self.mouse_x = event.pos[0]
                        self.mouse_y = event.pos[1]
                        self.main_window.mouse_move(self.mouse_x, self.mouse_y, self.key_modifier)
                        mouse_down_counter = MOUSE_DOWN_COUNTER
                        self.root.update()
                    elif event.type == pygame.VIDEORESIZE:
                        pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                        rect = Rect(0, 0, event.w, event.h)
                        self.main_window.redefine_rect(rect)
                    elif event.type == pygame.WINDOWLEAVE:
                        self.main_window.mouse_out(0, 0)
                        self.root.update()
                    elif event.type == pygame.MOUSEWHEEL:
                        self.main_window.mouse_wheel(self.mouse_x, self.mouse_y, event.x, event.y, self.key_modifier)
                        self.root.update()
                    elif event.type == pygame.KEYDOWN:
                        key = event.key
                        dx = 0
                        dy = 0
                        # print(f"key={key} + mod={event.mod}")
                        if key == pygame.K_RSHIFT or key == pygame.K_LSHIFT:
                            self.key_modifier |= pygame.KMOD_SHIFT
                        elif key == pygame.K_RCTRL or key == pygame.K_LCTRL:
                            self.key_modifier |= pygame.KMOD_CTRL
                        elif key == pygame.K_RMETA or key == pygame.K_LMETA:
                            self.key_modifier |= pygame.KMOD_META
                        elif key == pygame.K_RALT or key == pygame.K_LALT:
                            self.key_modifier |= pygame.KMOD_ALT
                        elif key == pygame.K_RIGHT:
                            dx = 16
                        elif key == pygame.K_LEFT:
                            dx = -16
                        elif key == pygame.K_UP:
                            dy = 16
                        elif key == pygame.K_DOWN:
                            dy = -16
                        elif key == pygame.K_DELETE or key == K_BACKSPACE:
                            self._delete_action()
                            self.root.update()
                        elif key == pygame.K_c:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._copy_action()
                        elif key == pygame.K_x:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._cut_action()
                        elif key == pygame.K_v:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._paste_action()
                        elif key == pygame.K_a:
                            if event.mod & self.pygame_control_modifier != 0:
                                if event.mod & pygame.KMOD_SHIFT:
                                    self._select_none_action()
                                else:
                                    self._select_all_action()
                        elif key == pygame.K_q:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._quit_action()
                        elif key == pygame.K_r:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._run_map_action()
                        elif key == pygame.K_n:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._create_new_map_action()
                        elif key == pygame.K_o:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._load_file_action()
                        elif key == pygame.K_s:
                            if event.mod & self.pygame_control_modifier != 0:
                                if event.mod & pygame.KMOD_SHIFT:
                                    self._save_as_map_action()
                                else:
                                    self._save_map_action()
                        elif key == pygame.K_z:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._undo_action()
                        elif key == pygame.K_y:
                            if event.mod & self.pygame_control_modifier != 0:
                                self._redo_action()

                        if dx != 0 or dy != 0:
                            self.main_window.mouse_wheel(self.mouse_x, self.mouse_y, dx, dy, self.key_modifier)

                    elif event.type == pygame.KEYUP:
                        key = event.key
                        if key == pygame.K_RSHIFT or key == pygame.K_LSHIFT:
                            self.key_modifier -= pygame.KMOD_SHIFT
                        elif key == pygame.K_RCTRL or key == pygame.K_LCTRL:
                            self.key_modifier -= pygame.KMOD_CTRL
                        elif key == pygame.K_RMETA or key == pygame.K_LMETA:
                            self.key_modifier -= pygame.KMOD_META
                        elif key == pygame.K_RALT or key == pygame.K_LALT:
                            self.key_modifier -= pygame.KMOD_ALT
                    elif event.type == pygame.ACTIVEEVENT:
                        # print(f"Active Event")
                        pass
                    elif event.type == pygame.WINDOWENTER:
                        # print(f"Window Enter")
                        pass
                    elif event.type == pygame.WINDOWLEAVE:
                        # print(f"Window Leave")
                        pass
                    elif event.type == pygame.WINDOWFOCUSGAINED:
                        has_focus = True
                    elif event.type == pygame.WINDOWFOCUSLOST:
                        has_focus = False
                    else:
                        # print(f"event.type == {event.type}")
                        pass

                if mouse_down_counter > 0:
                    mouse_down_counter -= 1
                    if mouse_down_counter == 0:
                        mouse_down_counter = MOUSE_DOWN_COUNTER
                        self.main_window.mouse_move(self.mouse_x, self.mouse_y, self.key_modifier)

                self.previous_keys = self.current_keys
                self.current_keys = pygame.key.get_pressed()
                # if self.previous_keys != self.current_keys:
                #     print(f"keys={self.current_keys}")

                self.actions_controller.action_tick()

                self.clock.tick(30)
                self.screen.fill((200, 200, 200))
                self.main_window.draw(self.screen)

                pygame.display.flip()
                if not has_focus:
                    self.root.update()
                last_exception = None
            except BaseException as e:
                display_exception = True
                if str(e) == str(last_exception):
                    exception_count += 1
                    display_exception = exception_count % 100 == 0
                else:
                    exception_count = 0
                last_exception = e
                if display_exception:
                    print(f"*** Caught exception {e} {('(' + str(exception_count) + ')') if exception_count > 0 else ''};\n stacktrace: {traceback.format_tb(e.__traceback__)}")


def prepare_resources() -> None:
    this_zip_file = os.path.dirname(os.path.dirname(__file__))
    current_path = os.path.dirname(this_zip_file)
    temp_dir = os.path.join(current_path, "temp")
    print(f"Temp dir is {temp_dir}")
    editor_dir = os.path.join(temp_dir, "editor")
    images_dir = os.path.join(editor_dir, "images")
    if not os.path.exists(images_dir):
        print(f"Creating {images_dir}")
        os.makedirs(images_dir, exist_ok=True)

    print(f"Opening zipfile {this_zip_file}")
    with ZipFile(this_zip_file) as zf:
        for name in zf.namelist():
            if name.startswith("editor/images/") or name in [
                "editor/test_fixed.otf",
                "editor/icons.png",
                "editor/arrows-small.png"
            ]:
                filename = os.path.join(temp_dir, name)
                with open(filename, "wb") as f:
                    with zf.open(name) as zff:
                        f.write(zff.read())


def prepare_game_resources(game_path: str) -> None:
    this_zip_file = os.path.dirname(os.path.dirname(__file__))
    print(f"Game path is {game_path}")
    engine_dir = os.path.join(game_path, "engine")
    game_dir = os.path.join(game_path, "game")
    if not os.path.exists(engine_dir):
        print(f"Creating {engine_dir}")
        os.makedirs(engine_dir, exist_ok=True)
    if not os.path.exists(game_dir):
        print(f"Creating {game_dir}")
        os.makedirs(game_dir, exist_ok=True)

    print(f"Opening zipfile {this_zip_file}")
    with ZipFile(this_zip_file) as zf:
        for name in zf.namelist():
            if name.startswith("engine") or name.startswith("game"):
                filename = os.path.join(game_path, name)
                path = os.path.dirname(filename)
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                with open(filename, "wb") as f:
                    with zf.open(name) as zff:
                        f.write(zff.read())


def start() -> None:
    this_file_path = os.path.dirname(os.path.dirname(__file__))
    resources_prefix.STARTED_FROM_ZIP = Path(__file__).parts[-3].endswith(".py") or Path(__file__).parts[-3].endswith(".zip")
    if resources_prefix.STARTED_FROM_ZIP:
        prepare_resources()
        resources_prefix.RESOURCES_PREFIX = os.path.join(os.path.dirname(this_file_path), "temp")
    else:
        resources_prefix.RESOURCES_PREFIX = os.path.join(this_file_path)

    editor = Editor()
    if len(sys.argv) > 1:
        editor.load_file(sys.argv[1])
    else:
        print("No arguments given")
        editor.actions_controller.create_new_map()

    editor.pygame_loop()
