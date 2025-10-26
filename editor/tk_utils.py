import tkinter as tk

from typing import Optional


def bindtag(parent: tk.Widget, widget: tk.Widget, name: Optional[str] = None) -> tk.Widget:
    if name is not None:
        widget.bindtags((widget, name, parent, ".", "all"))
    else:
        widget.bindtags((widget, parent, ".", "all"))
    return widget


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk
