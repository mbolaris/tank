"""Entity lifecycle management system.

This module handles entity birth, death, and lifecycle transitions.
It is the SINGLE OWNER of entity removal logic in the simulation.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.FRAME_START to reset per-frame counters
- OWNS ALL entity removal decisions:
  - Fish death processing (with death animation delay)
  - Plant death and root spot release
  - Food removal (expiry for LiveFood, off-screen for regular food)
  - PlantNectar removal
- Tracks lifecycle statistics (births, deaths, food removed)

Design Decision: Single Owner of Removal Logic
----------------------------------------------
Previously, entity removal logic was duplicated between:
1. SimulationEngine._phase_entity_act() - inline checks
2. EntityLifecycleSystem.process_food_removal() - method

This violated DRY and created heisenbug potential (double removals,
stats miscounts, events not fired consistently). Now ALL removal rules
live here, and the engine simply calls this system's methods.

To add new removal rules: Add a method here, call from _phase_lifecycle.
Do NOT add inline removal logic in SimulationEngine.

Removal requests are queued through the engine mutation queue and applied
between phases to prevent mid-iteration mutations.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.systems.base import BaseSystem
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Agent, Food
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@runs_in_phase(UpdatePhase.FRAME_START)
class EntityLifecycleSystem(BaseSystem):
    """Single owner of entity removal logic and lifecycle tracking.

    This system runs in the FRAME_START phase and is the authoritative source
    for all entity removal decisions:
    - Fish death (with animation delay before removal)
    - Plant death (releases root spot)
    - Food removal (LiveFood expiry, regular food off-screen)
    - PlantNectar removal

    Also tracks lifecycle statistics (births, deaths, food removed).

    Note: The system resets per-frame counters at FRAME_START via _do_update(),
    which is called by the engine at the start of each frame.

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
        - Plant: Releases root spot, removes from simulation
        - PlantNectar: Simply removes from simulation
        - Food: Returns to pool if applicable, removes from simulation

        Args:
            entity: The entity that died

        Returns:
            True if entity was processed and removed, False otherwise
        """
        from core.entities import Fish, Food
        from core.entities.plant import Plant, PlantNectar

        if isinstance(entity, Fish):
            # record_fish_death handles all stats tracking internally
            self.record_fish_death(entity)
            return True

        elif isinstance(entity, Plant):
            entity.die()  # Release root spot
            self._engine.request_remove(entity, reason="plant_death")
            self._deaths_this_frame += 1
            self._total_deaths += 1
            self._plants_died += 1
            logger.debug(f"Plant #{entity.plant_id} died at age {entity.age}")
            return True

        elif isinstance(entity, PlantNectar):
            self._engine.request_remove(entity, reason="plant_nectar_expired")
            return True

        elif isinstance(entity, Food):
            self._engine.request_remove(entity, reason="food_removed")
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
                self._engine.request_remove(entity, reason="food_expired")
                self._food_removed += 1
                return True
        else:
            # Standard food sinks off bottom
            if entity.pos.y >= screen_height - entity.height:
                self._engine.request_remove(entity, reason="food_offscreen")
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

    def record_fish_death(self, fish: "Agent", cause: Optional[str] = None) -> None:
        """Record a fish death in the ecosystem and mark for delayed removal.

        The fish remains in the simulation briefly so its death effect icon
        can be rendered before removal. The actual removal happens in
        cleanup_dying_fish() once death_effect_timer expires.

        Args:
            fish: The fish that died
            cause: Optional death cause override (defaults to fish.get_death_cause())
        """
        # Skip if already recorded as dying (prevent double-recording)
        if fish.visual_state.death_effect_state is not None:
            return

        death_cause = cause if cause is not None else fish.get_death_cause()

        # Set death effect for visual indicator on frontend (45 frames = 1.5s at 30fps)
        fish.set_death_effect(death_cause, duration=45)

        self._deaths_this_frame += 1
        self._total_deaths += 1

        ecosystem = self._engine.ecosystem
        if ecosystem is not None:
            algorithm_id = None
            composable = fish.genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                behavior_id = composable.value.behavior_id
                algorithm_id = hash(behavior_id) % 1000

            # Track ALL energy lost when fish dies (including banked overflow)
            total_energy_lost = fish.energy + fish._reproduction_component.overflow_energy_bank
            ecosystem.record_death(
                fish.fish_id,
                fish.generation,
                fish._lifecycle_component.age,
                death_cause,
                fish.genome,
                algorithm_id=algorithm_id,
                remaining_energy=total_energy_lost,
            )

        # NOTE: EntityDiedEvent emission was removed - nothing subscribed to it.
        # Re-add when we have actual consumers for death events.

        # Don't remove fish yet - stay in simulation for death effect to render
        # Cleanup happens in cleanup_dying_fish() when death_effect_timer expires

    def cleanup_dying_fish(self) -> None:
        """Remove fish whose death effect timer has expired.

        Called each frame to clean up fish that have finished showing
        their death animation.
        """
        from core.entities import Fish

        to_remove = []
        for entity in self._engine.get_all_entities():
            if isinstance(entity, Fish) and entity.visual_state.death_effect_state is not None:
                # If timer expired, mark for removal
                if entity.visual_state.death_effect_timer <= 0:
                    to_remove.append(entity)

        for fish in to_remove:
            self._engine.request_remove(fish, reason="death_effect_complete")

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
