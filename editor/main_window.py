from typing import Optional

import os

import pygame
from pygame import Rect

from editor.map_controller import MapController
from editor.pygame_components import ComponentCollection, UISize
from editor.tileset_controller import TilesetActionsPanel, TilesetController
from editor.toolbar_panel import ToolbarPanel


class MainWindow(ComponentCollection):
    def __init__(self, rect: Rect) -> None:
        super().__init__(rect)

        self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "icons.png"))

        self.toolbar = ToolbarPanel(Rect(0, 0, 0, 0), icon_surface=self.icon_surface)
        self.tileset_controller: Optional[TilesetController] = None
        self.tileset_actions_toolbar: Optional[TilesetActionsPanel] = None
        self.map_controller: Optional[MapController] = None

    def finish_initialisation(self) -> None:
        self.components += [
            self.toolbar, self.map_controller, self.tileset_controller, self.tileset_actions_toolbar
        ]
        self.relayout()

    def calculate_size(self) -> UISize:
        return self.rect.size

    def redefine_rect(self, rect: Rect) -> None:
        self.rect = rect
        self.relayout()

    def relayout(self) -> None:
        right_column = self.rect.width - 300

        self.toolbar.relayout()
        toolbar_height = self.toolbar.rect.height

        self.map_controller.redefine_rect(Rect(0, toolbar_height, right_column, self.rect.height - toolbar_height))
        self.tileset_actions_toolbar.redefine_rect(Rect(right_column, self.rect.bottom - 32 - 20, 300, 32))
        self.tileset_controller.redefine_rect(Rect(right_column, self.tileset_actions_toolbar.rect.top - 10 - 500, 300, 500))
