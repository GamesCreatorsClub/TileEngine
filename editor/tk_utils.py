import time

import tkinter as tk
import traceback

from typing import Optional, Union, Callable, Any


def bindtag(parent: tk.Widget, widget: tk.Widget, name: Optional[str] = None) -> tk.Widget:
    if name is not None:
        widget.bindtags((widget, name, parent, ".", "all"))
    else:
        widget.bindtags((widget, parent, ".", "all"))
    return widget


def pack(tk: tk.Widget, **kwargs) -> tk.Widget:
    tk.pack(**kwargs)
    return tk


last_exception_time = 0
last_exception: Optional[BaseException] = 0
exception_count = 0


def handle_exception_tk(target: Callable) -> Callable:
    def wrapper(*args, **kwargs) -> Any:
        global exception_count, last_exception, last_exception_time
        try:
            result = target(*args, **kwargs)
            last_exception = None
            return result
        except BaseException as e:
            display_exception = True
            if str(e) == str(last_exception) and last_exception_time + 5 > time.time():
                exception_count += 1
                display_exception = exception_count % 100 == 0
            else:
                exception_count = 0
            last_exception = e
            last_exception_time = time.time()
            if display_exception:
                # TODO add appropriate pop-up here.
                print(f"*** Caught exception {e}{(' (' + str(exception_count) + ')') if exception_count > 0 else ''};\n stacktrace: {traceback.format_tb(e.__traceback__)}")

    return wrapper
