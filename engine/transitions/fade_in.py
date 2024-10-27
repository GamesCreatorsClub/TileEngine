from typing import Optional

from pygame import Surface

from engine.level import Level
from engine.transitions.level_transition import LevelTransition
from engine.transitions.render_direct import RenderDirect
from engine.utils import clip


class FadeIn(LevelTransition):
    def __init__(self, level: Level) -> None:
        super().__init__(level)
        self.countdown = 255

    def draw(self, surface: Surface) -> Optional[LevelTransition]:
        with clip(surface, self.level.viewport):
            self.level.offscreen_surface.fill(self.level.background_colour)
            self.level.render_to(self.level.offscreen_surface, -self.level.x_offset, -self.level.y_offset)
            self.level.offscreen_surface.set_alpha(255 - self.countdown)

            surface.blit(self.level.offscreen_surface, self.level.viewport.topleft)
            self.countdown -= 1
            if self.countdown == -1:
                return RenderDirect(self.level)

        return None
