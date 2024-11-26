import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from engine.tmx import TiledMap


class TestLoadAndSave(TestCase):
    def setUp(self) -> None:
        self.project_root = Path(__file__).parent.parent.parent.absolute()

    def test_load_and_save_simple_case(self) -> None:

        with TemporaryDirectory() as t:
            tiled_map = TiledMap()
            tmx_file = str(self.project_root / "assets" / "side_scroller" / "level1.tmx")
            tiled_map.load(tmx_file)

            tiled_map.save(tmx_file + ".1.tmx")
            tiled_map.save(f"{t}/level1.tmx".replace("/", os.sep))
            pass
