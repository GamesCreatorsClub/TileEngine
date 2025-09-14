import os.path


BACKUPS = 2


def backup_file(filename: str) -> None:
    i = filename.rfind(".")

    prefix_filename = filename[:i]
    suffix = filename[i + 1:]

    if os.path.exists(filename):
        for i in range(BACKUPS, -1, -1):
            this_filename = f"{prefix_filename}.{i}.{suffix}" if i > 0 else f"{prefix_filename}.{suffix}"
            previous_filename = f"{prefix_filename}.{i - 1}.{suffix}" if i > 1 else f"{prefix_filename}.{suffix}"
            if os.path.exists(previous_filename):
                os.rename(previous_filename, this_filename)
