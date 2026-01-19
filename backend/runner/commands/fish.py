import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from core import entities, movement_strategy
from core.config.display import FILES, SCREEN_HEIGHT, SCREEN_WIDTH
from core.config.ecosystem import SPAWN_MARGIN_PIXELS
from core.genetics import Genome

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


class FishCommands:
    def _cmd_spawn_fish(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'spawn_fish' command."""
        try:
            logger.info("Spawn fish command received")
            rng = self.world.rng
            if rng is None:
                return self._create_error_response("RNG not available")

            # Random spawn position (avoid edges)
            x = rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS)
            y = rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS)

            logger.info(f"Creating fish at position ({x}, {y})")

            # Create new fish with random genome
            environment = getattr(self.world, "environment", None)
            genome = Genome.random(use_algorithm=True, rng=rng)
            new_fish = entities.Fish(
                environment,
                movement_strategy.AlgorithmicMovement(),
                FILES["schooling_fish"][0],
                x,
                y,
                4,  # Base speed
                genome=genome,
                generation=0,
                ecosystem=getattr(self.world, "ecosystem", None),
            )
            self.world.add_entity(new_fish)
            new_fish.register_birth()  # Record in lineage tracker
            self._invalidate_state_cache()
        except Exception as e:
            logger.error(f"Error spawning fish: {e}")
        return None
