from tkinter.messagebox import askyesno
from zipfile import ZipFile

import os

from functools import reduce

from re import finditer

import tkinter as tk
from tkinter import BOTH, RIGHT, X, BOTTOM, TOP, W
from typing import Callable, Union, Optional, cast

from editor.properties import pack
from engine.tmx import TiledMap


class PythonBoilerplateDialog(tk.Toplevel):
    def __init__(self, root: Union[tk.Widget, tk.Tk],
                 tiled_map: TiledMap,
                 this_zip_file: Optional[str]) -> None:
        super().__init__(root)
        self.root = root
        self.tiled_map = tiled_map
        self.this_zip_file = this_zip_file

        self.title(f"Create Python Code")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.transient(root)
        self.wait_visibility()
        self.grab_set()

        self.top_down_var = tk.StringVar(self)
        self.top_down_var.set("top_down")

        self.frame = tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5)
        self.top_down_radio_button = pack(tk.Radiobutton(self, text="Top Down", variable=self.top_down_var, value="top_down"), anchor=W)
        self.side_radio_button = pack(tk.Radiobutton(self, text="Side Scroller", variable=self.top_down_var, value="side_scroller"), anchor=W)

        self.entry_frame = pack(tk.Frame(self, highlightthickness=0, bd=0, padx=5, pady=5), fill=X)

        # self.button = pack(tk.Label(self.entry_frame, text="..."), side=RIGHT)
        # self.button.bind("<Button-1>", self.stop_and_open_text_editor)

        python_name = ""
        if "python_file" in self.tiled_map:
            python_name = os.path.split(self.tiled_map["python_file"])[1]
            python_name = python_name[:-3] if python_name.endswith(".py") else python_name
            python_name = self.to_python_class_name(python_name)

        self.entry = pack(tk.Entry(self.entry_frame, bd=0, highlightthickness=0), fill=X, padx=5)
        cast(tk.Entry, self.entry).insert(0, python_name)
        self.entry["exportselection"] = False

        self.frame.pack(side=TOP, fill=BOTH, expand=True)
        self.buttons_frame = tk.Frame(self, highlightthickness=0, bd=0)
        self.buttons_frame.pack(side=BOTTOM, fill=X)
        self.ok_btn = pack(tk.Button(self.buttons_frame, text="OK", command=self.ok, width=5), padx=5, pady=10, side=RIGHT)
        self.cancel_btn = pack(tk.Button(self.buttons_frame, text="Cancel", command=self.close, width=5), padx=5, pady=10, side=RIGHT)
        self.bind("<Escape>", self.close)

    def ok(self, _event=None) -> None:
        name = cast(tk.Entry, self.entry).get()

        if name == "":
            tk.messagebox.showerror(title="Error", message=f"You must enter game name")
        else:
            name = name.replace(" ", "_")

            if "python_file" in self.tiled_map:
                game_path = os.path.dirname(self.tiled_map["python_file"])
            else:
                map_dir = os.path.dirname(self.tiled_map.filename)
                game_path = os.path.dirname(map_dir) if map_dir.endswith("assets") else map_dir

            map_filename = self.tiled_map.filename[len(game_path) + 1:]

            level_name = os.path.split(map_filename)[1]
            level_name = level_name[:-4] if level_name.endswith(".tmx") else level_name

            engine_path = os.path.join(game_path, "engine")
            if not os.path.exists(engine_path):
                self.prepare_game_resources(game_path)
            else:
                print(f"Path {engine_path} already exists - skipping copying files.")

            read_prefix = self.top_down_var.get()

            main_class_name = self.to_python_class_name(name)
            main_full_filename = os.path.join(game_path, self.to_python_filename(name))
            context_class_name = self.to_python_class_name(name) + "Context"
            context_filename = self.to_python_filename(name + "_context")
            context_full_filename = os.path.join(game_path, context_filename)

            print(f"Creating {main_class_name} in {main_full_filename}")
            main_content = self.read_content(f"examples/{read_prefix}_example_game_main.py")
            proceed = True
            if os.path.exists(main_full_filename):
                print(f"File {main_full_filename} already exists")
                proceed = askyesno(title=f"File {main_full_filename}",
                                   message=f"File {main_full_filename} already exists. Do you want to overwrite it?")

            if proceed:
                self.write_content(main_full_filename, self.process_main_file(
                    main_content,
                    context_filename, context_class_name,
                    map_filename,
                    level_name,
                    read_prefix == "top_down"))

            print(f"Creating {context_class_name} in {context_full_filename}")
            main_content = self.read_content(f"examples/{read_prefix}_example_game_context.py")
            proceed = True
            if os.path.exists(context_full_filename):
                print(f"File {context_full_filename} already exists")
                proceed = askyesno(title=f"File {context_full_filename}",
                                   message=f"File {context_full_filename} already exists. Do you want to overwrite it?")

            if proceed:
                self.write_content(
                    context_full_filename,
                    self.process_context_file(
                        main_content,
                        context_class_name,
                        read_prefix == "top_down"))

            self.tiled_map["python_file"] = main_full_filename

        self.destroy()

    def close(self, _event=None) -> None:
        self.destroy()

    def prepare_resources(self) -> None:
        pass

    @staticmethod
    def underscore_camel_case_split(s: str) -> list[str]:
        return reduce(
            lambda a, b: a + b,
            ([m.group(0).lower() for m in finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', k)] for k in s.split("_")),
        [])

    def to_python_class_name(self, s: str) -> str:
        return "".join((s[0].upper() + ("" if len(s) < 2 else s[1:])) for s in self.underscore_camel_case_split(s))

    def to_python_filename(self, s: str) -> str:
        return "_".join((s for s in self.underscore_camel_case_split(s))) + ".py"

    def prepare_game_resources(self, game_path: str) -> None:
        print(f"Game path is {game_path}")

        def process_file(name: str, copier: Callable[[str, str], None]) -> None:
            if name.startswith("engine") or name.startswith("game"):
                filename = os.path.join(game_path, name)
                path = os.path.dirname(filename)
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                copier(name, filename)

        if self.this_zip_file is not None:
            def zip_file_copier(from_name: str, to_filename: str) -> None:
                with open(to_filename, "wb") as f:
                    with zf.open(from_name) as zff:
                        f.write(zff.read())

            print(f"Opening zipfile {self.this_zip_file}")
            with ZipFile(self.this_zip_file) as zf:
                for name in zf.namelist():
                    process_file(name, zip_file_copier)
        else:
            source_dir = os.path.dirname(os.path.dirname(__file__))
            print(f"Reading files from dir {source_dir}")

            def file_copier(to_filename: str, from_name: str) -> None:
                with open(os.path.join(game_path, to_filename), "wb") as tf:
                    with open(os.path.join(source_dir, to_filename), "rb") as ff:
                        tf.write(ff.read())

            def collect_names(root: str, path: str) -> list[str]:
                r = []
                for name in os.listdir(os.path.join(root, path)):
                    rel_filename = os.path.join(path, name)
                    full_filename = os.path.join(root, rel_filename)
                    if os.path.isdir(full_filename):
                        r += collect_names(root, rel_filename)
                    elif name != "__pycache__" and not name.endswith(".pyc"):
                        r.append(rel_filename)
                return r

            for name in collect_names(source_dir, ""):
                process_file(name, file_copier)

    def process_main_file(self,
                          content: str,
                          context_filename: str, context_class_name: str,
                          map_filename: str,
                          level_name: str,
                          top_down: bool) -> str:
        context_import = "examples.top_down_example_game_context" if top_down else "examples.side_scroller_example_game_context"
        context_class = "TopDownExampleGameContext" if top_down else "SideScrollerExampleGameContext"
        content = (content
                   .replace(context_import, context_filename[:-3])
                   .replace(context_class, context_class_name)
                   .replace("assets/side_scroller/level1.tmx", map_filename)
                   .replace("assets/top_down/test-level.tmx", map_filename)
                   .replace(",\n    \"assets/side_scroller/level2.tmx\"", "")
                   .replace("game_context.set_level(levels[\"test-level\"])", f"game_context.set_level(levels[\"{level_name}\"])")
                   .replace("game_context.set_level(levels[\"level1\"])", f"game_context.set_level(levels[\"{level_name}\"])")
                   .replace("""
# This is needed to ensure examples can be run from the subfolder
if not os.path.exists("engine"):
    os.chdir(os.path.dirname(os.path.abspath(".")))

sys.path.append(os.getcwd())
""", "")
                   )
        return content

    def process_context_file(self, content: str, class_name: str, top_down: bool) -> str:
        content = (content
                   .replace("SideScrollerExampleGameContext", class_name)
                   .replace("TopDownExampleGameContext", class_name)
                   )
        return content

    @staticmethod
    def write_content(filename: str, content: str) -> None:
        with open(filename, "w") as f:
            f.write(content)

    def read_content(self, path: str) -> str:
        if self.this_zip_file is not None:
            with ZipFile(self.this_zip_file) as zf:
                with zf.open(path) as zff:
                    return zff.read().decode("UTF-8")
        else:
            source_dir = os.path.dirname(os.path.dirname(__file__))
            with open(os.path.join(source_dir, path), "r") as f:
                return f.read()
