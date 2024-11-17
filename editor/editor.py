import os

import pygame
import tkinter as tk

from tkinter import colorchooser, X, filedialog

from typing import Optional
from sys import exit

from pygame import Surface, Rect

from properties import Properties
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
        root.geometry("320x800+10+10")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.title("Edit object")

        # menu_frame = tk.Frame(root)
        # menu_frame.pack(fill=X)
        #
        # menu = tk.Menubutton(menu_frame, text="Menu")
        # menu.menu = tk.Menu(menu, tearoff=0)
        # menu["menu"] = menu.menu
        # menu.menu.add_command(label="Load", command=self.on_load)
        # menu.menu.add_command(label="Save", command=self.on_save)
        # menu.pack(side=LEFT)

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

        pack(tk.Label(root, text="Properties"), fill=X)

        self.main_properties = Properties(root)
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

        pack(tk.Label(root, text=""), fill=X)
        pack(tk.Label(root, text="Custom Properties"), fill=X)

        self.custom_properties = Properties(root)
        values = {
            "on_click": "do_nothing()",
            "on_animation": "a = a + 1",
            "on_entry": "say_once(\"Hey\")\n# second line \nb = b + 1\n",
            "on_leave": "say(\"Buy\")",
            # **{f"custom_{k}": k for k in range(20)}
        }
        for k, v in values.items():
            self.custom_properties.insert('', tk.END, text=k, values=(v, ))

        pack(tk.Button(root, text="Select Colour", command=self.select_colour), fill=X)

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
        os.environ['SDL_VIDEO_WINDOW_POS'] = "320,10"

        self.screen = pygame.display.set_mode((800, 800))
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
