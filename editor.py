import os

import pygame
import tkinter as tk

from tkinter import colorchooser, X, filedialog, LEFT, BOTH, TOP

from typing import Optional, cast, get_type_hints
from sys import exit

from pygame import Surface, Rect, Color

from editor.hierarchy import Hierarchy
from editor.properties import Properties
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
        self.screen = None
        self.screen_rect: Optional[Rect] = None
        self.main_properties: Optional[Properties] = None
        self.custom_properties: Optional[Properties] = None
        self.hierarchy_view: Optional[Hierarchy] = None

        self._selected_object: Optional[TiledElement] = None

        self.file_menu: Optional[tk.Menu] = None
        self.edit_menu: Optional[tk.Menu] = None
        self.help_menu: Optional[tk.Menu] = None

        self._tiled_map: Optional[TiledMap] = None

        self._current_element: Optional[TiledElement] = None
        self._current_object: Optional[TiledElement] = None
        self._current_tileset: Optional[TiledTileset] = None
        self._current_layer: Optional[BaseTiledLayer] = None

        # Initialisation of other components

        # tk.Tk() and pygame.init() must be done in this order and before anything else (in tkinter world)
        self.root = tk.Tk()
        # self.popup: Optional[tk.Tk] = None
        pygame.init()

        self.clock = pygame.time.Clock()

        self.open_tk_window(self.root)
        if WITH_PYGAME:
            self.setup_pygame()
            self.background = Surface(self.screen_rect.size, pygame.HWSURFACE).convert_alpha()
        self.draw = False
        self.draw_size = (50, 50)

    @property
    def tiled_map(self) -> Optional[TiledMap]:
        return self._tiled_map

    @tiled_map.setter
    def tiled_map(self, tiled_map: Optional[TiledMap]) -> None:
        self._tiled_map = tiled_map
        if tiled_map is not None:
            self.file_menu.entryconfig("Save", state="normal")
            self.file_menu.entryconfig("Save as...", state="normal")
        else:
            self.file_menu.entryconfig("Save", state="disabled")
            self.file_menu.entryconfig("Save as...", state="disabled")

        self.hierarchy_view.set_map(self.tiled_map)

    @property
    def current_element(self) -> Optional[TiledElement]:
        return self._current_element

    @current_element.setter
    def current_element(self, current_element: Optional[TiledElement]) -> None:
        self._current_element = current_element
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
        print(f"Current tileset is {tileset.name}: {tileset.image}")

    @property
    def current_layer(self) -> Optional[BaseTiledLayer]:
        return self._current_layer

    @current_layer.setter
    def current_layer(self, tileset: Optional[BaseTiledLayer]) -> None:
        self._current_tileset = tileset
        print(f"Current layer is {tileset.name}: {tileset.id}")

    @property
    def current_object(self) -> Optional[TiledObject]:
        return self._current_object

    @current_object.setter
    def current_object(self, obj: Optional[TiledObject]) -> None:
        self._current_object = obj
        print(f"Current object is {obj.name}: {obj.id}")

    def _set_selected_element(self, selected_element: Optional[TiledElement]) -> None:
        self.current_element = selected_element

    def quit(self) -> None:
        self.running = False
        if WITH_PYGAME:
            pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        root.geometry("300x900+10+30")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.title("Edit object")

        menubar = tk.Menu(root)
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New", command=self.create_new_map)
        self.file_menu.add_command(label="Open", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.do_nothing, state="disabled")
        self.file_menu.add_command(label="Save as...", command=self.do_nothing, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)
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

        self.hierarchy_view.init_properties_widgets(self.main_properties, self.custom_properties)

        pack(tk.Button(left_frame, text="Select Colour", command=self.select_colour), fill=X)

        return root

    def load_file(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))

        tiled_map = TiledMap()
        tiled_map.load(filename)
        self.tiled_map = tiled_map

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
        # self.clock = pygame.time.Clock()

        pygame.display.set_caption("Editor Window")

    def select_colour(self) -> None:
        color = colorchooser.askcolor()
        print(color)
        if color[0] is not None:
            self.colour = color[0]

    def pygame_loop(self) -> None:
        mouse_pos = (0, 0)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.draw = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.draw = False
                elif event.type == pygame.MOUSEMOTION:
                    mouse_pos = event.pos[0] - self.draw_size[0] // 2, event.pos[1] - self.draw_size[1] // 2
                    if self.draw:
                        pygame.draw.rect(self.background, self.colour, (mouse_pos, self.draw_size))

            self.screen.fill((0, 0, 0))
            self.screen.blit(self.background, (0, 0))

            pygame.draw.rect(self.screen, self.colour, (mouse_pos, self.draw_size))
            pygame.display.flip()
            self.clock.tick(30)
            self.root.update()
            # if self.popup is not None:
            #     self.popup.update()

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


editor = Editor()
if WITH_PYGAME:
    editor.pygame_loop()
else:
    editor.root.mainloop()
