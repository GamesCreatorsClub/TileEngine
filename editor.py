import os
import subprocess
import sys

import pygame
import tkinter as tk
from tkinter import messagebox

from tkinter import X, filedialog, LEFT, BOTH, TOP

from typing import Optional, cast
from sys import exit

from pygame import Surface, Rect, Color, K_BACKSPACE

from editor.hierarchy import Hierarchy
from editor.properties import Properties
from editor.pygame_components import ComponentCollection
from editor.map_canvas import MapCanvas, MapActionsPanel, MapAction
from editor.tileset_canvas import TilesetCanvas
from engine.tmx import TiledMap, TiledElement, TiledTileset, BaseTiledLayer, TiledObject, TiledTileLayer, TiledGroupLayer, TiledObjectGroup

WITH_PYGAME = True
WITH_SCROLLBAR = True

MOUSE_DOWN_COUNTER = 1


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class Editor:
    def __init__(self) -> None:
        self.macos = False
        self.running = True
        self.colour = pygame.Color("yellow")
        self.speed = 10
        self.screen: Optional[Surface] = None
        self.screen_rect: Optional[Rect] = None
        self.main_properties: Optional[Properties] = None
        self.custom_properties: Optional[Properties] = None
        self.hierarchy_view: Optional[Hierarchy] = None
        self.button_panel: Optional[tk.Canvas] = None
        self.add_property: Optional[tk.Button] = None
        self.remove_property: Optional[tk.Button] = None
        self.edit_property: Optional[tk.Button] = None

        self._selected_object: Optional[TiledElement] = None

        self.file_menu: Optional[tk.Menu] = None
        self.edit_menu: Optional[tk.Menu] = None
        self.run_menu: Optional[tk.Menu] = None
        self.help_menu: Optional[tk.Menu] = None

        self._tiled_map: Optional[TiledMap] = None

        self._current_element: Optional[TiledElement] = None
        self._current_object: Optional[TiledElement] = None
        self._current_tileset: Optional[TiledTileset] = None
        self._current_layer: Optional[BaseTiledLayer] = None

        # Initialisation of other components

        # tk.Tk() and pygame.init() must be done in this order and before anything else (in tkinter world)
        self.root = tk.Tk()
        self.root.title("Editor")

        pygame.init()
        self.previous_keys = pygame.key.get_pressed()
        self.current_keys = pygame.key.get_pressed()

        self.clock = pygame.time.Clock()

        self.open_tk_window(self.root)
        if WITH_PYGAME:
            self.setup_pygame()

        # self.font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "editor", "raleway-medium-webfont.ttf"), 17)
        self.font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "editor", "test_fixed.otf"), 17)

        self.viewport = Rect(0, 0, 1150, 900)
        right_column = self.viewport.width - 300

        image_size = 32
        margin = 3

        self.map_action_panel = MapActionsPanel(Rect(right_column, 0, 300, 50), margin=margin)

        self.tileset_canvas = TilesetCanvas(
            Rect(right_column, image_size + margin * 2, 300, 500), None,
            self._tile_selected_callback
        )
        self.map_canvas = MapCanvas(
            Rect(0, 0, right_column, self.viewport.height),
            self.font,
            self.map_action_panel,
            self.tileset_canvas,
            self._object_added_callback,
            self._object_selected_callback,
            self._selection_changed_callback
        )

        self.map_action_panel.visible = False
        self.map_action_panel.action = MapAction.BRUSH_TILE

        self.components = ComponentCollection(
            self.viewport,
            self.map_canvas, self.map_action_panel, self.tileset_canvas)

        self.key_modifier = 0
        self.mouse_x = 0
        self.mouse_y = 0

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        control_modifier = "Command" if self.macos else "Control"

        root.geometry("300x900+10+30")
        root.protocol("WM_DELETE_WINDOW", self._quit_action)
        root.title("Edit object")

        menubar = tk.Menu(root)
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New", command=self._create_new_map_action, accelerator=f"{control_modifier}+N")
        self.file_menu.add_command(label="Open", command=self._load_file_action)
        self.file_menu.add_command(label="Save", command=self._save_map_action, state="disabled", accelerator=f"{control_modifier}+S")
        self.file_menu.add_command(label="Save as...", command=self._save_as_map_action, state="disabled", accelerator=f"Shift+{control_modifier}+X")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self._quit_action, accelerator=f"{control_modifier}+Q")
        menubar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0)
        self.edit_menu.add_command(label="Redo", command=self._do_nothing_action, state="disabled")
        self.edit_menu.add_command(label="Undo", command=self._do_nothing_action, state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self._cut_action, state="disabled", accelerator=f"{control_modifier}+X")
        self.edit_menu.add_command(label="Copy", command=self._copy_action, state="disabled", accelerator=f"{control_modifier}+C")
        self.edit_menu.add_command(label="Paste", command=self._paste_action, state="disabled", accelerator=f"{control_modifier}+V")
        self.edit_menu.add_command(label="Delete", command=self._delete_action, state="disabled", accelerator="Delete")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Select All", command=self._select_all_action, state="disabled", accelerator=f"{control_modifier}+A")
        self.edit_menu.add_command(label="Select None", command=self._select_none_action, state="disabled", accelerator=f"Shift+{control_modifier}+A")

        menubar.add_cascade(label="Edit", menu=self.edit_menu)

        self.run_menu = tk.Menu(menubar, tearoff=0)
        self.run_menu.add_command(label="Run", command=self._run_map_action, state="disabled", accelerator="{control_modifier}+R")

        menubar.add_cascade(label="Run", menu=self.run_menu)

        self.help_menu = tk.Menu(menubar, tearoff=0)
        self.help_menu.add_command(label="Help Index", command=self._do_nothing_action, state="disabled")
        self.help_menu.add_command(label="About...", command=self._do_nothing_action, state="disabled")
        menubar.add_cascade(label="Help", menu=self.help_menu)
        root.config(menu=menubar)

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

        left_frame = tk.Frame(root)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)
        right_frame = left_frame
        # pack(tk.Label(text="|"), side=LEFT, fill=Y)
        # right_frame = tk.Frame(root)
        # right_frame.pack(side=LEFT, fill=BOTH, expand=True)

        pack(tk.Label(right_frame, text="Hierarchy"), fill=X)
        self.hierarchy_view = Hierarchy(right_frame, self._set_selected_element)
        self.hierarchy_view.pack(side=TOP, fill=X, expand=True)

        pack(tk.Label(left_frame, text="Properties"), fill=X)

        self.main_properties = Properties(left_frame, self.update_current_element_attribute)

        pack(tk.Label(left_frame, text=""), fill=X)
        pack(tk.Label(left_frame, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(left_frame, self.update_current_element_property)

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
        import platform
        if platform.system() == "Darwin":
            self.macos = True
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,58"
        else:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,30"

        self.screen = pygame.display.set_mode((1150, 900))
        self.screen_rect = self.screen.get_rect()
        pygame.display.set_caption("Editor")
        # self.clock = pygame.time.Clock()

        pygame.display.set_caption("Editor Window")

    @property
    def tiled_map(self) -> Optional[TiledMap]:
        return self._tiled_map

    @tiled_map.setter
    def tiled_map(self, tiled_map: Optional[TiledMap]) -> None:
        self._tiled_map = tiled_map
        if tiled_map is not None:
            self.file_menu.entryconfig("Save", state="normal", command=self._save_map_action)
            self.file_menu.entryconfig("Save as...", state="normal", command=self._save_as_map_action)
            self.current_tileset = tiled_map.tilesets[0] if len(tiled_map.tilesets) > 0 else None

            # main_layer = next((l for l in tiled_map.layers if l.name == "main"), None)
            #
            # self.current_layer = main_layer
            self.current_object = None
            self.map_action_panel.visible = True
            self.map_canvas.tiled_map = tiled_map
            self.hierarchy_view.set_map(tiled_map)

            if self.current_tileset is not None:
                self.tileset_canvas.select_tile(self.tileset_canvas.tileset.firstgid)
        else:
            self.file_menu.entryconfig("Save", state="disabled")
            self.file_menu.entryconfig("Save as...", state="disabled")
            self.current_tileset = None
            self.current_element = None
            self.current_layer = None
            self.current_object = None

            self.map_canvas.tiled_map = None
            self.tileset_canvas.select_tile(None)

    @property
    def current_element(self) -> Optional[TiledElement]:
        return self._current_element

    @current_element.setter
    def current_element(self, current_element: Optional[TiledElement]) -> None:
        self._current_element = current_element

        self.add_property.configure(state="normal" if current_element is not None else "disabled")

        if isinstance(current_element, BaseTiledLayer):
            self.current_layer = cast(BaseTiledLayer, current_element)
            self.edit_menu.entryconfig("Delete", state="disabled")
        elif isinstance(current_element, TiledTileset):
            self.current_tileset = cast(TiledTileset, current_element)
            self.edit_menu.entryconfig("Delete", state="disabled")
        elif isinstance(current_element, TiledObject):
            self.current_object = cast(TiledObject, current_element)
        else:
            self.edit_menu.entryconfig("Delete", state="disabled")

    @property
    def current_tileset(self) -> Optional[TiledTileset]:
        return self._current_tileset

    @current_tileset.setter
    def current_tileset(self, tileset: Optional[TiledTileset]) -> None:
        self._current_tileset = tileset
        self.tileset_canvas.tileset = tileset
        if tileset is not None:
            print(f"Current tileset is {tileset.name}: {tileset.image}")
        else:
            print("No current tileset")

    @property
    def current_layer(self) -> Optional[BaseTiledLayer]:
        return self._current_layer

    @current_layer.setter
    def current_layer(self, tile_layer: Optional[BaseTiledLayer]) -> None:
        self._current_layer = tile_layer
        self.map_canvas.selected_layer = tile_layer

    @property
    def current_object(self) -> Optional[TiledObject]:
        return self._current_object

    @current_object.setter
    def current_object(self, obj: Optional[TiledObject]) -> None:
        self._current_object = obj
        if obj is not None:
            self.edit_menu.entryconfig("Delete", state="normal")
            self.map_canvas.select_object(obj)

    def _object_added_callback(self, layer: TiledObjectGroup, obj: TiledObject) -> None:
        self.hierarchy_view.add_object(layer, obj)
        self.hierarchy_view.selected_object = obj

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
        self.map_canvas.tile_selection_changed()

    def _quit_action(self, _event=None) -> None:
        self.running = False
        if WITH_PYGAME:
            pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    def _load_file_action(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        self.load_file(filename)

    def _save_map_action(self, _event=None) -> None:
        if self.tiled_map.filename is None:
            self._save_as_map_action()
        else:
            self.tiled_map.save(self.tiled_map.filename)

    def _save_as_map_action(self, _event=None) -> None:
        filename = filedialog.asksaveasfilename(title="Save map", filetypes=(("Map file", "*.tmx"),))
        self.tiled_map.filename = filename
        self._save_map_action()

    def _cut_action(self, _event=None) -> None:
        print(f"CUT for {self.current_element}")

    def _copy_action(self, _event=None) -> None:
        print(f"COPY for {self.current_element}")

    def _paste_action(self, _event=None) -> None:
        print(f"PASTE for {self.current_element}")

    def _select_all_action(self, _event=None) -> None:
        self.map_canvas.select_all()

    def _select_none_action(self, _event=None) -> None:
        self.map_canvas.select_none()

    def _create_new_map_action(self, _event=None) -> None:
        tiled_map = TiledMap()
        tiled_map.tilewidth = 16
        tiled_map.tileheight = 16
        tiled_map.width = 64
        tiled_map.height = 64
        foreground_layer = TiledTileLayer(tiled_map)
        foreground_layer.id = 1
        foreground_layer.name = "foreground"
        objects_layer = TiledObjectGroup(tiled_map)
        objects_layer.id = 2
        objects_layer.name = "objects"
        main_layer = TiledTileLayer(tiled_map)
        main_layer.id = 3
        main_layer.name = "main"
        background_layer = TiledTileLayer(tiled_map)
        background_layer.id = 4
        background_layer.name = "background"

        tiled_map.add_layer(foreground_layer)
        tiled_map.add_layer(objects_layer)
        tiled_map.add_layer(main_layer)
        tiled_map.add_layer(background_layer)

        self.tiled_map = tiled_map

    def _run_map_action(self, _event=None) -> None:
        self.run_map()

    def _delete_action(self, _event=None) -> None:
        if isinstance(self.current_element, TiledObject):
            obj = cast(TiledObject, self.current_element)
            layer = cast(TiledObjectGroup, obj.parent)
            del layer.objects_id_map[obj.id]
            self.hierarchy_view.delete_object(obj)
            self.map_canvas.deselect_object()
        elif isinstance(self.current_element, TiledTileLayer):
            print(f"Selected delete action")
            self.map_canvas.delete_tiles()
        else:
            print(f"No layer selected")

    @staticmethod
    def _do_nothing_action(_event=None) -> None:
        print("Do nothing!")

    def load_file(self, filename: str) -> None:
        tiled_map = TiledMap()
        tiled_map.load(filename)
        self.tiled_map = tiled_map
        map_name = self.tiled_map.name
        if map_name is not None:
            self.run_menu.entryconfig(1, label=f"Run '{map_name}'", state="normal")
        else:
            self.run_menu.entryconfig(1, label=f"Run", state="normal")

    def run_map(self) -> None:
        if "code" in self.tiled_map.properties:
            python_file = self.tiled_map.properties["code"]
            map_file = self.tiled_map.filename if self.tiled_map.filename is not None else os.getcwd()
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
                    self.components.mouse_down(self.mouse_x, self.mouse_y, self.key_modifier)
                    self.root.update()
                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_down_counter = 0
                    self.components.mouse_up(self.mouse_x, self.mouse_y, self.key_modifier)
                    self.root.update()
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_x = event.pos[0]
                    self.mouse_y = event.pos[1]
                    self.components.mouse_move(self.mouse_x, self.mouse_y, self.key_modifier)
                    mouse_down_counter = MOUSE_DOWN_COUNTER
                    self.root.update()
                elif event.type == pygame.WINDOWLEAVE:
                    self.components.mouse_out(0, 0)
                    self.root.update()
                elif event.type == pygame.MOUSEWHEEL:
                    self.components.mouse_wheel(self.mouse_x, self.mouse_y, event.x, event.y, self.key_modifier)
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
                                self._save_map_action()
                            else:
                                self._save_as_map_action()

                    if dx != 0 or dy != 0:
                        self.components.mouse_wheel(self.mouse_x, self.mouse_y, dx, dy, self.key_modifier)

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
                    print(f"Active Event")
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
                    self.components.mouse_move(self.mouse_x, self.mouse_y, self.key_modifier)

            self.previous_keys = self.current_keys
            self.current_keys = pygame.key.get_pressed()
            # if self.previous_keys != self.current_keys:
            #     print(f"keys={self.current_keys}")

            self.screen.fill((200, 200, 200))
            self.components.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(30)
            if not has_focus:
                self.root.update()

    def update_current_element_attribute(self, key: str, value: str) -> None:
        if self._current_element is not None:

            attrs = type(self._current_element).ATTRIBUTES
            typ = attrs[key].type if key in attrs else type(getattr(self._current_element, key))

            if typ is None:
                setattr(self._current_element, key, value)
            elif typ is bool:
                setattr(self._current_element, key, bool(value))
            elif typ is int:
                setattr(self._current_element, key, int(value))
            elif typ is float:
                setattr(self._current_element, key, float(value))
            elif typ is Color:
                if value == "":
                    setattr(self._current_element, key, None)
                elif len(value) >= 7 and value[0] == "(" and value[-1] == ")":
                    s = [f"{int(s.strip()):02x}" for s in value[1:-1].split(",")]
                    if len(s) == 3:
                        setattr(self._current_element, key, "#" + "".join(s))
                        return
                print(f"Got incorrect color value '{value}'")
            else:
                setattr(self._current_element, key, value)

            if key == "name":
                if isinstance(self._current_element, TiledObject):
                    self.hierarchy_view.update_object_name(cast(TiledObject, self._current_element))
                elif isinstance(self._current_element, BaseTiledLayer):
                    self.hierarchy_view.update_layer_name(cast(BaseTiledLayer, self._current_element))

    def update_current_element_property(self, key: str, value: str) -> None:
        if self._current_element is not None:
            current_value = self._current_element.properties[key]
            if current_value is None:
                self._current_element.properties[key] = value
            elif isinstance(current_value, bool):
                self._current_element.properties[key] = bool(value)
            elif isinstance(current_value, int):
                self._current_element.properties[key] = int(value)
            elif isinstance(current_value, float):
                self._current_element.properties[key] = float(value)
            else:
                self._current_element.properties[key] = value


if __name__ == '__main__':
    editor = Editor()

    if len(sys.argv) > 1:
        editor.load_file(sys.argv[1])
    else:
        print("No arguments given")

    if WITH_PYGAME:
        editor.pygame_loop()
    else:
        editor.root.mainloop()
