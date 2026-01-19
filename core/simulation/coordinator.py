"""System Coordinator module.

Responsible for wiring subsystems and executing per-phase logic.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SystemCoordinator:
    """
    Coordinates simulation subsystems and executes phase logic.
    """

    def __init__(self):
        # Systems
        self.collision_system: Optional[Any] = None
        self.reproduction_service: Optional[Any] = None
        self.reproduction_system: Optional[Any] = None
        self.poker_system: Optional[Any] = None
        self.lifecycle_system: Optional[Any] = None
        self.poker_proximity_system: Optional[Any] = None
        self.food_spawning_system: Optional[Any] = None

        # Managers (some are systems in disguise)
        self.plant_manager: Optional[Any] = None

        # Phase debugging
        self._phase_hooks: Any = None

    def set_phase_hooks(self, hooks: Any) -> None:
        self._phase_hooks = hooks

    # Phase Executions

    def run_frame_start(
        self, frame_count: int, lifecycle_system: Any, plant_manager: Any, entity_manager: Any
    ) -> None:
        """Execute FRAME_START phase logic."""
        if lifecycle_system:
            lifecycle_system.update(frame_count)

        # Enforce the invariant: at most one Plant per RootSpot
        if plant_manager is not None:
            # We need entities list
            entities = entity_manager.entities_list
            plant_manager.reconcile_plants(entities, frame_count)
            plant_manager.respawn_if_low(entities, frame_count)

    def run_environment(self, ecosystem: Any, env: Any, frame_count: int) -> None:
        """Execute ENVIRONMENT phase logic."""
        if ecosystem is not None:
            ecosystem.update(frame_count)

        if env is not None:
            env.update_detection_modifier()

    def run_spawn(self, food_system: Any, frame_count: int) -> None:
        """Execute SPAWN phase logic."""
        if food_system:
            food_system.update(frame_count)

    def run_collision(self, collision_system: Any, frame_count: int) -> None:
        """Execute COLLISION phase logic."""
        if collision_system:
            collision_system.update(frame_count)

    def run_interaction(
        self, proximity_system: Any, poker_system: Any, frame_count: int, engine_delegate: Any
    ) -> None:
        """Execute INTERACTION phase logic."""
        if proximity_system:
            proximity_system.update(frame_count)

        if poker_system:
            poker_system.update(frame_count)

        # Mixed poker games (fish-plant, etc)
        # Delegate back to engine for now if logic is complex or move logic here
        # engine.handle_mixed_poker_games() just calls poker_system.handle_mixed_poker_games()
        if poker_system:
            poker_system.handle_mixed_poker_games()

    def run_reproduction(
        self, reproduction_system: Any, frame_count: int, phase_hooks: Any, engine: Any
    ) -> None:
        """Execute REPRODUCTION phase logic."""
        if reproduction_system:
            reproduction_system.update(frame_count)

        if phase_hooks:
            phase_hooks.on_reproduction_complete(engine)

    def run_lifecycle(
        self, engine: Any, new_entities: list, entities_to_remove: list, phase_hooks: Any
    ) -> None:
        """Execute LIFECYCLE phase logic."""
        # Request removals
        for entity in entities_to_remove:
            engine.request_remove(entity, reason="entity_act")

        # Mode-specific hooks
        if phase_hooks:
            phase_hooks.on_lifecycle_cleanup(engine)

        # Request spawns
        for new_entity in new_entities:
            engine.request_spawn(new_entity, reason="entity_act")

    def run_entity_act(
        self,
        entity_manager: Any,
        frame_count: int,
        time_modifier: float,
        time_of_day: float,
        phase_hooks: Any,
        engine: Any,
    ) -> tuple[list, list]:
        """Execute ENTITY_ACT phase logic. Returns (new_entities, entities_to_remove)."""
        new_entities = []
        entities_to_remove = []

        entities = list(entity_manager.entities_list)
        for entity in entities:
            # Polymorphic update
            result = entity.update(frame_count, time_modifier, time_of_day)

            # Handle spawns
            if result.spawned_entities:
                for spawned in result.spawned_entities:
                    if phase_hooks:
                        decision = phase_hooks.on_entity_spawned(engine, spawned, entity)
                        if decision.should_add:
                            new_entities.append(decision.entity)
                    else:
                        new_entities.append(spawned)

            # Handle death
            if entity.is_dead():
                should_remove = True
                if phase_hooks:
                    should_remove = phase_hooks.on_entity_died(engine, entity)

                if should_remove:
                    entities_to_remove.append(entity)

            # Constrain
            entity.constrain_to_screen()

        return new_entities, entities_to_remove
