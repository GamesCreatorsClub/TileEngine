from typing import Optional

import os

import pygame
from pygame import Rect

from editor.info_panel import InfoPanel
from editor.map_controller import MapController
from editor.mini_map_controller import MiniMap
from editor.pygame_components import ComponentCollection, UISize, Divider
from editor.tileset_controller import TilesetActionsPanel, TilesetController
from editor.toolbar_panel import ToolbarPanel


class MainWindow(ComponentCollection):
    def __init__(self, rect: Rect) -> None:
        super().__init__(rect)

        self.icon_surface = pygame.image.load(os.path.join(os.path.dirname(__file__), "icons.png"))

        self.toolbar = ToolbarPanel(Rect(0, 0, 0, 0), icon_surface=self.icon_surface)
        self.divider = Divider(Rect(0, 0, 0, 0), False, self)
        self.tileset_controller: Optional[TilesetController] = None
        self.tileset_actions_toolbar: Optional[TilesetActionsPanel] = None
        self.mini_map: Optional[MiniMap] = None
        self.info_panel: Optional[InfoPanel] = None
        self.map_controller: Optional[MapController] = None

    def finish_initialisation(self) -> None:
        self.components += [
            self.toolbar, self.map_controller, self.divider, self.mini_map, self.info_panel, self.tileset_controller, self.tileset_actions_toolbar
        ]
        self.divider.rect.update(self.rect.right - 300, self.rect.y + self.toolbar.rect.height, 5, self.rect.height - self.toolbar.rect.height)
        self.divider.redefine_rect(self.divider.rect)
        self.relayout()

    def calculate_size(self) -> UISize:
        return self.rect.size

    def redefine_rect(self, rect: Rect) -> None:
        divider_from_left = self.rect.right - self.divider.rect.x
        self.divider.rect.x = rect.right - divider_from_left
        self.divider.redefine_rect(self.divider.rect)
        self.rect = rect
        self.relayout()

    def relayout(self) -> None:
        left_column_width = self.divider.rect.x - self.rect.x
        right_column_x = self.divider.rect.right
        right_column_width = self.rect.right - self.divider.rect.right
        mini_map_height = self.rect.height * 2 // 6

        self.toolbar.relayout()
        toolbar_height = self.toolbar.rect.height

        self.map_controller.redefine_rect(Rect(self.rect.x, toolbar_height, left_column_width, self.rect.height - toolbar_height))
        self.mini_map.redefine_rect(Rect(right_column_x, toolbar_height, right_column_width, mini_map_height))
        self.info_panel.redefine_rect(Rect(right_column_x, self.mini_map.rect.bottom + 2, right_column_width, self.info_panel.font.get_height() * 2))
        self.tileset_actions_toolbar.redefine_rect(Rect(right_column_x, self.rect.bottom - 32 - 20, right_column_width, 32))
        self.tileset_controller.redefine_rect(Rect(right_column_x, self.info_panel.rect.bottom + 10, right_column_width, self.tileset_actions_toolbar.rect.top - 10 - self.info_panel.rect.bottom - 10))
