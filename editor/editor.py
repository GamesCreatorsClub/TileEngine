import os
from typing import Optional

import pygame
import tkinter as tk

from tkinter import colorchooser, ttk, RIGHT, Y, X, LEFT
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


class EditText:
    def __init__(self, root: tk.Tk, properties_widget: PropertiesWidget) -> None:
        self.properties_widget = properties_widget
        self.pop_up_window = tk.Tk()
        self.frame = tk.Frame(self.pop_up_window, highlightbackground="green", highlightcolor="green", highlightthickness=1, bd=0)
        self.frame.pack()
        self.pop_up_window.overrideredirect(1)
        self.pop_up_window.geometry("200x70+650+400")
        self.label = tk.Label(self.frame, text="Edit text")
        self.label.pack()
        yes_btn = tk.Button(self.frame, text="Yes", bg="light blue", fg="red", command=self.ok, width=10)
        yes_btn.pack(padx=10, pady=10, side=LEFT)
        no_btn = tk.Button(self.frame, text="No", bg="light blue", fg="red", command=self.close, width=10)
        no_btn.pack(padx=10, pady=10, side=LEFT)

    def ok(self) -> None:
        print("OK!")
        self.close()

    def close(self) -> None:
        self.pop_up_window.destroy()


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
        filemenu.add_command(label="Open", command=self.donothing)
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

        properties_label = pack(tk.Label(root, text="Properties"), fill=X)

        main_properties = PropertiesWidget(root)
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
            main_properties.insert('', tk.END, text=k, values=(v, ))

        pack(tk.Label(root, text=""), fill=X)
        custom_properties_label = pack(tk.Label(root, text="Custom Properties"), fill=X)

        custom_properties = PropertiesWidget(root)
        values = {
            "on_click": "do_nothing()",
            "on_animation": "a = a + 1",
            "on_entry": "say_once(\"Hey\")",
            "on_leave": "say(\"Buy\")",
            **{f"custom_{k}": k for k in range(20)}
        }
        for k, v in values.items():
            custom_properties.insert('', tk.END, text=k, values=(v, ))

        select_colour_button = pack(tk.Button(root, text="Select Colour", command=self.select_colour), fill=X)

        def open_edit() -> None:
            text_edit = EditText(root, properties_widget=custom_properties)

        pack(tk.Button(root, text="Edit text", command=open_edit), fill=X)

        return root

    def donothing(self) -> None:
        print("Do nothigng!")

    def on_load(self) -> None:
        print("Called on load")

    def on_save(self) -> None:
        print("Called on load")

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
