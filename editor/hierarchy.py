import tkinter as tk
from tkinter import ttk, RIGHT, X, Y, TOP
from typing import Optional, cast, Callable

from editor.properties import Properties
from engine.tmx import TiledMap, TiledObjectGroup, TiledObject, BaseTiledLayer, TiledElement


class Hierarchy(ttk.Treeview):
    def __init__(self, root: tk.Widget, selected_object_callback: Callable[[Optional[TiledElement]], None]) -> None:
        self.root = root
        self.selected_object_callback = selected_object_callback
        self.treeview_frame = tk.Frame(root)
        super().__init__(self.treeview_frame, columns=("visible",))

        self.scrollbar = tk.Scrollbar(self.treeview_frame,
                                      orient="vertical",
                                      command=self.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.configure(yscrollcommand=self.scrollbar.set)

        self.heading("#0", text="")
        self.heading("visible", text="v")

        self.column("#0", minwidth=50, width=240)
        self.column("visible", minwidth=20, width=40)

        self.bind("<Button-1>", self.on_left_click)
        self.pack(side=TOP, fill=X, expand=True)
        self.treeview_frame.pack(side=TOP, fill=X)
        self.tiled_map: Optional[TiledMap] = None
        self.main_properties: Optional[Properties] = None
        self.custom_properties: Optional[Properties] = None

        self._selected_object: Optional[TiledElement] = None

        self.tag_configure("odd", background="gray95")

    def init_properties_widgets(self, main_properties: Properties, custom_properties: Properties):
        self.main_properties = main_properties
        self.custom_properties = custom_properties

    @property
    def selected_object(self) -> TiledElement:
        return self._selected_object

    @selected_object.setter
    def selected_object(self, selected_object: Optional[TiledElement]) -> None:
        self._selected_object = selected_object

        if selected_object is not None:
            self.main_properties.update_properties(
                {k: getattr(selected_object, k) for k in type(selected_object).ATTRIBUTES.keys()},
                type(selected_object).ATTRIBUTES
            )
            self.custom_properties.update_properties(selected_object.properties)
        else:
            self.main_properties.update_properties({})
            self.custom_properties.update_properties({})

        self.selected_object_callback(selected_object)

    @staticmethod
    def _obj_visibility(e: TiledObject | BaseTiledLayer) -> str:
        return "o" if e.visible else "-"

    def set_map(self, tiled_map: TiledMap) -> None:
        self.tiled_map = tiled_map
        self.delete(*self.get_children())

        self.insert('', tk.END, iid="map", text="map", open=True)
        self.insert('', tk.END, iid="tilesets", text="tilesets", open=True)
        self.insert('', tk.END, iid="layers", text="layers", open=True)

        for i, tileset in enumerate(tiled_map.tilesets):
            self.insert('', tk.END, iid=f"ts_{i}", text=f"{tileset.name}", values=("", ), open=True)
            self.move(f"ts_{i}", "tilesets", i)

        for i, layer in enumerate(tiled_map.layers):
            self.insert('', tk.END, iid=f"l_{layer.id}", text=f"{layer.name}", values=(self._obj_visibility(layer), ), open=False)
            self.move(f"l_{layer.id}", "layers", i)
            if isinstance(layer, TiledObjectGroup):
                for j, obj in enumerate(layer.objects):
                    self.insert('', tk.END, iid=f"o_{layer.id}_{obj.id}", text=f"{obj.name}", values=(self._obj_visibility(obj), ), open=True)
                    self.move(f"o_{layer.id}_{obj.id}", f"l_{layer.id}", j)

        def tag(el, even: bool) -> bool:
            for child in self.get_children() if el is None else self.get_children(el):
                self.item(child, tags="even" if even else "odd")
                even = not even
                even = tag(child, even)
            return even

        tag(None, True)

        self.main_properties.update_properties({})
        self.custom_properties.update_properties({})

        self.bind("<<TreeviewSelect>>", self.on_tree_select)

    def on_tree_select(self, _event):
        for rowid in self.selection():
            selected_object = None
            if rowid == "map":
                selected_object = self.tiled_map
            elif rowid == "tilesets":
                pass
            elif rowid == "layers":
                pass
            elif rowid.startswith("ts_"):
                s = rowid.split("_")
                selected_object = self.tiled_map.tilesets[int(s[1])]
            elif rowid.startswith("l_"):
                s = rowid.split("_")
                selected_object = cast(TiledObjectGroup, self.tiled_map.layer_id_map[int(s[1])])
            elif rowid.startswith("o_"):
                s = rowid.split("_")
                layer = cast(TiledObjectGroup, self.tiled_map.layer_id_map[int(s[1])])
                selected_object = layer.objects_id_map[int(s[2])]

            self.selected_object = selected_object

    def on_left_click(self, event) -> None:
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if column == "#1":
            if rowid.startswith("o_"):
                s = rowid.split("_")
                layer = cast(TiledObjectGroup, self.tiled_map.layer_id_map[int(s[1])])
                obj = layer.objects_id_map[int(s[2])]
                obj.visible = not obj.visible
                self.item(rowid, values=(self._obj_visibility(obj),))
            elif rowid.startswith("l_"):
                s = rowid.split("_")
                layer = cast(TiledObjectGroup, self.tiled_map.layer_id_map[int(s[1])])
                layer.visible = not layer.visible
                self.item(rowid, values=(self._obj_visibility(layer),))
