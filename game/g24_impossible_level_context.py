from engine.game_context import GameContext, in_context
from engine.level_context import LevelContext


class G24ImpossibleLevelContext(LevelContext):
    def __init__(self, game_context: GameContext) -> None:
        super().__init__()
        self.game_context = game_context

    @in_context
    def add_coins(self, coins: int) -> None:
        print(f"Adding {coins} coin{'s' if coins > 1 else ''}")
        self.game_context.player.coins += coins
