import os

import pygame
import tkinter as tk

from tkinter import colorchooser, X, filedialog, LEFT, BOTH, TOP

from typing import Optional, cast
from sys import exit

from pygame import Surface, Rect

from editor.hierarchy import Hierarchy
from editor.properties import Properties
from engine.tmx import TiledMap, TiledElement, TiledTileset, BaseTiledLayer, TiledObject

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
        self.current_map: Optional[TiledMap] = None
        self._current_element: Optional[TiledElement] = None
        self._current_object: Optional[TiledElement] = None
        self._current_tileset: Optional[TiledTileset] = None
        self._current_layer: Optional[BaseTiledLayer] = None

        self.tiled_map: Optional[TiledMap] = None

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
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.do_nothing)
        filemenu.add_command(label="Open", command=self.load_file)
        filemenu.add_command(label="Save", command=self.do_nothing)
        filemenu.add_command(label="Save as...", command=self.do_nothing)
        filemenu.add_command(label="Close", command=self.do_nothing)

        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo", command=self.do_nothing)
        editmenu.add_separator()
        editmenu.add_command(label="Cut", command=self.do_nothing)
        editmenu.add_command(label="Copy", command=self.do_nothing)
        editmenu.add_command(label="Paste", command=self.do_nothing)
        editmenu.add_command(label="Delete", command=self.do_nothing)
        editmenu.add_command(label="Select All", command=self.do_nothing)

        menubar.add_cascade(label="Edit", menu=editmenu)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.do_nothing)
        helpmenu.add_command(label="About...", command=self.do_nothing)
        menubar.add_cascade(label="Help", menu=helpmenu)
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

        self.main_properties = Properties(left_frame)

        pack(tk.Label(left_frame, text=""), fill=X)
        pack(tk.Label(left_frame, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(left_frame)

        self.hierarchy_view.init_properties_widgets(self.main_properties, self.custom_properties)

        pack(tk.Button(left_frame, text="Select Colour", command=self.select_colour), fill=X)

        return root

    def load_file(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        print(f"Selected {filename}")

        self.tiled_map = TiledMap()
        self.tiled_map.load(filename)

        self.hierarchy_view.set_map(self.tiled_map)

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


editor = Editor()
if WITH_PYGAME:
    editor.pygame_loop()
else:
    editor.root.mainloop()
