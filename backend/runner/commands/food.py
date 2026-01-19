from typing import TYPE_CHECKING, Any, Dict, Optional

from core import entities
from core.config.display import SCREEN_WIDTH

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner


class FoodCommands:
    def _cmd_add_food(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'add_food' command."""
        rng = self.world.rng
        if rng is None:
            return self._create_error_response("RNG not available")

        x = rng.randint(0, SCREEN_WIDTH)
        environment = getattr(self.world, "environment", None)
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
