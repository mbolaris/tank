"""Backend implementation of migration handler for entity transfers."""

import hashlib
import logging
import os
from typing import TYPE_CHECKING, Any

from backend.transfer_history import log_transfer
from core.transfer.entity_transfer import try_deserialize_entity, try_serialize_entity_for_transfer

if TYPE_CHECKING:
    from backend.connection_manager import ConnectionManager
    from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


class MigrationHandler:
    """Handles entity migrations between worlds in the backend.

    This class implements the migration logic that was previously embedded in
    Fish entity, properly decoupling core from backend concerns.
    """

    def __init__(self, connection_manager: "ConnectionManager", world_manager: "WorldManager"):
        """Initialize migration handler.

        Args:
            connection_manager: Manager for inter-world connections
            world_manager: Manager for all active worlds
        """
        self.connection_manager = connection_manager
        self.world_manager = world_manager

    @staticmethod
    def _connection_sort_key(connection: Any) -> tuple:
        return (
            getattr(connection, "destination_world_id", ""),
            getattr(connection, "destination_server_id", "") or "",
            getattr(connection, "direction", "") or "",
            getattr(connection, "source_world_id", "") or "",
            getattr(connection, "id", "") or "",
        )

    @staticmethod
    def _stable_hash64(*parts: Any) -> int:
        material = "|".join(str(part) for part in parts).encode("utf-8")
        return int.from_bytes(hashlib.blake2b(material, digest_size=8).digest(), "little")

    @staticmethod
    def _get_entity_selection_id(entity: Any) -> Any:
        getter = getattr(entity, "get_entity_id", None)
        if callable(getter):
            try:
                value = getter()
                if value is not None:
                    return value
            except Exception:
                pass

        for attr in ("fish_id", "plant_id", "entity_id", "id"):
            value = getattr(entity, attr, None)
            if value is not None:
                return value

        return 0

    @staticmethod
    def _get_env_selection_seed() -> int:
        raw = os.getenv("MIGRATION_SELECTION_SEED")
        if not raw:
            return 0
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid MIGRATION_SELECTION_SEED=%s; using 0", raw)
            return 0

    def _resolve_selection_seed(self, source_runner: Any, source_world: Any) -> int:
        seed = None
        if source_world is not None:
            engine = getattr(source_world, "engine", None)
            if engine is not None:
                seed = getattr(engine, "seed", None)

        if seed is None and source_runner is not None:
            seed = getattr(source_runner, "seed", None)
            if seed is None:
                seed = getattr(source_runner, "_seed", None)

        if seed is None:
            seed = self._get_env_selection_seed()

        try:
            return int(seed)
        except (TypeError, ValueError):
            return 0

    def _select_connection(
        self,
        connections: list,
        entity: Any,
        source_world_id: str,
        direction: str,
        selection_seed: int,
    ) -> Any:
        ordered = sorted(connections, key=self._connection_sort_key)
        entity_key = self._get_entity_selection_id(entity)
        index = self._stable_hash64(selection_seed, source_world_id, direction, entity_key) % len(
            ordered
        )
        return ordered[index]

    def attempt_entity_migration(self, entity: Any, direction: str, source_world_id: str) -> bool:
        """Attempt to migrate an entity to a connected world.

        Args:
            entity: The entity attempting to migrate
            direction: "left" or "right" - which boundary was hit
            source_world_id: ID of the source world

        Returns:
            True if migration successful, False otherwise
        """
        # Find connections for this world and direction
        connections = self.connection_manager.get_connections_for_world(source_world_id, direction)

        if not connections:
            return False  # No connection in this direction

        logger.debug(
            f"Entity {type(entity).__name__} hit {direction} boundary in world "
            f"{source_world_id[:8]}, found {len(connections)} connection(s)"
        )

        # Get source instance for selection seed and logging
        source_instance = self.world_manager.get_world(source_world_id)
        if not source_instance:
            logger.warning(f"Source world {source_world_id} not found")
            return False

        source_runner = source_instance.runner
        source_world = getattr(source_runner, "world", None)

        selection_seed = self._resolve_selection_seed(source_runner, source_world)
        connection = self._select_connection(
            connections=connections,
            entity=entity,
            source_world_id=source_world_id,
            direction=direction,
            selection_seed=selection_seed,
        )

        # Get destination world
        dest_instance = self.world_manager.get_world(connection.destination_world_id)
        if not dest_instance:
            logger.warning(f"Destination world {connection.destination_world_id} not found")
            return False

        # Get the actual world objects
        dest_runner = dest_instance.runner
        dest_world = getattr(dest_runner, "world", None)

        if not source_world or not dest_world:
            return False

        # Lock destination runner state while we deserialize/add to prevent races with its update loop.
        # Avoid deadlocks by using a short timeout; if destination is busy, migration simply fails
        # and the entity stays in the source world.
        dest_lock = getattr(dest_runner, "lock", None)
        dest_lock_acquired = False
        if dest_lock is not None:
            try:
                dest_lock_acquired = dest_lock.acquire(timeout=0.02)
            except TypeError:
                dest_lock_acquired = dest_lock.acquire(False)
            if not dest_lock_acquired:
                return False

        # Best-effort lock for source if we aren't already inside its update loop.
        source_lock = getattr(source_runner, "lock", None)
        source_lock_acquired = False
        if source_lock is not None:
            try:
                source_lock_acquired = source_lock.acquire(False)
            except TypeError:
                source_lock_acquired = False

        # Perform the migration
        removed_from_source = False
        added_to_destination = False
        new_entity = None
        original_root_spot = None
        try:
            # Track energy leaving the source world (for fish only)
            entity_type = getattr(entity, "snapshot_type", type(entity).__name__.lower())

            if (
                entity_type == "fish"
                and hasattr(entity, "ecosystem")
                and entity.ecosystem is not None
            ):
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            if entity_type == "plant":
                # If destination has no available root spots, fail fast to avoid churn.
                dest_root_spot_manager = getattr(dest_world.engine, "root_spot_manager", None)
                if dest_root_spot_manager is None or dest_root_spot_manager.get_empty_count() <= 0:
                    return False
                original_root_spot = getattr(entity, "root_spot", None)

            # Serialize the entity (pass direction for plants to select appropriate edge spot)
            outcome = try_serialize_entity_for_transfer(entity, migration_direction=direction)
            if not outcome.ok:
                logger.error(
                    "Failed to serialize entity for transfer (code=%s): %s",
                    outcome.error.code if outcome.error else "unknown",
                    outcome.error.message if outcome.error else "unknown error",
                )
                return False
            entity_data = outcome.value

            old_id = id(entity)

            # Optimistic removal causes flickering if destination fails.
            # New flow: Check destination first -> then remove/add.

            if entity_data is None:
                return False

            # Deserialize in destination (Check)
            new_entity_outcome = try_deserialize_entity(entity_data, dest_world)
            if not new_entity_outcome.ok:
                # Failed to deserialize in destination (e.g. no root spots)
                # Just return False, no need to restore since we haven't removed yet.
                if new_entity_outcome.error and new_entity_outcome.error.code == "no_root_spots":
                    # Silent fail for plants
                    return False

                log_transfer(
                    entity_type=type(entity).__name__.lower(),
                    entity_old_id=old_id,
                    entity_new_id=None,
                    source_world_id=source_world_id,
                    source_world_name=source_instance.name,
                    destination_world_id=connection.destination_world_id,
                    destination_world_name=dest_instance.name,
                    success=False,
                    error=f"Failed to deserialize in destination: {new_entity_outcome.error.code if new_entity_outcome.error else 'unknown'}",
                    generation=getattr(entity, "generation", None),
                    selection_seed=selection_seed,
                )
                return False

            # If we get here, migration is go.
            # Remove from source (Commit)
            source_world.engine.request_remove(entity, reason="migration_transfer")
            removed_from_source = True

            new_entity = new_entity_outcome.value
            if new_entity is None:
                return False

            # Position entity at opposite edge of destination world
            if direction == "left":
                new_entity.pos.x = dest_world.config.screen_width - new_entity.width - 10
            else:  # right
                new_entity.pos.x = 10

            dest_world.engine.request_spawn(new_entity, reason="migration_in")
            added_to_destination = True

            # Track energy entering the destination world (for fish only)
            new_entity_type = getattr(new_entity, "snapshot_type", type(new_entity).__name__.lower())
            if (
                new_entity_type == "fish"
                and hasattr(new_entity, "ecosystem")
                and new_entity.ecosystem is not None
            ):
                new_entity.ecosystem.record_energy_gain("migration_in", new_entity.energy)

            # Invalidate cached state on destination and source runners so
            # websocket clients immediately see updated stats (e.g., max generation).
            try:
                if hasattr(dest_runner, "invalidate_state_cache"):
                    dest_runner.invalidate_state_cache()
                elif hasattr(dest_runner, "_invalidate_state_cache"):
                    dest_runner._invalidate_state_cache()

                if hasattr(source_runner, "invalidate_state_cache"):
                    source_runner.invalidate_state_cache()
                elif hasattr(source_runner, "_invalidate_state_cache"):
                    source_runner._invalidate_state_cache()
            except Exception:
                # Non-fatal: cache invalidation is best-effort
                logger.debug("Failed to invalidate runner cache after migration", exc_info=True)

            # Log successful migration
            generation = getattr(entity, "generation", None)
            try:
                log_transfer(
                    entity_type=type(entity).__name__.lower(),
                    entity_old_id=old_id,
                    entity_new_id=id(new_entity),
                    source_world_id=source_world_id,
                    source_world_name=source_instance.name,
                    destination_world_id=connection.destination_world_id,
                    destination_world_name=dest_instance.name,
                    success=True,
                    generation=generation,
                    selection_seed=selection_seed,
                )
            except Exception:
                logger.debug("Failed to log successful migration", exc_info=True)

            logger.debug(
                f"{type(entity).__name__} (Gen {generation}) migrated {direction} from "
                f"{source_instance.name} to {dest_instance.name}"
            )

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            if removed_from_source and not added_to_destination:
                try:
                    if original_root_spot is not None:
                        try:
                            original_root_spot.claim(entity)
                        except Exception:
                            logger.debug(
                                "Failed to re-claim root spot after migration error (world=%s)",
                                source_world_id[:8],
                                exc_info=True,
                            )
                    source_world.engine.request_spawn(entity, reason="migration_restore_error")
                except Exception:
                    logger.debug(
                        "Failed to restore entity after migration error (world=%s)",
                        source_world_id[:8],
                        exc_info=True,
                    )
            # Log failed transfer
            try:
                log_transfer(
                    entity_type=type(entity).__name__.lower(),
                    entity_old_id=id(entity),
                    entity_new_id=None,
                    source_world_id=source_world_id,
                    source_world_name=source_instance.name if source_instance else "unknown",
                    destination_world_id=connection.destination_world_id,
                    destination_world_name=(dest_instance.name if dest_instance else "unknown"),
                    success=False,
                    error=str(e),
                    generation=getattr(entity, "generation", None),
                    selection_seed=selection_seed,
                )
            except Exception:
                logger.debug("Failed to log failed migration", exc_info=True)
            return False
        finally:
            if source_lock is not None and source_lock_acquired:
                try:
                    source_lock.release()
                except Exception:
                    pass
            if dest_lock is not None and dest_lock_acquired:
                try:
                    dest_lock.release()
                except Exception:
                    pass
