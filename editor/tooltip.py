from typing import Optional

import tkinter as tk


class ToolTip:
    def __init__(self, button: tk.Button, text=None):
        self.tooltip: Optional[tk.Toplevel] = None
        self.disabled = True

        def on_enter(event):
            if not self.disabled:
                self.tooltip = tk.Toplevel()
                self.tooltip.overrideredirect(True)
                self.tooltip.geometry(f"+{event.x_root+15}+{event.y_root+10}")

                self.label = tk.Label(self.tooltip, text=self.text)
                self.label.pack()

        def on_leave(_event=None):
            if self.tooltip is not None:
                self.tooltip.destroy()
                self.tooltip = None

        self.button = button
        self.text = text

        self.button.bind('<Enter>', on_enter)
        self.button.bind('<Leave>', on_leave)
