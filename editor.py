import os
import subprocess
import sys

import pygame
import tkinter as tk
from tkinter import messagebox, ttk

from tkinter import X, filedialog, LEFT, BOTH, TOP

from typing import Optional, cast, Any
from sys import exit

from pygame import Surface, Rect, K_BACKSPACE

from editor.actions_controller import ActionsController, ChangeKind
from editor.hierarchy import Hierarchy
from editor.main_window import MainWindow
from editor.properties import Properties
from editor.map_controller import MapController
from editor.tileset_controller import TilesetController, TilesetActionsPanel
from engine.tmx import TiledMap, TiledElement, TiledTileset, BaseTiledLayer, TiledObject, TiledObjectGroup

MOUSE_DOWN_COUNTER = 1


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class Editor:
    def __init__(self) -> None:
        self.macos = sys.platform == 'darwin'
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
        self.hamburger_menu_image: Optional[tk.PhotoImage] = None

        self._selected_object: Optional[TiledElement] = None

        self.file_menu: Optional[tk.Menu] = None
        self.edit_menu: Optional[tk.Menu] = None
        self.map_menu: Optional[tk.Menu] = None
        self.run_menu: Optional[tk.Menu] = None
        self.help_menu: Optional[tk.Menu] = None

        self._tiled_map: Optional[TiledMap] = None

        self._current_element: Optional[TiledElement] = None
        self._current_tileset: Optional[TiledTileset] = None

        # Initialisation of other components

        # tk.Tk() and pygame.init() must be done in this order and before anything else (in tkinter world)
        self.root = tk.Tk()
        self.root.title("Editor")

        pygame.init()

        self.open_tk_window(self.root)
        self.previous_keys = pygame.key.get_pressed()
        self.current_keys = pygame.key.get_pressed()
        self.setup_pygame()
        self.colour = pygame.Color("yellow")
        self.clock = pygame.time.Clock()

        # self.font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "editor", "raleway-medium-webfont.ttf"), 17)
        self.font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "editor", "test_fixed.otf"), 17)

        self.actions_controller = ActionsController()
        self.actions_controller.tiled_map_callbacks.append(self._tiled_map_callback)
        self.actions_controller.current_object_callbacks.append(self._current_object_callback)
        self.actions_controller.undo_redo_callbacks.append(self._undo_redo_callback)
        self.actions_controller.element_attr_change_callbacks.append(self._element_attr_change_callback)
        self.actions_controller.element_property_change_callbacks.append(self._element_property_change_callback)
        self.actions_controller.add_object_callbacks.append(self._object_added_callback)
        self.actions_controller.delete_object_callbacks.append(self._object_deleted_callback)
        self.actions_controller.clean_flag_callbacks.append(self._clean_flag_callback)

        self.viewport = Rect(0, 0, 1150, 900)
        right_column = self.viewport.width - 300

        image_size = 32
        margin = 3

        # self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "editor", "icons.png"))

        self.main_window = MainWindow(self.viewport)

        self._new_map_button = self.main_window.toolbar.add_button(12, callback=self._create_new_map_action)
        self._load_map_button = self.main_window.toolbar.add_button(10, callback=self._load_file_action)
        self._save_map_button = self.main_window.toolbar.add_button(11, 31, callback=self._save_map_action)
        self.main_window.toolbar.add_spacer()
        self._redo_button = self.main_window.toolbar.add_button(13, 33, callback=self._undo_action)
        self._undo_button = self.main_window.toolbar.add_button(14, 34, callback=self._redo_action)
        self.main_window.toolbar.add_spacer()
        self._cut_button = self.main_window.toolbar.add_button(16, 36, callback=self._undo_action)
        self._copy_button = self.main_window.toolbar.add_button(15, 35, callback=self._redo_action)
        self._paste_button = self.main_window.toolbar.add_button(17, 37, callback=self._undo_action)
        self.main_window.toolbar.add_spacer()

        self._save_map_button.disabled = True
        self._redo_button.disabled = True
        self._undo_button.disabled = True
        self._cut_button.disabled = True
        self._copy_button.disabled = True
        self._paste_button.disabled = True

        toolbar_height = image_size + margin * 2
        self.main_window.tileset_controller = TilesetController(
            # Rect(right_column, toolbar_height, 300, 500),
            Rect(0, 0, 0, 0),
            None,
            self.actions_controller,
            self._tile_selected_callback
        )
        self.main_window.tileset_actions_toolbar = TilesetActionsPanel(
            # Rect(right_column, self.main_window.tileset_controller.rect.bottom + 10, 300, 32),
            Rect(0, 0, 0, 0),
            self.main_window.icon_surface,
            self._add_tileset_action,
            self._remove_tileset_action
        )
        self.main_window.map_controller = MapController(
            # Rect(0, 0, right_column, self.viewport.height),
            # Rect(0, toolbar_height, right_column, self.viewport.height - toolbar_height),
            Rect(0, 0, 0, 0),
            self.font,
            self.main_window.toolbar,
            self.main_window.tileset_controller,
            self.actions_controller,
            self._object_added_callback,
            self._object_selected_callback,
            self._selection_changed_callback
        )
        self.main_window.finish_initialisation()

        self.key_modifier = 0
        self.mouse_x = 0
        self.mouse_y = 0

    def _tiled_map_callback(self, tiled_map: TiledMap) -> None:
        self._tiled_map = tiled_map
        if tiled_map is not None:
            self.file_menu.entryconfig("Save", state="normal")
            self.file_menu.entryconfig("Save as...", state="normal")

            self.map_menu.entryconfig("Add Tileset", state="normal")

            self.main_window.map_controller.set_action_panel_visibility(True)
            self.hierarchy_view.set_map(tiled_map)

        else:
            self.file_menu.entryconfig("Save", state="disabled")
            self.file_menu.entryconfig("Save as...", state="disabled")

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
                self.custom_properties.update_properties(element.properties)
            elif kind == ChangeKind.UPDATE_PROPERTY:
                self.custom_properties.update_value(key, value)
            elif kind == ChangeKind.DELETE_PROPERTY:
                self.custom_properties.update_properties(element.properties)

    @property
    def current_element(self) -> Optional[TiledElement]:
        return self._current_element

    @current_element.setter
    def current_element(self, current_element: Optional[TiledElement]) -> None:
        self._current_element = current_element

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

    def _object_added_callback(self, layer: TiledObjectGroup, obj: TiledObject) -> None:
        self.hierarchy_view.add_object(layer, obj)
        self.hierarchy_view.selected_object = obj
        self.root.update()

    def _object_deleted_callback(self, layer: TiledObjectGroup, obj: TiledObject) -> None:
        self.hierarchy_view.delete_object(layer, obj)
        self.hierarchy_view.selected_object = None
        self.root.update()

    def _object_selected_callback(self, obj: TiledObject) -> None:
        self.current_element = obj
        self.hierarchy_view.selected_object = obj

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

    def _tile_selected_callback(self, _tile_id: Optional[int]) -> None:
        # TODO do we want to have it exposed in properties (hierarchy)?
        self.main_window.map_controller.tile_selection_changed()

    def _clean_flag_callback(self, clean_flag) -> None:
        if self._tiled_map is not None and self._tiled_map.filename is not None and self._tiled_map.filename != "":
            filename = os.path.split(self._tiled_map.filename)[-1]
            pygame.display.set_caption(f"{'' if clean_flag else '* '} {filename}")
        else:
            pygame.display.set_caption("Editor")

        self._save_map_button.disabled = clean_flag

    def _quit_action(self, _event=None) -> None:
        self.running = False
        pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    def _add_tileset_action(self) -> None:
        # if self._tiled_map.filename is None:
        #     tk.messagebox.showerror(title="Error", message=f"You first must save the map")
        #     return

        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Tileset file", "*.tsx"), ))
        if filename != "":
            tileset = TiledTileset(self._tiled_map)
            tileset.firstgid = self._tiled_map.maxgid + 1
            tileset.source = filename
            self._tiled_map.add_tileset(tileset)
            if len(self._tiled_map.tilesets) == 1:
                self._tiled_map.tilewidth = tileset.tilewidth
                self._tiled_map.tileheight = tileset.tileheight
            self.hierarchy_view.set_map(self._tiled_map)
            self.hierarchy_view.selected_object = tileset

    def _remove_tileset_action(self) -> None:
        print(f"Calculate removing tileset")

    def _load_file_action(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        if filename != "":
            self.load_file(filename)

    def _save_map_action(self, _event=None) -> None:
        if self._tiled_map.filename is None:
            self._save_as_map_action()
        else:
            self._tiled_map.save(self._tiled_map.filename)
            filename = os.path.split(self._tiled_map.filename)[-1]
            pygame.display.set_caption(filename)
            self.actions_controller.mark_saved()

    def _save_as_map_action(self, _event=None) -> None:
        filename = filedialog.asksaveasfilename(title="Save map", filetypes=(("Map file", "*.tmx"),))
        if filename != "":
            self._tiled_map.filename = filename
            self._save_map_action()

    def _cut_action(self, _event=None) -> None:
        print(f"CUT for {self.current_element}")

    def _copy_action(self, _event=None) -> None:
        print(f"COPY for {self.current_element}")

    def _paste_action(self, _event=None) -> None:
        print(f"PASTE for {self.current_element}")

    def _redo_action(self, _event=None) -> None:
        self.main_window.map_controller.deselect_object()
        self.actions_controller.redo()

    def _undo_action(self, _event=None) -> None:
        self.main_window.map_controller.deselect_object()
        self.actions_controller.undo()

    def _select_all_action(self, _event=None) -> None:
        self.main_window.map_controller.select_all()

    def _select_none_action(self, _event=None) -> None:
        self.main_window.map_controller.select_none()

    def _create_new_map_action(self, _event=None) -> None:
        self.actions_controller.create_new_map()

    def _run_map_action(self, _event=None) -> None:
        self.run_map()

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

            if key == "name":
                if isinstance(self._current_element, TiledObject):
                    self.hierarchy_view.update_object_name(cast(TiledObject, self._current_element))
                elif isinstance(self._current_element, BaseTiledLayer):
                    self.hierarchy_view.update_layer_name(cast(BaseTiledLayer, self._current_element))

    def add_current_element_property(self, key: str, value: str) -> None:
        if self._current_element is not None:
            self.actions_controller.add_element_property(self._current_element, key, value)

    def update_current_element_property(self, key: str, value: str) -> None:
        if self._current_element is not None:
            self.actions_controller.update_element_property(self._current_element, key, value)

    def delete_current_element_property(self, key: str) -> None:
        if self._current_element is not None:
            self.actions_controller.delete_element_property(self._current_element, key)

    @staticmethod
    def _do_nothing_action(_event=None) -> None:
        print("Do nothing!")

    def load_file(self, filename: str) -> None:
        tiled_map = TiledMap()
        tiled_map.load(filename)
        self.actions_controller.tiled_map = tiled_map
        map_name = self._tiled_map.name
        if map_name is not None:
            self.run_menu.entryconfig(1, label=f"Run '{map_name}'", state="normal")
        else:
            self.run_menu.entryconfig(1, label=f"Run", state="normal")

        filename = os.path.split(self._tiled_map.filename)[-1]
        pygame.display.set_caption(filename)
        self.actions_controller.mark_saved()

    def run_map(self) -> None:
        if "code" in self._tiled_map.properties:
            python_file = self._tiled_map.properties["code"]
            map_file = self._tiled_map.filename if self._tiled_map.filename is not None else os.getcwd()
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
                    return None

                python_exec = find_python()
                if python_exec is None:
                    tk.messagebox.showerror(title="Error", message=f"Cannot find python exec in PATH environment variable")
                    return
            else:
                tk.messagebox.showerror(title="Error", message=f"Cannot find python exec")
                return

            python_exec = os.path.abspath(python_exec)
            python_file = os.path.split(full_python_file)[-1]
            python_file_dir = os.path.abspath(os.path.dirname(full_python_file))
            print(f"Running '{python_exec} {python_file}' in {python_file_dir}")
            subprocess.Popen([f"{python_exec}", python_file], cwd=python_file_dir)
            return
        else:
            tk.messagebox.showerror(title="Error", message="No 'code' property in the map")

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        control_modifier = "Command" if self.macos else "Control"

        root.geometry("300x900+10+30")
        root.protocol("WM_DELETE_WINDOW", self._quit_action)
        root.title("Edit object")

        left_frame = tk.Frame(root)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)
        right_frame = left_frame

        self.menu_panel = tk.Canvas(left_frame)
        self.menu_panel.columnconfigure(1, weight=1)
        # self.hamburger_menu_image = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "editor", "hamburger-menu.png"))

        # menu = tk.Menu(root)
        menu_button = pack(
            ttk.Menubutton(
                self.menu_panel,
                style="TButton",
                text="Menu",
                # image=self.hamburger_menu_image
            ), fill=X)
        menu = tk.Menu(menu_button)
        menu_button.menu = menu
        menu_button["menu"] = menu
        menu_button.grid(row=0, column=0, ipady=3, padx=3, pady=3, sticky=tk.W)

        pack(self.menu_panel, fill=X)

        self.file_menu = tk.Menu(menu, tearoff=0)
        self.file_menu.add_command(label="New", command=self._create_new_map_action, accelerator=f"{control_modifier}+N")
        self.file_menu.add_command(label="Open", command=self._load_file_action)
        self.file_menu.add_command(label="Save", command=self._save_map_action, state="disabled", accelerator=f"{control_modifier}+S")
        self.file_menu.add_command(label="Save as...", command=self._save_as_map_action, state="disabled", accelerator=f"Shift+{control_modifier}+X")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self._quit_action, accelerator=f"{control_modifier}+Q")
        menu.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(menu, tearoff=0)
        self.edit_menu.add_command(label="Redo", command=self._redo_action, state="disabled", accelerator=f"{control_modifier}+Y")
        self.edit_menu.add_command(label="Undo", command=self._undo_action, state="disabled", accelerator=f"{control_modifier}+Z")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self._cut_action, state="disabled", accelerator=f"{control_modifier}+X")
        self.edit_menu.add_command(label="Copy", command=self._copy_action, state="disabled", accelerator=f"{control_modifier}+C")
        self.edit_menu.add_command(label="Paste", command=self._paste_action, state="disabled", accelerator=f"{control_modifier}+V")
        self.edit_menu.add_command(label="Delete", command=self._delete_action, state="disabled", accelerator="Delete")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Select All", command=self._select_all_action, state="disabled", accelerator=f"{control_modifier}+A")
        self.edit_menu.add_command(label="Select None", command=self._select_none_action, state="disabled", accelerator=f"Shift+{control_modifier}+A")

        menu.add_cascade(label="Edit", menu=self.edit_menu)

        self.map_menu = tk.Menu(menu, tearoff=0)
        self.map_menu.add_command(label="Add Tileset", command=self._add_tileset_action, state="disabled")

        menu.add_cascade(label="Map", menu=self.map_menu)

        self.run_menu = tk.Menu(menu, tearoff=0)
        self.run_menu.add_command(label="Run", command=self._run_map_action, state="disabled", accelerator="{control_modifier}+R")

        menu.add_cascade(label="Run", menu=self.run_menu)

        self.help_menu = tk.Menu(menu, tearoff=0)
        self.help_menu.add_command(label="Help Index", command=self._do_nothing_action, state="disabled")
        self.help_menu.add_command(label="About...", command=self._do_nothing_action, state="disabled")
        menu.add_cascade(label="Help", menu=self.help_menu)
        # root.config(menu=menu)

        root.bind_all("<Delete>", self._delete_action)
        root.bind_all(f"<{control_modifier}-q>", self._quit_action)
        root.bind_all(f"<{control_modifier}-n>", self._create_new_map_action)
        root.bind_all(f"<{control_modifier}-s>", self._save_map_action)
        root.bind_all(f"<Shift-{control_modifier}-s>", self._save_as_map_action)
        root.bind_all(f"<{control_modifier}-x>", self._cut_action)
        root.bind_all(f"<{control_modifier}-c>", self._copy_action)
        root.bind_all(f"<{control_modifier}-v>", self._paste_action)
        root.bind_all(f"<{control_modifier}-a>", self._select_all_action)
        root.bind_all(f"<Shift-{control_modifier}-c>", self._select_none_action)
        root.bind_all(f"<{control_modifier}-r>", self._run_map_action)
        root.bind_all(f"<{control_modifier}-z>", self._undo_action)
        root.bind_all(f"<{control_modifier}-y>", self._redo_action)

        pack(tk.Label(right_frame, text="Hierarchy"), fill=X)
        self.hierarchy_view = Hierarchy(right_frame, self._set_selected_element)
        self.hierarchy_view.pack(side=TOP, fill=X, expand=True)

        pack(tk.Label(left_frame, text="Properties"), fill=X)

        self.main_properties = Properties(left_frame, self.macos, None, self.update_current_element_attribute, None)

        pack(tk.Label(left_frame, text=""), fill=X)
        pack(tk.Label(left_frame, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(left_frame,
                                            self.macos,
                                            self.add_current_element_property,
                                            self.update_current_element_property,
                                            self.delete_current_element_property)

        self.button_panel = tk.Canvas(left_frame)
        self.button_panel.columnconfigure(1, weight=1)

        self.add_property = tk.Button(self.button_panel, text="+", state="disabled", command=self.custom_properties.start_add_new_property)
        self.remove_property = tk.Button(self.button_panel, text="-", state="disabled", command=self.custom_properties.remove_property)
        self.edit_property = tk.Button(
            self.button_panel, text="edit", state="disabled",
            command=lambda: self.custom_properties.start_editing(self.custom_properties.selected_rowid)
        )

        self.add_property.grid(row=0, column=0, pady=3, padx=3, sticky=tk.W)
        self.remove_property.grid(row=0, column=1, pady=3, padx=3, sticky=tk.W)
        self.edit_property.grid(row=0, column=2, pady=3, padx=3, sticky=tk.W)

        pack(self.button_panel, fill=X)

        self.hierarchy_view.init_properties_widgets(self.main_properties, self.custom_properties)
        self.custom_properties.update_buttons(self.add_property, self.remove_property, self.edit_property)

        return root

    def setup_pygame(self) -> None:
        if self.macos:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,58"
        else:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,30"

        self.screen = pygame.display.set_mode((1150, 900))
        self.screen_rect = self.screen.get_rect()
        pygame.display.set_caption("Editor")

    def pygame_loop(self) -> None:
        control_modifier = pygame.KMOD_META if self.macos else pygame.KMOD_CTRL
        self.key_modifier = 0
        self.root.update()

        has_focus = False
        mouse_down_counter = 0
        while self.running:
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
                        if event.mod & control_modifier != 0:
                            self._copy_action()
                    elif key == pygame.K_x:
                        if event.mod & control_modifier != 0:
                            self._cut_action()
                    elif key == pygame.K_v:
                        if event.mod & control_modifier != 0:
                            self._paste_action()
                    elif key == pygame.K_a:
                        if event.mod & control_modifier != 0:
                            if event.mod & pygame.KMOD_SHIFT:
                                self._select_none_action()
                            else:
                                self._select_all_action()
                    elif key == pygame.K_q:
                        if event.mod & control_modifier != 0:
                            self._quit_action()
                    elif key == pygame.K_r:
                        if event.mod & control_modifier != 0:
                            self._run_map_action()
                    elif key == pygame.K_n:
                        if event.mod & control_modifier != 0:
                            self._create_new_map_action()
                    elif key == pygame.K_o:
                        if event.mod & control_modifier != 0:
                            self._load_file_action()
                    elif key == pygame.K_s:
                        if event.mod & control_modifier != 0:
                            if event.mod & pygame.KMOD_SHIFT:
                                self._save_as_map_action()
                            else:
                                self._save_map_action()
                    elif key == pygame.K_z:
                        if event.mod & control_modifier != 0:
                            self._undo_action()
                    elif key == pygame.K_y:
                        if event.mod & control_modifier != 0:
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


if __name__ == '__main__':
    editor = Editor()

    if len(sys.argv) > 1:
        editor.load_file(sys.argv[1])
    else:
        print("No arguments given")
        editor.actions_controller.create_new_map()

    editor.pygame_loop()
