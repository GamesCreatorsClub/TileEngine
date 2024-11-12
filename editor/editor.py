import os
from typing import Optional

import pygame
import tkinter as tk

from tkinter import colorchooser, ttk, RIGHT, Y, X
from sys import exit

from pygame import Surface, Rect


WITH_PYGAME = True
WITH_SCROLLBAR = True


class EntryPopup(tk.Entry):

    def __init__(self, root: tk.Tk, treeview: ttk.Treeview, iid, text, **kw):
        super().__init__(treeview, **kw)
        self.destroyed = False
        self.window = root
        self.treeview = treeview
        self.iid = iid

        self.insert(0, text)
        self['exportselection'] = False

        self.focus_force()
        self.bind("<Return>", self.update_value)
        self.bind("<Control-a>", self.select_all)

        self.bind("<Escape>", self.abandon_edit)
        self.bind("<FocusOut>", self.update_value)

        self.window.bind("<FocusOut>", self.update_value)

    def abandon_edit(self, _event):
        if not self.destroyed:
            self.destroyed = True
            self.destroy()

    def update_value(self, _event):
        if not self.destroyed:
            new_value = self.get()
            self.treeview.item(self.iid, values=(new_value,))
            self.destroyed = True
            self.destroy()

    def select_all(self, _event):
        if not self.destroyed:
            self.selection_range(0, tk.END)
            return "break"


class PropertiesWidget(ttk.Treeview):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.treeview_frame = tk.Frame(root)
        super().__init__(self.treeview_frame, columns=("value",))

        self.scrollbar = tk.Scrollbar(self.treeview_frame,
                                      orient="vertical",
                                      command=self.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.configure(yscrollcommand=self.scrollbar.set)

        self.heading("#0", text="Property")
        self.heading("value", text="Value")
        self.column("#0", minwidth=50, width=150)
        self.column("value", minwidth=50, width=150)

        self.bind("<Button-1>", self.on_left_click)
        self.pack(fill=X)
        self.treeview_frame.pack(fill=X)
        self.entryPopup: Optional[EntryPopup] = None

    def on_left_click(self, event) -> None:
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if column == "#1":
            info = self.bbox(rowid, column)
            if info:
                x, y, width, height = info
                text = self.item(rowid, "values")[0]
                self.entryPopup = EntryPopup(self.root, self, rowid, text, bd=0, highlightthickness=0)
                self.entryPopup.place(x=x, y=y + height // 2, width=width, height=height, anchor=tk.W, relwidth=1)


class Editor:
    def __init__(self) -> None:
        self.running = True
        self.colour = pygame.Color("yellow")
        self.speed = 10
        self.screen = None
        self.screen_rect: Optional[Rect] = None

        # tk.Tk() and pygame.init() must be done in this order and before anything else (in tkinter world)
        self.root = tk.Tk()
        pygame.init()

        self.clock = pygame.time.Clock()

        self.open_tk_window(self.root)
        if WITH_PYGAME:
            self.setup_pygame()
            self.background = Surface(self.screen_rect.size, pygame.HWSURFACE).convert_alpha()
        self.draw = False
        self.draw_size = (50, 50)

    def quit(self) -> None:
        self.running = False
        if WITH_PYGAME:
            pygame.quit()  # destroy pygame window
        self.root.destroy()  # destroy root window
        exit(0)

    def open_tk_window(self, root: tk.Tk) -> tk.Tk:
        def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
            tk.pack(**kwargs)
            return tk

        root.geometry("300x800+10+10")
        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.title("Edit object")

        properties_label = pack(tk.Label(root, text="Properties"), fill=X)

        properties = PropertiesWidget(root)

        values = {
            "First": 1,
            "Second": "some value",
            "Third": True,
            "fourth": 42,
            "fifth": "something",
            "sixth": "line1\nline2\nline3",
            **{k: k for k in range(20)}
        }
        for k, v in values.items():
            properties.insert('', tk.END, text=k, values=(v, ))

        # treeview_frame = tk.Frame(root)
        #
        # properties = ttk.Treeview(treeview_frame, columns=("value",))
        # scrollbar = tk.Scrollbar(treeview_frame,
        #                          orient="vertical",
        #                          command=properties.yview)
        # scrollbar.pack(side=RIGHT, fill=Y)
        # if WITH_SCROLLBAR:
        #     properties.configure(yscrollcommand=scrollbar.set)
        #
        # properties.heading("#0", text="Property")
        # properties.heading("value", text="Value")
        # properties.column("#0", minwidth=50, width=150)
        # properties.column("value", minwidth=50, width=150)
        #
        # for k, v in values.items():
        #     properties.insert('', tk.END, text=k, values=(v, ))
        #
        # def on_left_click(event):
        #     rowid = properties.identify_row(event.y)
        #     column = properties.identify_column(event.x)
        #
        #     info = properties.bbox(rowid, column)
        #     if info:
        #         x, y, width, height = info
        #         text = properties.item(rowid, "values")[0]
        #         self.entryPopup = EntryPopup(root, properties, rowid, text, bd=0, highlightthickness=0)
        #         self.entryPopup.place(x=x, y=y + height // 2, width=width, height=height, anchor=tk.W, relwidth=1)
        #
        # properties.bind("<Button-1>", on_left_click)
        # properties.pack(fill=X)
        # treeview_frame.pack(fill=X)

        select_colour_button = pack(tk.Button(root, text="Select Colour", command=self.select_colour), fill=X)

        return root

    def setup_pygame(self) -> None:
        os.environ['SDL_VIDEO_WINDOW_POS'] = "320,10"

        # pygame.init()

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


editor = Editor()
if WITH_PYGAME:
    editor.pygame_loop()
else:
    editor.root.mainloop()
