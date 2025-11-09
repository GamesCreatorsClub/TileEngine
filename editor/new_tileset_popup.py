import tkinter as tk
from tkinter import BOTH, RIGHT, X, BOTTOM, TOP
from typing import Callable, Any, Union

from editor.actions_controller import ActionsController
from editor.properties import Properties, pack
from editor.tk_utils import handle_exception_tk
from engine.tmx import F


class NewTilesetPopup(tk.Toplevel):
    def __init__(self,
                 root: Union[tk.Widget, tk.Tk],
                 actions_controller: ActionsController,
                 name: str,
                 macos: bool,
                 tkinter_images: dict[str, tk.PhotoImage],
                 image_width: int,
                 callback: Callable[[int, int, int, int, int], None]):

        super().__init__(root, bd=0, highlightthickness=0)

        self.image_width = image_width
        self.actions_controller = actions_controller

        self.tilewidth = 16
        self.tileheight = 16
        self.columns = image_width // self.tilewidth
        self.spacing = 0
        self.margin = 0

        self.callback = callback
        self.tkinter_images = tkinter_images

        self.title(f"Add new tileset {name}")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()
        self.frame = tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5)

        self.properties = Properties(self, macos, self.tkinter_images,
                                     self.actions_controller,
                                     None,
                                     self.update_current_element_attribute,
                                     None,
                                     None)
        self.properties.pack(side=TOP, fill=BOTH, expand=True)
        self.frame.pack(side=TOP, fill=BOTH, expand=True)
        self.buttons_frame = tk.Frame(self, highlightthickness=0, bd=0)
        self.buttons_frame.pack(side=BOTTOM, fill=X)
        self.ok_btn = pack(tk.Button(self.buttons_frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)
        self.cancel_btn = pack(tk.Button(self.buttons_frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)
        control_modifier = "Command" if macos else "Control"
        self.bind(f"<{control_modifier}-Return>", self.ok)
        self.bind("<Escape>", self.close)
        self.properties.bind(f"<{control_modifier}-Return>", self.ok)
        self.properties.bind("<Escape>", self.close)
        self.properties.focus()

        self.values = {
            "tilewidth": 16,
            "tileheight": 16,
            "columns": self.image_width // 16,
            "spacing": 0,
            "margin": 0
        }

        self.properties.update_properties(self.values, {
            "tilewidth": F(int, True), "tileheight": F(int, True),
            "columns": F(int, True),
            "spacing": F(int, True), "margin": F(int, True),
            "imagewidth": F(int, False)
        })

    @handle_exception_tk
    def ok(self, _event=None) -> None:
        self.callback(int(self.values["tilewidth"]), int(self.values["tileheight"]),
                      int(self.values["columns"]), int(self.values["spacing"]), int(self.values["margin"]))
        self.destroy()

    @handle_exception_tk
    def close(self, _event=None) -> None:
        self.destroy()

    def update_current_element_attribute(self, key: str, value: Any) -> None:
        def from_int(s: Union[str, int]) -> int:
            try:
                return int(s)
            except Exception:
                return -1

        print(f"Edited property {key} to {value}")
        self.values[key] = value
        if key == "tilewidth" or key == "margin" or key == "spacing":
            available_pixels = (self.image_width - from_int(self.values["margin"])) + from_int(self.values["spacing"])  # Add artificial last spacing that does not exist
            columns = available_pixels // (from_int(self.values["tilewidth"]) + from_int(self.values["spacing"]))
            self.values["columns"] = columns
            self.properties.update_value("columns", str(columns), True)
        if key == "columns":
            # TODO implement this properly using margin and spacing in consideration
            tilewidth = self.image_width // from_int(value)
            self.values["tilewidth"] = tilewidth
            self.properties.update_value("tilewidth", str(tilewidth), True)
