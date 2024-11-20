import tkinter as tk
from tkinter import ttk, INSERT, BOTH, END, RIGHT, X, Y, BOTTOM, TOP, LEFT
from typing import Callable, Optional


class Hierarchy(ttk.Treeview):
    def __init__(self, root: tk.Widget) -> None:
        self.root = root
        self.treeview_frame = tk.Frame(root)
        super().__init__(self.treeview_frame)

        self.heading("#0", text="")

        self.scrollbar = tk.Scrollbar(self.treeview_frame,
                                      orient="vertical",
                                      command=self.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.configure(yscrollcommand=self.scrollbar.set)

        self.column("#0", minwidth=50, width=120)
        # self.column("value", minwidth=50, width=130)

        self.bind("<Button-1>", self.on_left_click)
        self.pack(side=TOP, fill=X, expand=True)
        self.treeview_frame.pack(side=TOP, fill=X)

    def on_left_click(self, event) -> None:
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
