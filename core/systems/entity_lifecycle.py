"""Entity lifecycle management system.

This module handles entity birth, death, and lifecycle transitions.
It centralizes lifecycle logic that was previously scattered throughout
the simulation engine.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Manages entity death processing and cleanup
- Handles food expiration and removal
- Coordinates emergency fish spawning
- Emits lifecycle events (when event bus is wired)
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

from core.systems.base import BaseSystem

if TYPE_CHECKING:
    from core.entities import Agent, Food
    from core.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)


class EntityLifecycleSystem(BaseSystem):
    """Manages entity lifecycle events including births, deaths, and cleanup.

    This system consolidates lifecycle management logic:
    - Processing entity deaths with proper cleanup
    - Removing expired/consumed food
    - Emergency fish spawning when population is critical
    - Tracking lifecycle statistics

    Attributes:
        _deaths_this_frame: Count of deaths in current frame
        _births_this_frame: Count of births in current frame
        _total_deaths: Total deaths processed
        _total_births: Total births processed
        _emergency_spawns: Count of emergency fish spawns
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the entity lifecycle system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "EntityLifecycle")
        self._deaths_this_frame: int = 0
        self._births_this_frame: int = 0
        self._total_deaths: int = 0
        self._total_births: int = 0
        self._emergency_spawns: int = 0
        self._food_removed: int = 0
        self._plants_died: int = 0

    def _do_update(self, frame: int) -> None:
        """Reset per-frame counters at start of each frame.

        The actual lifecycle processing is done via explicit method calls
        from SimulationEngine to maintain control over execution order.

        Args:
            frame: Current simulation frame number
        """
        # Reset per-frame counters
        self._deaths_this_frame = 0
        self._births_this_frame = 0

    def process_entity_death(self, entity: "Agent") -> bool:
        """Process an entity's death with proper cleanup.

        Handles different entity types appropriately:
        - Fish: Records death in ecosystem, removes from simulation
        - FractalPlant: Releases root spot, removes from simulation
        - PlantNectar: Simply removes from simulation
        - Food: Returns to pool if applicable, removes from simulation

        Args:
            entity: The entity that died

        Returns:
            True if entity was processed and removed, False otherwise
        """
        from core.entities import Fish, Food
        from core.entities.fractal_plant import FractalPlant, PlantNectar

        if isinstance(entity, Fish):
            self._engine.record_fish_death(entity)
            self._deaths_this_frame += 1
            self._total_deaths += 1
            return True

        elif isinstance(entity, FractalPlant):
            entity.die()  # Release root spot
            self._engine.remove_entity(entity)
            self._deaths_this_frame += 1
            self._total_deaths += 1
            self._plants_died += 1
            logger.debug(f"FractalPlant #{entity.plant_id} died at age {entity.age}")
            return True

        elif isinstance(entity, PlantNectar):
            self._engine.remove_entity(entity)
            return True

        elif isinstance(entity, Food):
            self._engine.remove_entity(entity)
            self._food_removed += 1
            return True

        return False

    def process_food_removal(
        self,
        entity: "Food",
        screen_height: int,
    ) -> bool:
        """Check if food should be removed and process removal.

        Handles:
        - LiveFood expiration
        - Regular food sinking off screen

        Args:
            entity: The food entity to check
            screen_height: Screen height for boundary check

        Returns:
            True if food was removed, False otherwise
        """
        from core.entities import LiveFood

        if isinstance(entity, LiveFood):
            if entity.is_expired():
                self._engine.remove_entity(entity)
                self._food_removed += 1
                return True
        else:
            # Standard food sinks off bottom
            if entity.pos.y >= screen_height - entity.height:
                self._engine.remove_entity(entity)
                self._food_removed += 1
                return True

        return False

    def record_birth(self) -> None:
        """Record that a birth occurred this frame."""
        self._births_this_frame += 1
        self._total_births += 1

    def record_emergency_spawn(self) -> None:
        """Record that an emergency spawn occurred."""
        self._emergency_spawns += 1
        self._births_this_frame += 1
        self._total_births += 1

    def get_debug_info(self) -> Dict[str, Any]:
        """Return lifecycle statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "deaths_this_frame": self._deaths_this_frame,
            "births_this_frame": self._births_this_frame,
            "total_deaths": self._total_deaths,
            "total_births": self._total_births,
            "emergency_spawns": self._emergency_spawns,
            "food_removed": self._food_removed,
            "plants_died": self._plants_died,
            "net_population_change": self._total_births - self._total_deaths,
        }
