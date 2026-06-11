"""World-type hot-swapping and migration-context wiring.

Extracted from SimulationRunner verbatim. The runner keeps thin
``switch_world_type()`` / ``_update_environment_migration_context()`` facades
that delegate here so the public API and test monkeypatch points are
unchanged. The switch happens entirely under ``runner.lock``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from backend.world_registry import get_world_metadata
from core.worlds.interfaces import MultiAgentWorldBackend

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


def switch_world_type(runner: SimulationRunner, new_world_type: str) -> None:
    """Switch to a different world type while preserving entities.

    This hot-swaps between tank and petri modes without resetting the
    simulation. Both modes share the same underlying engine, so we
    wrap/unwrap the adapter and update metadata - never reset.

    Args:
        runner: The SimulationRunner instance
        new_world_type: Target world type ("tank" or "petri")

    Raises:
        ValueError: If switching between incompatible world types
    """
    from backend.runner.world_hooks import get_hooks_for_world

    with runner.lock:
        if new_world_type == runner.world_type:
            return

        # Only tank <-> petri switching is supported (they share the same engine)
        if {runner.world_type, new_world_type} != {"tank", "petri"}:
            raise ValueError(
                f"Cannot hot-swap between {runner.world_type} and {new_world_type}. "
                f"Only tank <-> petri switching is supported."
            )

        was_paused = runner.world.is_paused

        # Capture old world type BEFORE any mutation for correct hook sequencing
        old_world_type = runner.world_type
        old_hooks = runner.world_hooks

        logger.info(
            "Hot-swapping world type from %s to %s (preserving entities)",
            old_world_type,
            new_world_type,
        )

        # Get the underlying tank backend (the "base" backend)
        from core.worlds.petri.backend import PetriWorldBackendAdapter

        tank_backend: MultiAgentWorldBackend
        if isinstance(runner.world, PetriWorldBackendAdapter):
            tank_backend = runner.world._tank_backend
        else:
            tank_backend = runner.world

        # 1) Cleanup OLD physics/resources using current hooks BEFORE switching
        cleanup_physics = getattr(old_hooks, "cleanup_physics", None)
        if callable(cleanup_physics):
            cleanup_physics(runner)

        cleanup = getattr(old_hooks, "cleanup", None)
        if callable(cleanup):
            cleanup(runner)

        # 2) Swap the world backend (preserve underlying engine/entities)
        new_world: MultiAgentWorldBackend
        if new_world_type == "petri":
            new_world = PetriWorldBackendAdapter(tank_backend=cast(Any, tank_backend))
        else:
            # Switching to tank - just use the tank backend directly
            new_world = tank_backend

        runner.world = new_world
        runner.world_type = new_world_type

        # Update metadata from registry
        metadata = get_world_metadata(new_world_type)
        runner.mode_id = metadata.mode_id if metadata else new_world_type
        runner.view_mode = metadata.view_mode if metadata else "side"

        # Propagate view mode to engine (for soccer avatars/rendering hints)
        if hasattr(runner.world, "engine"):
            runner.world.engine.view_mode = runner.view_mode

        # Update snapshot builder for the new world type
        from backend.world_registry import _SNAPSHOT_BUILDERS

        builder_factory = _SNAPSHOT_BUILDERS.get(new_world_type)
        if builder_factory:
            runner._entity_snapshot_builder = builder_factory()

        # Clear cached state to force full rebuild on next get_state()
        runner.state_publisher.invalidate_cache()

        # 3) Install NEW hooks and apply NEW constraints/lifecycle
        runner.world_hooks = get_hooks_for_world(new_world_type)

        warmup = getattr(runner.world_hooks, "warmup", None)
        if callable(warmup):
            warmup(runner)

        apply_constraints = getattr(runner.world_hooks, "apply_physics_constraints", None)
        if callable(apply_constraints):
            apply_constraints(runner)

        on_switch = getattr(runner.world_hooks, "on_world_type_switch", None)
        if callable(on_switch):
            on_switch(runner, old_world_type, new_world_type)

        # Restore paused state to what it was at entry
        runner.world.set_paused(was_paused)
        if hasattr(runner.world, "paused"):
            runner.world.paused = was_paused

        logger.info(
            "World type switch complete: now %s (mode_id=%s, view_mode=%s)",
            new_world_type,
            runner.mode_id,
            runner.view_mode,
        )


def update_environment_migration_context(runner: SimulationRunner) -> None:
    """Update the environment with current migration context."""
    if hasattr(runner.world, "engine") and hasattr(runner.world.engine, "environment"):
        env = runner.world.engine.environment
        if env:
            env.connection_manager = runner.connection_manager
            env.world_manager = runner.world_manager
            env.world_id = runner.world_id
            env.world_name = runner.world_name

            # Create (or clear) a migration handler based on available dependencies.
            # Core entities depend only on the MigrationHandler protocol, while the backend
            # provides the concrete implementation.
            if runner.connection_manager is not None and runner.world_manager is not None:
                deps = (runner.connection_manager, runner.world_manager)
                if runner._migration_handler is None or runner._migration_handler_deps != deps:
                    from backend.migration_handler import MigrationHandler

                    runner._migration_handler = MigrationHandler(
                        connection_manager=runner.connection_manager,
                        world_manager=runner.world_manager,
                    )
                    runner._migration_handler_deps = deps
                env.migration_handler = runner._migration_handler
            else:
                runner._migration_handler = None
                runner._migration_handler_deps = (None, None)
                env.migration_handler = None

            logger.info(
                f"Migration context updated for world {runner.world_id[:8] if runner.world_id else 'None'}: "
                f"conn_mgr={'SET' if runner.connection_manager else 'NULL'}, "
                f"manager={'SET' if runner.world_manager else 'NULL'}"
            )
        else:
            logger.warning("Cannot update migration context: environment is None")
    else:
        logger.warning(
            "Cannot update migration context: world.engine or world.engine.environment not found"
        )
