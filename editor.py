import os
import subprocess
import sys

import pygame
import tkinter as tk
from tkinter import messagebox

from tkinter import X, filedialog, LEFT, BOTH, TOP

from typing import Optional, cast
from sys import exit

from pygame import Surface, Rect, Color

from editor.hierarchy import Hierarchy
from editor.properties import Properties
from editor.pygame_components import ComponentCollection, TilesetCanvas, MapCanvas
from engine.tmx import TiledMap, TiledElement, TiledTileset, BaseTiledLayer, TiledObject, TiledTileLayer, TiledGroupLayer

WITH_PYGAME = True
WITH_SCROLLBAR = True


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class Editor:
    def __init__(self) -> None:
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
        # self.popup: Optional[tk.Tk] = None
        pygame.init()
        self.previous_keys = pygame.key.get_pressed()
        self.current_keys = pygame.key.get_pressed()

        self.clock = pygame.time.Clock()

        self.open_tk_window(self.root)
        if WITH_PYGAME:
            self.setup_pygame()

        self.font = pygame.font.SysFont("apple casual", 24)

        self.viewport = Rect(0, 0, 1150, 900)
        self.map_canvas = MapCanvas(
            Rect(0, 0, self.viewport.width - 300, self.viewport.height), None
        )
        self.tileset_canvas = TilesetCanvas(
            Rect(self.viewport.width - 300, 50, 300, 500), None
        )
        self.components = ComponentCollection(self.viewport, self.map_canvas, self.tileset_canvas)

        self.key_modifier = 0
        self.mouse_x = 0
        self.mouse_y = 0

    @property
    def tiled_map(self) -> Optional[TiledMap]:
        return self._tiled_map

    @tiled_map.setter
    def tiled_map(self, tiled_map: Optional[TiledMap]) -> None:
        self._tiled_map = tiled_map
        if tiled_map is not None:
            self.file_menu.entryconfig("Save", state="normal", command=self.save_map)
            self.file_menu.entryconfig("Save as...", state="normal", command=self.save_as_map)
            self.current_tileset = tiled_map.tilesets[0] if len(tiled_map.tilesets) > 0 else None
            # self.current_element = tiled_map

            main_layer = next((l for l in tiled_map.layers if l.name == "main"), None)

            self.current_layer = main_layer
            self.current_object = None
        else:
            self.file_menu.entryconfig("Save", state="disabled")
            self.file_menu.entryconfig("Save as...", state="disabled")
            self.current_tileset = None
            self.current_element = None
            self.current_layer = None
            self.current_object = None

        self.hierarchy_view.set_map(tiled_map)
        self.map_canvas.tiled_map = tiled_map

    @property
    def current_element(self) -> Optional[TiledElement]:
        return self._current_element

    @current_element.setter
    def current_element(self, current_element: Optional[TiledElement]) -> None:
        self._current_element = current_element

        self.add_property.configure(state="normal" if current_element is not None else "disabled")

        if isinstance(current_element, BaseTiledLayer):
            self.current_layer = cast(BaseTiledLayer, current_element)
        elif isinstance(current_element, TiledTileset):
            self.current_tileset = cast(TiledTileset, current_element)
        elif isinstance(current_element, TiledObject):
            self.current_object = cast(TiledObject, current_element)

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
    def current_layer(self, tileset: Optional[BaseTiledLayer]) -> None:
        self._current_layer = tileset
        if tileset is not None:
            print(f"Current layer is {tileset.name}: {tileset.id}")
        else:
            print("No current layer")

    @property
    def current_object(self) -> Optional[TiledObject]:
        return self._current_object

    @current_object.setter
    def current_object(self, obj: Optional[TiledObject]) -> None:
        self._current_object = obj
        if obj is not None:
            print(f"Current object is {obj.name}: {obj.id}")
        else:
            print("No current object")

    def _set_selected_element(self, selected_element: Optional[TiledElement]) -> None:
        self.current_element = selected_element

    def quit(self) -> None:
        self.running = False
        if WITH_PYGAME:
            pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    def save_map(self) -> None:
        if self.tiled_map.filename is None:
            self.save_as_map()
        else:
            self.tiled_map.save(self.tiled_map.filename)

    def save_as_map(self) -> None:
        filename = filedialog.asksaveasfilename(title="Save map", filetypes=(("Map file", "*.tmx"),))
        self.tiled_map.filename = filename
        self.save_map()

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        root.geometry("300x900+10+30")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.title("Edit object")

        menubar = tk.Menu(root)
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New", command=self.create_new_map)
        self.file_menu.add_command(label="Open", command=self.browse_to_load_file)
        self.file_menu.add_command(label="Save", command=self.do_nothing, state="disabled")
        self.file_menu.add_command(label="Save as...", command=self.do_nothing, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0)
        self.edit_menu.add_command(label="Redo", command=self.do_nothing, state="disabled")
        self.edit_menu.add_command(label="Undo", command=self.do_nothing, state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self.do_nothing, state="disabled")
        self.edit_menu.add_command(label="Copy", command=self.do_nothing, state="disabled")
        self.edit_menu.add_command(label="Paste", command=self.do_nothing, state="disabled")
        self.edit_menu.add_command(label="Delete", command=self.do_nothing, state="disabled")
        self.edit_menu.add_command(label="Select All", command=self.do_nothing, state="disabled")

        menubar.add_cascade(label="Edit", menu=self.edit_menu)

        self.run_menu = tk.Menu(menubar, tearoff=0)
        self.run_menu.add_command(label="Run", command=self.run_map, state="disabled")

        menubar.add_cascade(label="Run", menu=self.run_menu)

        self.help_menu = tk.Menu(menubar, tearoff=0)
        self.help_menu.add_command(label="Help Index", command=self.do_nothing, state="disabled")
        self.help_menu.add_command(label="About...", command=self.do_nothing, state="disabled")
        menubar.add_cascade(label="Help", menu=self.help_menu)
        root.config(menu=menubar)

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
            command=lambda : self.custom_properties.start_editing(self.custom_properties.selected_rowid)
        )

        self.add_property.grid(row=0, column=0, pady=3, padx=3, sticky=tk.W)
        self.remove_property.grid(row=0, column=1, pady=3, padx=3, sticky=tk.W)
        self.edit_property.grid(row=0, column=2, pady=3, padx=3, sticky=tk.W)

        pack(self.button_panel, fill=X)

        self.hierarchy_view.init_properties_widgets(self.main_properties, self.custom_properties)
        self.custom_properties.update_buttons(self.add_property, self.remove_property, self.edit_property)

        return root

    def browse_to_load_file(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        self.load_file(filename)

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

    def create_new_map(self) -> None:
        tiled_map = TiledMap()
        foreground_layer = TiledTileLayer(self.tiled_map)
        foreground_layer.id = 1
        foreground_layer.name = "foreground"
        objects_layer = TiledGroupLayer(self.tiled_map)
        objects_layer.id = 2
        objects_layer.name = "objects"
        main_layer = TiledTileLayer(self.tiled_map)
        main_layer.id = 3
        main_layer.name = "main"
        background_layer = TiledTileLayer(self.tiled_map)
        background_layer.id = 4
        background_layer.name = "background"

        tiled_map.add_layer(foreground_layer)
        tiled_map.add_layer(objects_layer)
        tiled_map.add_layer(main_layer)
        tiled_map.add_layer(background_layer)

        self.tiled_map = tiled_map

    @staticmethod
    def do_nothing() -> None:
        print("Do nothing!")

    def setup_pygame(self) -> None:
        import platform
        if platform.system() == "Darwin":
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,58"
        else:
            os.environ['SDL_VIDEO_WINDOW_POS'] = "315,30"

        self.screen = pygame.display.set_mode((1150, 900))
        self.screen_rect = self.screen.get_rect()
        pygame.display.set_caption("Editor")
        # self.clock = pygame.time.Clock()

        pygame.display.set_caption("Editor Window")

    def pygame_loop(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.components.mouse_down(self.mouse_x, self.mouse_y, self.key_modifier)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.components.mouse_up(self.mouse_x, self.mouse_y, self.key_modifier)
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_x = event.pos[0]
                    self.mouse_y = event.pos[1]
                    self.components.mouse_move(self.mouse_x, self.mouse_y, self.key_modifier)
                elif event.type == pygame.WINDOWLEAVE:
                    self.components.mouse_out(0, 0)
                elif event.type == pygame.MOUSEWHEEL:
                    self.components.mouse_wheel(self.mouse_x, self.mouse_y, event.x, event.y, self.key_modifier)
                elif event.type == pygame.KEYDOWN:
                    dx = 0
                    dy = 0
                    if event.key == pygame.K_RIGHT:
                        dx = 1
                    elif event.key == pygame.K_LEFT:
                        dx = -1
                    elif event.key == pygame.K_UP:
                        dy = 1
                    elif event.key == pygame.K_DOWN:
                        dy = -1
                    if dx != 0 or dy != 0:
                        self.components.mouse_wheel(self.mouse_x, self.mouse_y, event.x, event.y, self.key_modifier)
                # elif event.type == pygame.KEYUP:
                #     pass
                # else:
                #     print(f"event.type == {event.type}")

            self.previous_keys = self.current_keys
            self.current_keys = pygame.key.get_pressed()

            self.screen.fill((200, 200, 200))
            self.components.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(30)
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
