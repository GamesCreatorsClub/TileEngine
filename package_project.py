#!/usr/bin/env python3
import base64
################################################################################
# Copyright (C) 2020 Abstract Horizon
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License v2.0
# which accompanies this distribution, and is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
#  Contributors:
#    Daniel Sendula - initial API and implementation
#
#################################################################################

import datetime
import glob
import os
from os.path import join
from zipfile import ZipFile, ZIP_DEFLATED


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

SOURCE_PATHS = [
    (join(CURRENT_PATH, "editor.py"), "__main__.py"),
    (join(CURRENT_PATH, "editor"), ("editor")),
    (join(CURRENT_PATH, "engine"), ("engine")),
    (join(CURRENT_PATH, "game"), ("game")),
    (join(CURRENT_PATH, "assets"), "assets"),
    (join(CURRENT_PATH, "examples"), "examples")
]

RESULT_NAME = "tile_editor"  # CHANGE: your project name - name of resulting executable
MAIN_FILE = "__main__"  # CHANGE: Main python file without '.py' suffix (that will be invoked)

REQUIREMENTS_FILE = join(CURRENT_PATH, "requirements.txt")  # Requirements file to package with your source (no need to change)

TARGET_PATH = join(CURRENT_PATH, "target")  # working directory (no need to change)
TARGET_REQUIREMENTS_PATH = join(TARGET_PATH, "requirements")  # dir where install dependencies before being packaged (no need to change)
TARGET_TEMPLATES_PATH = join(TARGET_PATH, "templates")  # dir where templated files are going to be stored before being packaged (no need to change)
VERSION_FILE = join(CURRENT_PATH, "VERSION")  # version file (no need to change)

# Version file here is just for your convenience. Check below what you can comment out if you don't want to maintain version


def ensure_empty_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

    def del_recursively(path_to_delete):
        for file in os.listdir(path_to_delete):
            new_path = os.path.join(path_to_delete, file)
            try:
                if os.path.isdir(new_path):
                    del_recursively(new_path)
                    os.rmdir(new_path)
                else:
                    os.remove(new_path)
            except IOError:
                pass

    del_recursively(path)

    return path


EXCLUDE_FILES = [".DS_Store", "__pycache__"]


def list_all_paths(dir_name):
    result = []

    def collect_files(path):
        for filename in os.listdir(str(os.path.join(dir_name, path))):
            if filename not in EXCLUDE_FILES:
                if os.path.isdir(os.path.join(dir_name, path, filename)):
                    collect_files(os.path.join(path, filename))
                else:
                    result.append((os.path.join(dir_name, path, filename), os.path.join(path, filename)))

    collect_files("")

    return result


def install_requirements(requirements_file, target_directory):
    print(f"Attempting to install requirements from '{requirements_file}' in '{target_directory}")
    os.system(f"pip install -r '{glob.glob(requirements_file)[0]}' --target '{target_directory}'")


def update_build_version(version_file, target_templates_path):
    if os.path.exists(version_file):
        ensure_empty_dir(target_templates_path)
        with open(version_file, 'r') as in_file:
            lines = in_file.readlines()
            lines[0] = lines[0] + datetime.datetime.now().strftime('-%Y%m%d%H%M%S')
            with open(os.path.join(target_templates_path, os.path.split(version_file)[1]), 'w') as out_file:
                out_file.write("\n".join(lines) + "\n")


def create_zipfile(zip_file, source_paths, *other_paths):
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zip_file:
        for source_path in source_paths:
            if os.path.isdir(source_path[0]):
                for source_file, result_file in list_all_paths(source_path[0]):
                    zip_file.write(source_file, str(os.path.join(source_path[1], result_file)))
            else:
                zip_file.write(source_path[0], source_path[1])

        for path in other_paths:
            for source_file, result_file in list_all_paths(path):
                zip_file.write(source_file, result_file)

    return zip_file


START_SCRIPT = f"""#!/bin/bash

export SCRIPT_FILE=`which "$0" 2>/dev/null`

source=`cat <<EOF
import sys
import os
import runpy

sys.argv[0] = os.environ['SCRIPT_FILE']
sys.path.insert(0, sys.argv[0])

print(f"Running module run_editor.py")
runpy.run_module("run_editor.py", run_name="run_editor.py")
EOF`

/usr/bin/env python3 -u -c "${{source}}" $@
exit $?
"""

START_PYTHON_1 = """#!/bin/bash
import base64
import sys
import os
import runpy

CHUNK_SIZE = 10240

print(f"In main file - starting editor now")

"""

START_PYTHON_2 = """

if __name__ == "__main__":
    this_path = os.path.dirname(__file__)
    temp_path = os.path.join(this_path, "temp")
    if not os.path.exists(temp_path):
        os.makedirs(temp_path, exist_ok=True)
    zip_file_path = os.path.join(temp_path, "editor.zip")

    with open(zip_file_path, "wb") as zip_file:
        for chunk in zip_file_base64:
            encoded = base64.b64decode(chunk)
            zip_file.write(encoded)

    sys.path.insert(0, zip_file_path)
    print(f"sys.path={sys.path}")
    # runpy.run_module("editor")

    from editor.main_editor import start
    start()

print(f"Finished...")

"""

if __name__ == "__main__":

    ensure_empty_dir(TARGET_PATH)
    ensure_empty_dir(TARGET_REQUIREMENTS_PATH)

    zip_file = os.path.join(TARGET_PATH, "out.zip")
    result_executable = os.path.join(TARGET_PATH, RESULT_NAME)

    update_build_version(VERSION_FILE, TARGET_TEMPLATES_PATH)
    create_zipfile(zip_file, SOURCE_PATHS, TARGET_REQUIREMENTS_PATH, TARGET_TEMPLATES_PATH)

    with open(result_executable + ".zip", "wb") as f:
        with open(zip_file, "rb") as zf:
            f.write(zf.read())

    BUFFER_SIZE = 10240

    with open(result_executable + ".py", "w") as f:
        f.write(START_PYTHON_1)
        f.write("zip_file_base64 = [\n")
        with open(zip_file, "rb") as zf:
            total_read = 0
            total_written = 0
            buf = zf.read(BUFFER_SIZE)
            while len(buf) == BUFFER_SIZE:
                encoded = base64.b64encode(buf).decode("utf-8")
                total_read += len(buf)
                total_written += len(encoded)
                f.write("    \"\"\"")
                f.write(encoded)
                f.write("\"\"\",\n")
                buf = zf.read(BUFFER_SIZE)
            total_read += len(buf)
            total_written += len(encoded)
            encoded = base64.b64encode(buf).decode("utf-8")
            f.write("    \"\"\"")
            f.write(encoded)
            f.write("\"\"\"\n")
            print(f"Total read {total_read} and written {total_written}")
        f.write("]\n")
        f.write(START_PYTHON_2)
        f.write("\n# EOF\n")

    os.system(f"chmod u+x '{result_executable}'")
