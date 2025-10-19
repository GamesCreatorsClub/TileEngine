import os.path
from typing import Optional

from pathlib import Path

BACKUPS = 2


def backup_file(filename: str) -> None:
    filename = Path(filename)
    suffix = filename.suffix
    prefix_filename = filename.name[:-len(suffix)]

    if filename.exists():
        last_backup_filename = f"{prefix_filename}.bak{BACKUPS}.{suffix}"
        if os.path.exists(last_backup_filename):
            os.remove(last_backup_filename)
        for i in range(BACKUPS, -1, -1):
            this_filename = f"{prefix_filename}.bak{i}.{suffix}" if i > 0 else f"{prefix_filename}.{suffix}"
            previous_filename = f"{prefix_filename}.{i - 1}.{suffix}" if i > 1 else f"{prefix_filename}.{suffix}"
            if os.path.exists(previous_filename):
                os.rename(previous_filename, this_filename)
