from typing import Optional

from pygame import Surface

from engine.level import Level, offscreen_rendering
from engine.transitions.level_transition import LevelTransition
from engine.utils import clip


class RenderDirect(LevelTransition):
    def __init__(self, level: Level) -> None:
        super().__init__(level)

    def draw(self, surface: Surface) -> Optional[LevelTransition]:
        with clip(surface, self.level.viewport):
            if self.level.invalidated:
                self.level.invalidated = False
                self.level.offscreen_surface.fill((0, 224, 0))
                self.level.render_to(self.level.offscreen_surface, -self.level.x_offset, -self.level.y_offset)
            surface.blit(self.level.offscreen_surface, self.level.viewport.topleft)
        return None
