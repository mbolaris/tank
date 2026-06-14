"""Engine assembly - SystemPack-driven setup sequence and validation.

Extracted from SimulationEngine.setup() so the assembly steps live in one
focused module. The numbered step order is behavior-critical (system creation,
coordinator wiring, entity seeding, and the final mutation commit must happen
in exactly this sequence) and must not change.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from core.environment import Environment
from core.simulation.phase_hooks import NoOpPhaseHooks
from core.simulation.pipeline import default_pipeline
from core.update_phases import UpdatePhase

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine
    from core.worlds.system_pack import SystemPack

logger = logging.getLogger(__name__)


def setup_engine(engine: SimulationEngine, pack: SystemPack | None = None) -> None:
    """Set up the simulation engine using the provided SystemPack."""
    # Fallback to TankPack if no pack provided. Deferred on purpose: generic
    # engine assembly must not statically depend on a specific world (Tank).
    if pack is None:
        from core.worlds.tank.pack import TankPack

        pack = TankPack(engine.config)

    # 1. Let the pack build core systems (wiring them into the engine for compatibility)
    systems = pack.build_core_systems(engine)
    for attr, system in systems.items():
        setattr(engine, attr, system)

    # 2. Let the pack build the environment
    engine.environment = cast(Environment, pack.build_environment(engine))

    # Wire up energy delta recorder for immediate tracking
    if engine.environment and hasattr(engine.environment, "set_energy_delta_recorder"):
        engine.environment.set_energy_delta_recorder(engine._create_energy_recorder())

    # 3. Let the pack register systems and contracts
    #    NOTE: register_systems() creates ecosystem, plant_manager, and
    #    food_spawning_system on the engine, so coordinator wiring MUST
    #    happen after this step.
    pack.register_systems(engine)
    pack.register_contracts(engine)
    validate_system_phase_declarations(engine)
    assert_required_systems(engine)

    # 4. Wire ALL systems into coordinator (after register_systems
    #    which creates ecosystem, plant_manager, food_spawning_system)
    engine.coordinator.collision_system = engine.collision_system
    engine.coordinator.reproduction_service = engine.reproduction_service
    engine.coordinator.reproduction_system = engine.reproduction_system
    engine.coordinator.poker_system = engine.poker_system
    engine.coordinator.lifecycle_system = engine.lifecycle_system
    engine.coordinator.poker_proximity_system = engine.poker_proximity_system
    engine.coordinator.food_spawning_system = engine.food_spawning_system
    engine.coordinator.plant_manager = engine.plant_manager
    engine.coordinator.entity_manager = engine.entity_manager
    engine.coordinator.environment = engine.environment
    engine.coordinator.ecosystem = engine.ecosystem

    # 5. Wire up the pipeline (pack can override or use default)
    custom_pipeline = pack.get_pipeline()
    engine.pipeline = custom_pipeline if custom_pipeline is not None else default_pipeline()

    # 6. Let the pack seed entities
    pack.seed_entities(engine)

    # 7. Store identity provider from pack
    engine._identity_provider = pack.get_identity_provider()

    # 8. Store phase hooks from pack
    hooks = pack.get_phase_hooks()
    engine._phase_hooks = hooks if hooks is not None else NoOpPhaseHooks()

    # Update coordinator hooks
    engine.coordinator.set_phase_hooks(engine._phase_hooks)

    # 9. Finalize setup: apply any queued mutations
    engine._apply_entity_mutations("setup_finalize", record_outputs=False)
    if engine.entity_manager.is_dirty:
        engine._rebuild_caches()


def assert_required_systems(engine: SimulationEngine) -> None:
    """Fail fast if core systems were not wired by the SystemPack."""
    required = {
        "lifecycle_system": engine.lifecycle_system,
        "collision_system": engine.collision_system,
        "poker_proximity_system": engine.poker_proximity_system,
        "poker_system": engine.poker_system,
        "reproduction_system": engine.reproduction_system,
    }
    missing = [name for name, system in required.items() if system is None]
    if missing:
        raise AssertionError(f"SystemPack did not initialize required systems: {missing}")


def validate_system_phase_declarations(engine: SimulationEngine) -> None:
    """Verify phase metadata matches the explicit phase loop."""
    phase_map: dict[UpdatePhase, list[Any]] = {
        UpdatePhase.FRAME_START: [engine.lifecycle_system],
        UpdatePhase.TIME_UPDATE: [engine.time_system],
        UpdatePhase.SPAWN: [engine.food_spawning_system],
        UpdatePhase.COLLISION: [engine.collision_system],
        UpdatePhase.INTERACTION: [engine.poker_proximity_system, engine.poker_system],
        UpdatePhase.REPRODUCTION: [engine.reproduction_system],
    }

    executed_systems = set()
    for phase, systems in phase_map.items():
        for system in systems:
            if system is None:
                continue
            executed_systems.add(system)
            declared_phase = system.phase
            if declared_phase is None:
                continue
            if declared_phase != phase:
                logger.warning(
                    "System %s declares phase %s but runs in %s",
                    system.name,
                    declared_phase.name,
                    phase.name,
                )

    for system in engine.get_systems():
        declared_phase = system.phase
        if declared_phase is None:
            continue
        if system not in executed_systems:
            logger.warning(
                "System %s declares phase %s but is not scheduled in the explicit phase loop",
                system.name,
                declared_phase.name,
            )
