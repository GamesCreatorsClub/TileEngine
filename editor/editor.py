import os

import pygame
import tkinter as tk

from tkinter import colorchooser, ttk, RIGHT, Y, X, filedialog, BOTH, TOP, INSERT, END, LEFT, NW

from typing import Optional, Callable
from sys import exit

from pygame import Surface, Rect

from engine.tmx import TiledMap, TiledElement

WITH_PYGAME = True
WITH_SCROLLBAR = True


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class EditText(tk.Toplevel):
    def __init__(self, root: tk.Tk, rowid: str, name: str, text: str, callback: Callable[[str, str], None]) -> None:
        super().__init__(root)
        self.root = root
        self.rowid = rowid
        self.callback = callback
        self.title(f"Edit {name}")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()
        self.frame = tk.Frame(self, highlightbackground="green", highlightcolor="green", highlightthickness=0, bd=0)
        self.frame.pack()
        # self.label = tk.Label(self.frame, text="Edit text")
        # self.label.pack(side=TOP)
        self.entry = tk.Text(self.frame, width=40, height=5, state="normal")
        self.entry.insert(INSERT, text)
        self.ys = ttk.Scrollbar(self, orient="vertical", command=self.entry.yview)
        self.xs = ttk.Scrollbar(self, orient="horizontal", command=self.entry.xview)
        self.entry["yscrollcommand"] = self.ys.set
        self.entry["xscrollcommand"] = self.xs.set
        self.entry.pack(fill=BOTH)
        self.cancel_btn = pack(tk.Button(self.frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)
        self.ok_btn = pack(tk.Button(self.frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)

    def ok(self) -> None:
        self.callback(self.rowid, self.entry.get("1.0", END))
        self.destroy()

    def close(self) -> None:
        self.destroy()


class EntryPopup(tk.Frame):
    def __init__(self,
                 window: tk.Tk,
                 parent: tk.Widget,
                 x: int, y: int, width: int, height: int,
                 rowid: str, text: str,
                 update_value_callback: Callable[[str, str], None],
                 open_text_editor_callback: Callable[[str], None]):

        super().__init__(parent, bd=0, highlightthickness=0)

        self.pack()
        self.window = window
        self.rowid = rowid
        self.update_value_callback = update_value_callback
        self.open_text_editor_callback = open_text_editor_callback

        self.button = tk.Label(self, text="...")
        self.button.pack(side=RIGHT)
        self.button.bind("<Button-1>", self.stop_and_open_text_editor)

        self.entry = tk.Entry(self, bd=0, highlightthickness=0)
        self.entry.insert(0, text)
        self.entry['exportselection'] = False
        self.entry.pack(fill=X)

        self.destroyed = False

        # self.focus_force()
        self.entry.focus_force()
        self.entry.bind("<Return>", self.update_value)
        self.entry.bind("<Control-a>", self.select_all)

        self.entry.bind("<Escape>", self.abandon_edit)
        self.entry.bind("<FocusOut>", self.update_value)
        # self.window.bind("<FocusOut>", self.update_value)

        self.place(x=x, y=y, width=width, height=height, anchor=tk.NW, relwidth=0.5)

    def abandon_edit(self, _event):
        if not self.destroyed:
            self.destroyed = True
            self.destroy()

    def update_value(self, _event):
        if not self.destroyed:
            new_value = self.entry.get()
            self.update_value_callback(self.rowid, new_value)
            self.destroyed = True
            self.destroy()

    def select_all(self, _event):
        if not self.destroyed:
            self.entry.selection_range(0, tk.END)
            return "break"

    def stop_and_open_text_editor(self, _even) -> None:
        self.abandon_edit(None)
        self.open_text_editor_callback(self.rowid)


class PropertiesWidget(ttk.Treeview):
    def __init__(self, editor: 'Editor', root: tk.Tk) -> None:
        self.editor = editor
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
        # self.bind("<Double-1>", self.on_double_left_click)
        self.pack(fill=X)
        self.treeview_frame.pack(fill=X)
        self.entryPopup: Optional[EntryPopup] = None
        self.editorPopup: Optional[EditText] = None

    def on_left_click(self, event) -> None:
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if column == "#1":
            info = self.bbox(rowid, column)
            if info:
                x, y, width, height = info
                text = self.item(rowid, "values")[0]

                if "\n" not in text:
                    self.entryPopup = EntryPopup(
                        self.root, self,
                        x=x, y=y,
                        width=5,  # width - self.scrollbar.winfo_width(),
                        height=height,
                        rowid=rowid, text=text,
                        update_value_callback=self.update_value,
                        open_text_editor_callback=self.open_text_editor)
                else:
                    self.open_text_editor(rowid)

    def on_double_left_click(self, event) -> None:
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if column == "#1":
            self.open_text_editor(rowid)

    def open_text_editor(self, rowid: str) -> None:
        name = self.item(rowid, "text")
        text = self.item(rowid, "values")[0]
        self.editorPopup = EditText(self.root, rowid, name, text, self.update_value)

    def update_value(self, rowid: str, new_value: str) -> None:
        self.item(rowid, values=(new_value,))
        self.editorPopup = None
        self.entryPopup = None


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
        self.main_properties: Optional[PropertiesWidget] = None
        self.custom_properties: Optional[PropertiesWidget] = None

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

        properties_label = pack(tk.Label(root, text="Properties"), fill=X)

        self.main_properties = PropertiesWidget(self, root)
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
        custom_properties_label = pack(tk.Label(root, text="Custom Properties"), fill=X)

        self.custom_properties = PropertiesWidget(self, root)
        values = {
            "on_click": "do_nothing()",
            "on_animation": "a = a + 1",
            "on_entry": "say_once(\"Hey\")\n# second line \nb = b + 1\n",
            "on_leave": "say(\"Buy\")",
            # **{f"custom_{k}": k for k in range(20)}
        }
        for k, v in values.items():
            self.custom_properties.insert('', tk.END, text=k, values=(v, ))

        select_colour_button = pack(tk.Button(root, text="Select Colour", command=self.select_colour), fill=X)

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
