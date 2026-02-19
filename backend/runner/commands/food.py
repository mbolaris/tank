from typing import TYPE_CHECKING, Any

from core import entities
from core.config.display import SCREEN_WIDTH

if TYPE_CHECKING:
    pass


class FoodCommands:
    if TYPE_CHECKING:
        world: Any

        def _create_error_response(self, error_msg: str) -> dict[str, Any]: ...

        def _invalidate_state_cache(self) -> None: ...

    def _cmd_add_food(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'add_food' command."""
        rng = self.world.rng
        if rng is None:
            return self._create_error_response("RNG not available")

        x = rng.randint(0, SCREEN_WIDTH)
        environment = getattr(self.world, "environment", None)
        if environment is None:
            return self._create_error_response("Environment not available")
        food = entities.Food(
            environment,
            x,
            0,
            source_plant=None,
            allow_stationary_types=False,
        )
        food.pos.y = 0
        self.world.add_entity(food)
        self._invalidate_state_cache()
        return None
