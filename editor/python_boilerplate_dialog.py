import tkinter as tk
from tkinter import BOTH, RIGHT, X, BOTTOM, TOP, W, filedialog
from typing import Callable, Union, Optional, cast

from editor.properties import pack


class PythonBoilerplateDialog(tk.Toplevel):
    def __init__(self, root: Union[tk.Widget, tk.Tk], callback: Callable[[str], None], python_file: Optional[str]) -> None:
        super().__init__(root)
        self.root = root
        self.callback = callback
        self.title(f"Create Python Code")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()

        self.top_down_var = tk.StringVar(self)
        self.top_down_var.set("top_down")

        self.frame = tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5)
        self.top_down_radio_button = pack(tk.Radiobutton(self, text="Top Down", variable=self.top_down_var, value="top_down"), anchor=W)
        self.side_radio_button = pack(tk.Radiobutton(self, text="Side Scroller", variable=self.top_down_var, value="side"), anchor=W)

        self.entry_frame = pack(tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5), fill=X)

        self.button = pack(tk.Label(self.entry_frame, text="..."), side=RIGHT)
        # self.button.bind("<Button-1>", self.stop_and_open_text_editor)

        self.entry = pack(tk.Entry(self.entry_frame, bd=0, highlightthickness=0), fill=X, padx=5)
        cast(tk.Entry, self.entry).insert(0, python_file if python_file is not None else "")
        self.entry["exportselection"] = False

        self.frame.pack(side=TOP, fill=BOTH, expand=True)
        self.buttons_frame = tk.Frame(self, highlightthickness=0, bd=0)
        self.buttons_frame.pack(side=BOTTOM, fill=X)
        self.ok_btn = pack(tk.Button(self.buttons_frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)
        self.cancel_btn = pack(tk.Button(self.buttons_frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)
        self.bind("<Escape>", self.close)

    def ok(self, _event=None) -> None:
        # new_value = self.entry.get("1.0", END)
        # if new_value.rstrip(" ").endswith("\n"):
        #     new_value = new_value.rstrip(" ")[:-1]
        self.destroy()

    def close(self, _event=None) -> None:
        self.destroy()
