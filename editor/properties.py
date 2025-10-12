import os.path
import tkinter as tk
from tkinter import ttk, INSERT, BOTH, END, RIGHT, LEFT, X, Y, BOTTOM, TOP, colorchooser, filedialog
from typing import Callable, Optional, Any, Union

from editor.actions_controller import ActionsController
from engine.tmx import F, TiledMap


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


class AddNewPropertyText(tk.Toplevel):
    def __init__(self, root: Union[tk.Widget, tk.Tk], callback: Callable[[str], None]) -> None:
        super().__init__(root)
        self.root = root
        self.callback = callback
        self.title(f"Add new property")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()
        self.frame = tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5)
        self.entry = tk.Entry(self.frame, bd=0, highlightthickness=0, state="normal")
        self.entry.insert(INSERT, "")
        self.entry.pack(side=TOP, fill=BOTH, expand=True)
        self.entry.bind("<Return>", self.ok)
        self.entry.bind("<Escape>", self.close)
        self.frame.pack(side=TOP, fill=BOTH, expand=True)
        self.buttons_frame = tk.Frame(self, highlightthickness=0, bd=0)
        self.buttons_frame.pack(side=BOTTOM, fill=X)
        self.ok_btn = pack(tk.Button(self.buttons_frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)
        self.cancel_btn = pack(tk.Button(self.buttons_frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.close)
        self.entry.focus()

    def ok(self, _event=None) -> None:
        new_value = self.entry.get()
        if new_value.rstrip(" ").endswith("\n"):
            new_value = new_value.rstrip(" ")[:-1]
        self.callback(new_value)
        self.destroy()

    def close(self, _event=None) -> None:
        self.destroy()


class EditText(tk.Toplevel):
    def __init__(self, root: Union[tk.Widget, tk.Tk], macos: bool, rowid: str, name: str, text: str, callback: Callable[[str, str], None]) -> None:
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
        control_modifier = "Command" if macos else "Control"
        self.bind(f"<{control_modifier}-Return>", self.ok)
        self.bind("<Escape>", self.close)
        self.entry.bind(f"<{control_modifier}-Return>", self.ok)
        self.entry.bind("<Escape>", self.close)
        self.entry.focus()

    def ok(self, _event=None) -> None:
        new_value = self.entry.get("1.0", END)
        if new_value.rstrip(" ").endswith("\n"):
            new_value = new_value.rstrip(" ")[:-1]
        self.callback(self.rowid, new_value)
        self.destroy()

    def close(self, _event=None) -> None:
        self.destroy()


class BooleanPopup(tk.Frame):
    def __init__(self,
                 window: tk.Widget,
                 parent: tk.Widget,
                 x: int, y: int, width: int, height: int,
                 rowid: str, text: str,
                 update_value_callback: Callable[[str, str], None]):

        super().__init__(parent, bd=0, highlightthickness=0)

        self.pack()
        self.window = window
        self.rowid = rowid
        self.update_value_callback = update_value_callback

        self.value = text

        self.button = tk.Label(self, text="True" if text.lower() == "true" else "False")
        self.button.pack(side=LEFT)
        self.button.bind("<Button-1>", self.toggle_value)

        self.destroyed = False

        self.button.focus_force()
        self.button.bind("<Return>", self.update_value)

        self.button.bind("<Escape>", self.abandon_edit)
        self.button.bind("<FocusOut>", self.update_value)

        self.place(x=x, y=y, width=width, height=height, anchor=tk.NW, relwidth=0.5)

    def abandon_edit(self, _event) -> None:
        if not self.destroyed:
            self.destroyed = True
            self.destroy()

    def update_value(self, _event) -> None:
        if not self.destroyed:
            self.update_value_callback(self.rowid, self.value)
            self.destroyed = True
            self.destroy()

    def toggle_value(self, _event) -> None:
        self.value = "False" if self.value.lower() == "true" else "True"
        self.button["text"] = self.value
        self.update_value_callback(self.rowid, self.value)


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
        self.entry["exportselection"] = False
        self.entry.pack(fill=X)

        self.destroyed = False

        self.entry.focus_force()
        self.entry.bind("<Return>", self.update_value)
        self.entry.bind("<Control-a>", self.select_all)

        self.entry.bind("<Escape>", self.abandon_edit)
        self.entry.bind("<FocusOut>", self.update_value)

        self.place(x=x, y=y, width=width, height=height, anchor=tk.NW, relwidth=0.5)

    def abandon_edit(self, _event) -> None:
        if not self.destroyed:
            self.destroyed = True
            self.destroy()

    def update_value(self, _event) -> None:
        if not self.destroyed:
            new_value = self.entry.get()
            if new_value.rstrip().endswith("/n"):
                new_value = new_value.rstrip()[:-1]
            self.update_value_callback(self.rowid, new_value)
            self.destroyed = True
            self.destroy()

    def select_all(self, _event) -> None:
        if not self.destroyed:
            self.entry.selection_range(0, tk.END)
        return "break"

    def stop_and_open_text_editor(self, _even) -> None:
        self.abandon_edit(None)
        self.open_text_editor_callback(self.rowid)


class Properties(ttk.Treeview):
    def __init__(self,
                 root: tk.Widget,
                 macos: bool,
                 tk_images: dict[str, tk.PhotoImage],
                 actions_controller: ActionsController,
                 add_callback: Optional[Callable[[str, str], None]],
                 update_callback: Callable[[str, str], None],
                 delete_callback: Optional[Callable[[str], None]],
                 element_select_callback: Optional[Callable[[Optional[str]], None]]) -> None:
        self.root = root
        self.macos = macos
        self.tk_images = tk_images
        self.actions_controller = actions_controller
        self.add_callback = add_callback
        self.update_callback = update_callback
        self.delete_callback = delete_callback
        self.element_select_callback = element_select_callback
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
        self.pack(side=TOP, fill=X, expand=True)
        self.treeview_frame.pack(side=TOP, fill=X)
        self.entryPopup: Optional[EntryPopup] = None
        self.editorPopup: Optional[EditText] = None
        self.addNewPropertyPopup: Optional[AddNewPropertyText] = None

        self.tag_configure("odd", background="gray95")
        self.tag_configure("disabled", foreground="gray")
        self.add_button: Optional[tk.Button] = None
        self.remove_button: Optional[tk.Button] = None
        self.edit_button: Optional[tk.Button] = None

        self.selected_rowid = None
        self.properties: Optional[dict[str, Any]] = None

        self.bind("<<TreeviewSelect>>", self.select_element)

    def select_element(self, _event) -> None:
        selection = self.selection()
        if selection is not None and len(selection) > 0:
            self.selected_rowid = self.selection()[0]

            if self.remove_button is not None:
                self.remove_button.configure(state="normal", image=self.tk_images["remove-icon"])
            if self.element_select_callback is not None:
                self.element_select_callback(self.selected_rowid)

            tags = self.item(self.selected_rowid, "tags")

            if self.edit_button is not None:
                if "disabled" not in tags:
                    self.edit_button.configure(state="normal")
                else:
                    self.edit_button.configure(state="disabled")

    def update_buttons(self,
                       add_button: tk.Button,
                       remove_button: tk.Button,
                       edit_button: tk.Button) -> None:
        self.add_button = add_button
        self.remove_button = remove_button
        self.edit_button = edit_button

    def on_left_click(self, event) -> None:
        self.selected_rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
        tags = self.item(self.selected_rowid, "tags")
        info = self.bbox(self.selected_rowid, column)
        if info:
            if "disabled" not in tags:
                if column == "#1":
                    self.start_editing(self.selected_rowid)

    def on_double_left_click(self, event) -> None:
        self.selected_rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if column == "#1":
            self.open_text_editor(self.selected_rowid)

    def open_text_editor(self, rowid: str) -> None:
        name = self.item(rowid, "text")
        text = self.item(rowid, "values")[0]
        self.editorPopup = EditText(self.root, self.macos, rowid, name, text, self.update_value)

    def start_editing(self, selected_rowid: str) -> None:
        info = self.bbox(selected_rowid, "#1")
        x, y, width, height = info
        tags = self.item(selected_rowid, "tags")

        text = self.item(selected_rowid, "values")[0]

        if "Color" in tags:
            def extract_color(v: str) -> str:
                return "#" + "".join(f"{int(s.strip()):02x}" for s in v[1:-1].split(","))

            initial_color = extract_color(text) if text != "" and text is not None else None
            color = colorchooser.askcolor(color=initial_color)
            if color[0] is not None:
                self.update_value(selected_rowid, str(color[0]))
        elif "Path" in tags:
            filename = filedialog.askopenfilename(title="Select python code", filetypes=(("Python file", "*.py"),))
            if filename:
                if self.actions_controller.tiled_map.filename:
                    filename = os.path.relpath(filename, os.path.dirname(self.actions_controller.tiled_map.filename))
                self.update_value(selected_rowid, filename)
        elif "bool" in tags:
            self.entryPopup = BooleanPopup(
                self.root, self,
                x=x, y=y,
                width=5,  # width - self.scrollbar.winfo_width(),
                height=height,
                rowid=selected_rowid, text=text,
                update_value_callback=self.update_value)
        elif "\n" not in text:
            self.entryPopup = EntryPopup(
                self.root, self,
                x=x, y=y,
                width=5,  # width - self.scrollbar.winfo_width(),
                height=height,
                rowid=selected_rowid, text=text,
                update_value_callback=self.update_value,
                open_text_editor_callback=self.open_text_editor)
        else:
            self.open_text_editor(selected_rowid)

    def start_add_new_property(self) -> None:
        def add_new_property(new_property_name: str) -> None:
            self.add_callback(new_property_name, "")

            # even = len(self.get_children()) % 2 == 0
            # self.insert("", tk.END, iid=new_property_name, text=new_property_name, values=("",), tags=("even" if even else "odd", True, str))

        self.addNewPropertyPopup = AddNewPropertyText(self.root, add_new_property)

    def add_new_property_with_name(self, property_name: str) -> None:
        self.add_callback(property_name, "")

        # even = len(self.get_children()) % 2 == 0
        # self.insert("", tk.END, iid=property_name, text=property_name, values=("",), tags=("even" if even else "odd", True, str))
        self.start_editing(property_name)

    def update_value(self, rowid: str, new_value: str, no_callback: bool = False) -> None:
        self.item(rowid, values=(new_value,))
        self.editorPopup = None
        self.entryPopup = None
        if not no_callback:
            self.update_callback(rowid, new_value)

    def update_properties(self, properties: dict[str, Any], types_and_visibility: Optional[dict[str, F]] = None) -> None:
        for c in self.get_children():
            self.delete(c)

        self.properties = properties
        even = True
        for k, v in properties.items():
            if not k.startswith("__"):
                enabled = "enabled" if types_and_visibility is None or (k in types_and_visibility and types_and_visibility[k].visible) or k not in types_and_visibility else "disabled"
                typ = types_and_visibility[k].type.__name__ if types_and_visibility is not None and k in types_and_visibility else "unknown_type"
                if typ == "Color":
                    v = "(" + ",".join(str(s) for s in v) + ")" if v is not None and v != "" else ""
                self.insert("", tk.END, iid=k, text=k, values=(v, ), tags=("even" if even else "odd", enabled, typ))
                even = not even

    def remove_property(self) -> None:
        if self.selected_rowid is not None:
            self.delete(self.selected_rowid)
            self.delete_callback(self.selected_rowid)
            if self.remove_button is not None:
                self.remove_button.configure(state="disabled", image=self.tk_images["remove-icon-disabled"])
            if self.element_select_callback is not None:
                self.element_select_callback(None)

    def edit_selected_property(self) -> None:
        if self.selected_rowid is not None:
            self.open_text_editor(self.selected_rowid)
