"""System Coordinator — wires subsystems and executes per-phase logic.

Design Decisions:
-----------------
1. The coordinator **owns** references to all subsystems. Phase methods use
   these stored references rather than receiving them as redundant parameters.

2. All system references are Optional — the coordinator gracefully skips
   systems that were not wired by the SystemPack.

3. TYPE_CHECKING imports keep the module lightweight at runtime while
   providing full type information for static analysis and IDE support.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.collision_system import CollisionSystem
    from core.ecosystem import EcosystemManager
    from core.environment import Environment
    from core.plant_manager import PlantManager
    from core.poker_system import PokerSystem
    from core.reproduction_service import ReproductionService
    from core.reproduction_system import ReproductionSystem
    from core.simulation.entity_manager import EntityManager
    from core.simulation.phase_hooks import PhaseHooks
    from core.systems.entity_lifecycle import EntityLifecycleSystem
    from core.systems.food_spawning import FoodSpawningSystem
    from core.systems.poker_proximity import PokerProximitySystem

logger = logging.getLogger(__name__)


class SystemCoordinator:
    """Coordinates simulation subsystems and executes phase logic.

    The coordinator is populated during engine.setup() and then drives
    each phase of the update loop using its stored system references.
    """

    def __init__(self) -> None:
        # Core systems (set by engine.setup via SystemPack)
        self.collision_system: CollisionSystem | None = None
        self.reproduction_service: ReproductionService | None = None
        self.reproduction_system: ReproductionSystem | None = None
        self.poker_system: PokerSystem | None = None
        self.lifecycle_system: EntityLifecycleSystem | None = None
        self.poker_proximity_system: PokerProximitySystem | None = None
        self.food_spawning_system: FoodSpawningSystem | None = None

        # Managers
        self.plant_manager: PlantManager | None = None
        self.ecosystem: EcosystemManager | None = None
        self.environment: Environment | None = None
        self.entity_manager: EntityManager | None = None

        # Phase hooks (mode-specific behavior)
        self._phase_hooks: PhaseHooks | None = None

    def set_phase_hooks(self, hooks: PhaseHooks) -> None:
        """Set the phase hooks for mode-specific entity handling."""
        self._phase_hooks = hooks

    # =========================================================================
    # Phase Executions
    # =========================================================================

    def run_frame_start(self, frame_count: int) -> None:
        """Execute FRAME_START phase logic."""
        if self.lifecycle_system:
            self.lifecycle_system.update(frame_count)

        # Enforce the invariant: at most one Plant per RootSpot
        if self.plant_manager is not None and self.entity_manager is not None:
            entities = self.entity_manager.entities_list
            self.plant_manager.reconcile_plants(entities, frame_count)
            self.plant_manager.respawn_if_low(entities, frame_count)

    def run_environment(self, frame_count: int) -> None:
        """Execute ENVIRONMENT phase logic."""
        if self.ecosystem is not None:
            self.ecosystem.update(frame_count)

        if self.environment is not None:
            self.environment.update_detection_modifier()

    def run_spawn(self, frame_count: int) -> None:
        """Execute SPAWN phase logic."""
        if self.food_spawning_system:
            self.food_spawning_system.update(frame_count)

    def run_collision(self, frame_count: int) -> None:
        """Execute COLLISION phase logic."""
        if self.collision_system:
            self.collision_system.update(frame_count)

    def run_interaction(self, frame_count: int) -> None:
        """Execute INTERACTION phase logic."""
        if self.poker_proximity_system:
            self.poker_proximity_system.update(frame_count)

        if self.poker_system:
            self.poker_system.update(frame_count)
            self.poker_system.handle_mixed_poker_games()

    def run_reproduction(self, frame_count: int) -> None:
        """Execute REPRODUCTION phase logic."""
        if self.reproduction_system:
            self.reproduction_system.update(frame_count)

    def run_lifecycle(
        self,
        engine: Any,
        new_entities: list[Any],
        entities_to_remove: list[Any],
    ) -> None:
        """Execute LIFECYCLE phase logic."""
        # Request removals
        for entity in entities_to_remove:
            engine.request_remove(entity, reason="entity_act")

        # Mode-specific hooks
        if self._phase_hooks:
            self._phase_hooks.on_lifecycle_cleanup(engine)

        # Request spawns
        for new_entity in new_entities:
            engine.request_spawn(new_entity, reason="entity_act")

    def run_entity_act(
        self,
        frame_count: int,
        time_modifier: float,
        time_of_day: float,
        engine: Any,
    ) -> tuple[list[Any], list[Any]]:
        """Execute ENTITY_ACT phase logic. Returns (new_entities, entities_to_remove)."""
        if self.entity_manager is None:
            return [], []

        new_entities: list[Any] = []
        entities_to_remove: list[Any] = []

        entities = list(self.entity_manager.entities_list)
        for entity in entities:
            # Polymorphic update
            result = entity.update(frame_count, time_modifier, time_of_day)

            # Handle spawns
            if result.spawned_entities:
                for spawned in result.spawned_entities:
                    if self._phase_hooks:
                        decision = self._phase_hooks.on_entity_spawned(engine, spawned, entity)
                        if decision.should_add:
                            new_entities.append(decision.entity)
                    else:
                        new_entities.append(spawned)

            # Handle death
            if entity.is_dead():
                should_remove = True
                if self._phase_hooks:
                    should_remove = self._phase_hooks.on_entity_died(engine, entity)

                if should_remove:
                    entities_to_remove.append(entity)

            # Constrain
            entity.constrain_to_screen()

        return new_entities, entities_to_remove
