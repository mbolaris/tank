"""Phase hooks for Fish/Plant/Food entity handling in Tank-like worlds.

This module extracts the Tank-like entity handling logic that was previously
embedded in SimulationEngine phase methods. By moving this logic into hooks,
new modes like Soccer can provide their own entity handling without modifying
engine code.

This provider is shared between Tank and Petri modes. It lives in the shared
namespace to avoid coupling Petri to Tank.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.simulation.phase_hooks import PhaseHooks, SpawnDecision

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


class FishPlantPhaseHooks(PhaseHooks):
    """Phase behavior for Fish/Plant/Food entities in Tank-like worlds.

    This class contains the logic that was previously in SimulationEngine
    phase methods. It handles:
    - Fish spawn population checks
    - Fish/Plant/PlantNectar death handling
    - Food expiry and off-screen removal
    - Fish population and energy stats
    - Poker benchmark evaluation
    """

    def on_entity_spawned(
        self,
        engine: "SimulationEngine",
        spawned_entity: Any,
        parent_entity: Any,
    ) -> SpawnDecision:
        """Handle Fish spawn population checks.

        For Fish entities, checks ecosystem population limits before allowing spawn.
        Non-Fish entities are always accepted.
        """
        from core.entities import Fish

        if isinstance(spawned_entity, Fish):
            ecosystem = engine.ecosystem
            if ecosystem is None:
                return SpawnDecision(should_add=False, entity=spawned_entity, reason="no_ecosystem")

            fish_count = len(engine.get_fish_list())
            if not ecosystem.can_reproduce(fish_count):
                return SpawnDecision(
                    should_add=False, entity=spawned_entity, reason="population_limit"
                )

            # Register birth for accepted fish
            spawned_entity.register_birth()
            engine.lifecycle_system.record_birth()

            return SpawnDecision(should_add=True, entity=spawned_entity, reason="fish_accepted")

        # Non-Fish entities are always accepted
        return SpawnDecision(should_add=True, entity=spawned_entity, reason="non_fish")

    def on_entity_died(
        self,
        engine: "SimulationEngine",
        entity: Any,
    ) -> bool:
        """Handle Fish/Plant/PlantNectar death.

        - Fish: Record death via lifecycle system (handles death animation)
        - Plant: Call die() and queue for removal
        - PlantNectar: Queue for removal

        Returns True if entity should be added to removal list.
        """
        from core.entities import Fish
        from core.entities.plant import Plant, PlantNectar

        if isinstance(entity, Fish):
            # Fish death is recorded but entity is not immediately removed
            # (death animation plays first, cleanup happens in lifecycle phase)
            engine.record_fish_death(entity)
            return False  # Don't add to removal list yet

        elif isinstance(entity, Plant):
            entity.die()
            logger.debug(f"Plant #{entity.plant_id} died at age {entity.age}")
            return True  # Add to removal list

        elif isinstance(entity, PlantNectar):
            return True  # Add to removal list

        # Unknown entity types: default to no removal
        return False

    def on_lifecycle_cleanup(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Handle Food expiry and dying fish cleanup.

        - Checks Food entities for expiry/off-screen and queues removal
        - Cleans up fish that finished their death animation
        """
        from core.entities import Food

        screen_height = engine.config.display.screen_height

        for entity in list(engine._entity_manager.entities_list):
            if isinstance(entity, Food):
                engine.lifecycle_system.process_food_removal(entity, screen_height)

        # Cleanup fish that finished their death animation
        engine.cleanup_dying_fish()

    def on_reproduction_complete(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Record fish population and energy stats.

        Called after reproduction phase to update ecosystem statistics.
        """
        ecosystem = engine.ecosystem
        if ecosystem is None:
            return

        fish_list = engine.get_fish_list()

        # Delegate stats recording to EcosystemManager
        ecosystem.update_population_stats(fish_list)

        # Periodic cleanup of dead fish records
        if engine.frame_count % 1000 == 0:
            alive_ids = {f.fish_id for f in fish_list}
            ecosystem.cleanup_dead_fish(alive_ids)

        # Record energy snapshot for delta calculations
        total_fish_energy = sum(
            f.energy + f._reproduction_component.overflow_energy_bank for f in fish_list
        )
        ecosystem.record_energy_snapshot(total_fish_energy, len(fish_list))

    def on_frame_end(
        self,
        engine: "SimulationEngine",
    ) -> None:
        """Run poker benchmarks if enabled.

        Called at end of frame to optionally run benchmark evaluation.
        """
        if engine.benchmark_evaluator is not None:
            fish_list = engine.get_fish_list()
            engine.benchmark_evaluator.maybe_run(engine.frame_count, fish_list)


# Backward-compatible alias
TankPhaseHooks = FishPlantPhaseHooks
