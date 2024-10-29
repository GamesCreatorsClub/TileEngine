from typing import Optional

import pygame
from pygame import Surface, Rect

from engine.level import Level
from engine.transitions.level_transition import LevelTransition
from engine.transitions.render_direct import RenderDirect
from engine.utils import clip


class MoveViewport(LevelTransition):
    def __init__(self, level: Level, new_pos: Rect, frames: int) -> None:
        super().__init__(level)
        self.start_post = level.viewport.copy()
        self.end_pos = new_pos
        self.total_frames = frames
        self.current_frame = 0
        mx = max(new_pos.width, self.start_post.width)
        my = max(new_pos.height, self.start_post.height)
        current_size = self.level.offscreen_surface.get_size()
        if current_size[0] < mx or current_size[1] < my:
            self.level.invalidated = True
            self.level.offscreen_surface = Surface((mx, my), pygame.HWSURFACE).convert_alpha()

    def draw(self, surface: Surface) -> Optional[LevelTransition]:
        self.current_frame += 1

        sx = self.start_post.x
        ex = self.end_pos.x
        sy = self.start_post.y
        ey = self.end_pos.y
        sw = self.start_post.width
        ew = self.end_pos.width
        sh = self.start_post.height
        eh = self.end_pos.height
        f = self.current_frame / self.total_frames

        new_width = sw + (ew - sw) * f
        new_height = sh + (eh - sh) * f

        # resized = self.level.viewport.width != new_width or self.level.viewport.height != new_height

        self.level.viewport.x = sx + (ex - sx) * f
        self.level.viewport.y = sy + (ey - sy) * f
        self.level.viewport.width = new_width
        self.level.viewport.height = new_height

        with clip(surface, self.level.viewport):
            # if resized:
            #     self.level.invalidated = True
            #     self.level.offscreen_surface = Surface(self.level.viewport.size, pygame.HWSURFACE).convert_alpha()

            if self.level.always or self.level.invalidated:
                self.level.invalidated = False
                self.level.offscreen_surface.fill(self.level.background_colour)
                self.level.render_to(self.level.offscreen_surface, -self.level.x_offset, -self.level.y_offset)

            surface.blit(self.level.offscreen_surface, self.level.viewport.topleft)

        return RenderDirect(self.level) if self.current_frame == self.total_frames else None
