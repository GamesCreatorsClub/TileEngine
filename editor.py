import os

import pygame
import tkinter as tk

from tkinter import colorchooser, X, filedialog, LEFT, Y, ttk, VERTICAL, BOTH, TOP, RIGHT

from typing import Optional
from sys import exit

from pygame import Surface, Rect

from editor.hierarchy import Hierarchy
from editor.properties import Properties
from engine.tmx import TiledMap, TiledElement

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
        self._current_object: Optional[TiledElement] = None
        self.main_properties: Optional[Properties] = None
        self.custom_properties: Optional[Properties] = None

    @property
    def current_object(self) -> Optional[TiledElement]:
        return self._current_object

    @current_object.setter
    def current_object(self, current_object: Optional[TiledElement]) -> None:
        self._current_object = current_object

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
        filemenu.add_command(label="New", command=self.donothing)
        filemenu.add_command(label="Open", command=self.load_file)
        filemenu.add_command(label="Save", command=self.donothing)
        filemenu.add_command(label="Save as...", command=self.donothing)
        filemenu.add_command(label="Close", command=self.donothing)

        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo", command=self.donothing)
        editmenu.add_separator()
        editmenu.add_command(label="Cut", command=self.donothing)
        editmenu.add_command(label="Copy", command=self.donothing)
        editmenu.add_command(label="Paste", command=self.donothing)
        editmenu.add_command(label="Delete", command=self.donothing)
        editmenu.add_command(label="Select All", command=self.donothing)

        menubar.add_cascade(label="Edit", menu=editmenu)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.donothing)
        helpmenu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=helpmenu)
        root.config(menu=menubar)

        left_frame = tk.Frame(root)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)
        right_frame = left_frame
        # pack(tk.Label(text="|"), side=LEFT, fill=Y)
        # right_frame = tk.Frame(root)
        # right_frame.pack(side=LEFT, fill=BOTH, expand=True)

        pack(tk.Label(right_frame, text="Hierarchy"), fill=X)
        hierarchy_view = Hierarchy(right_frame)
        hierarchy_view.pack(side=TOP, fill=X, expand=True)

        hierarchy_view.insert('', tk.END, iid=0, text="map", open=True)
        hierarchy_view.insert('', tk.END, iid=1, text="tilesets", open=True)
        hierarchy_view.insert('', tk.END, iid=2, text="layers", open=True)
        hierarchy_view.insert('', tk.END, iid=3, text="foreground", open=True)
        hierarchy_view.insert('', tk.END, iid=4, text="objects", open=True)
        hierarchy_view.insert('', tk.END, iid=5, text="main", open=True)
        hierarchy_view.insert('', tk.END, iid=6, text="background", open=True)
        hierarchy_view.move(1, 0, 0)
        hierarchy_view.move(2, 0, 1)
        hierarchy_view.move(3, 2, 0)
        hierarchy_view.move(4, 2, 1)
        hierarchy_view.move(5, 2, 3)
        hierarchy_view.move(6, 2, 4)

        hierarchy_view.insert('', tk.END, iid=7, text="player", open=False)
        hierarchy_view.insert('', tk.END, iid=8, text="door1", open=False)
        hierarchy_view.insert('', tk.END, iid=9, text="door2", open=False)
        hierarchy_view.insert('', tk.END, iid=10, text="teleport", open=False)
        hierarchy_view.move(7, 4, 0)
        hierarchy_view.move(8, 4, 1)
        hierarchy_view.move(9, 4, 2)
        hierarchy_view.move(10, 4, 3)


        pack(tk.Label(left_frame, text="Properties"), fill=X)

        self.main_properties = Properties(left_frame)
        # self.main_properties.pack(fill=X, expand=True)
        # values = {
        #     "First": 1,
        #     "Second": "some value",
        #     "Third": True,
        #     "fourth": 42,
        #     "fifth": "something",
        #     "sixth": "line1\nline2\nline3",
        #     **{k: k for k in range(20)}
        # }
        # for k, v in values.items():
        #     main_properties.insert('', tk.END, text=k, values=(v, ))

        pack(tk.Label(left_frame, text=""), fill=X)
        pack(tk.Label(left_frame, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(left_frame)
        # self.custom_properties.pack(fill=X, expand=True)
        values = {
            "on_click": "do_nothing()",
            "on_animation": "a = a + 1",
            "on_entry": "say_once(\"Hey\")\n# second line \nb = b + 1\n",
            "on_leave": "say(\"Buy\")",
            # **{f"custom_{k}": k for k in range(20)}
        }
        for k, v in values.items():
            self.custom_properties.insert('', tk.END, text=k, values=(v, ))

        pack(tk.Button(left_frame, text="Select Colour", command=self.select_colour), fill=X)

        # def open_edit() -> None:
        #     text_edit = EditText(root, properties_widget=self.custom_properties)
        #
        # pack(tk.Button(root, text="Edit text", command=open_edit), fill=X)

        return root

    def load_file(self) -> None:
        filename = filedialog.askopenfilename(title="Open file", filetypes=(("Map file", "*.tmx"), ("Tileset file", "*.tsx")))
        print(f"Selected {filename}")

    def donothing(self) -> None:
        print("Do nothigng!")

    def on_load(self) -> None:
        print("Called on load")

    def on_save(self) -> None:
        print("Called on load")

    def setup_pygame(self) -> None:
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
