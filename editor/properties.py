import tkinter as tk
from tkinter import ttk, INSERT, BOTH, END, RIGHT, X, Y, BOTTOM, TOP, LEFT
from typing import Callable, Optional


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class EditText(tk.Toplevel):
    def __init__(self, root: tk.Widget, rowid: str, name: str, text: str, callback: Callable[[str, str], None]) -> None:
        super().__init__(root)
        self.root = root
        self.rowid = rowid
        self.callback = callback
        self.title(f"Edit {name}")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()
        self.frame = tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5)
        self.entry = tk.Text(self.frame, width=40, height=5, state="normal")
        self.entry.insert(INSERT, text)
        self.ys = ttk.Scrollbar(self.frame, orient="vertical", command=self.entry.yview)
        self.xs = ttk.Scrollbar(self.frame, orient="horizontal", command=self.entry.xview)
        self.entry["yscrollcommand"] = self.ys.set
        self.entry["xscrollcommand"] = self.xs.set
        self.ys.pack(side=RIGHT, fill=Y)
        self.xs.pack(side=BOTTOM, fill=X)
        self.entry.pack(side=TOP, fill=BOTH, expand=True)
        self.frame.pack(side=TOP, fill=BOTH, expand=True)
        self.buttons_frame = tk.Frame(self, highlightthickness=0, bd=0)
        self.buttons_frame.pack(side=BOTTOM, fill=X)
        self.ok_btn = pack(tk.Button(self.buttons_frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)
        self.cancel_btn = pack(tk.Button(self.buttons_frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)

    def ok(self) -> None:
        new_value = self.entry.get("1.0", END)
        if new_value.rstrip(" ").endswith("\n"):
            new_value = new_value.rstrip(" ")[:-1]
        self.callback(self.rowid, new_value)
        self.destroy()

    def close(self) -> None:
        self.destroy()


class EntryPopup(tk.Frame):
    def __init__(self,
                 window: tk.Widget,
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
            if new_value.rstrip().endswith("/n"):
                new_value = new_value.rstrip()[:-1]
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


class Properties(ttk.Treeview):
    def __init__(self, root: tk.Widget) -> None:
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
        self.column("#0", minwidth=50, width=130)
        self.column("value", minwidth=50, width=130)

        self.bind("<Button-1>", self.on_left_click)
        # self.bind("<Double-1>", self.on_double_left_click)
        self.pack(side=TOP, fill=X, expand=True)
        self.treeview_frame.pack(side=TOP, fill=X)
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
