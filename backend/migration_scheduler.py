"""Background scheduler for automated world migrations."""

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Any, Optional

from backend.connection_manager import ConnectionManager
from backend.world_manager import WorldManager

if TYPE_CHECKING:
    from backend.discovery_service import DiscoveryService
    from backend.server_client import ServerClient

logger = logging.getLogger(__name__)

# Entity types eligible for migration (checked via snapshot_type property)
_MIGRATABLE_TYPES = frozenset({"fish", "plant"})


def _is_migratable(entity: Any) -> bool:
    """Check if an entity is eligible for migration via snapshot_type protocol."""
    snapshot_type = getattr(entity, "snapshot_type", None)
    return snapshot_type in _MIGRATABLE_TYPES


def _get_entity_type(entity: Any) -> str:
    """Get entity type string via snapshot_type protocol."""
    return getattr(entity, "snapshot_type", type(entity).__name__.lower())


class MigrationScheduler:
    """Schedules and executes automated entity migrations between worlds.

    Supports both local (same-server) and remote (cross-server) migrations.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        world_manager: WorldManager,
        check_interval: float = 2.0,
        discovery_service: Optional["DiscoveryService"] = None,
        server_client: Optional["ServerClient"] = None,
        local_server_id: str = "local-server",
    ):
        """Initialize the migration scheduler.

        Args:
            connection_manager: Manager for world connections
            world_manager: Manager for all worlds
            check_interval: Seconds between migration checks (default: 2)
            discovery_service: Optional discovery service for cross-server migrations
            server_client: Optional server client for cross-server migrations
            local_server_id: This server's ID
        """
        self.connection_manager = connection_manager
        self.world_manager = world_manager
        self.check_interval = check_interval
        self.discovery_service = discovery_service
        self.server_client = server_client
        self.local_server_id = local_server_id
        self._task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(f"MigrationScheduler initialized (check_interval={check_interval}s)")

    async def start(self) -> None:
        """Start the migration scheduler."""
        if self._running:
            logger.warning("Migration scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="migration_scheduler")
        logger.info("Migration scheduler started")

    async def stop(self) -> None:
        """Stop the migration scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Migration scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Migration scheduler loop started")
        check_count = 0

        try:
            while self._running:
                try:
                    check_count += 1
                    connections = self.connection_manager.list_connections()

                    if check_count % 6 == 0:  # Log every ~12 seconds
                        logger.debug(
                            f"Migration check #{check_count}: {len(connections)} active connections"
                        )

                    for connection in connections:
                        try:
                            await self._check_migration(connection)
                        except Exception as e:
                            logger.error(
                                f"Error checking migration for connection {connection.id}: {e}",
                                exc_info=True,
                            )

                    await asyncio.sleep(self.check_interval)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in migration scheduler loop: {e}", exc_info=True)
                    await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Migration scheduler loop cancelled")
        finally:
            logger.info(f"Migration scheduler loop ended after {check_count} checks")

    async def _check_migration(self, connection) -> None:
        """Check if a migration should occur for a connection.

        Handles both local (same-server) and remote (cross-server) migrations.

        Args:
            connection: The TankConnection to check
        """
        # Roll the dice
        roll = random.randint(1, 100)
        if roll > connection.probability:
            return  # No migration this time

        # Check if this is a remote migration
        if connection.is_remote():
            await self._perform_remote_migration(connection)
        else:
            await self._perform_local_migration(connection)

    async def _perform_local_migration(self, connection) -> None:
        """Perform a migration between worlds on the same server.

        Args:
            connection: The TankConnection
        """
        # Get source and destination worlds
        source_instance = self.world_manager.get_world(connection.source_world_id)
        dest_instance = self.world_manager.get_world(connection.destination_world_id)

        if not source_instance or not dest_instance:
            logger.warning(
                f"Migration failed: world not found (source={connection.source_world_id[:8]}, "
                f"dest={connection.destination_world_id[:8]})"
            )
            return

        # Get the runners
        source_runner = source_instance.runner
        dest_runner = dest_instance.runner

        # Skip migration if either world is paused
        if getattr(source_runner, "paused", False):
            return
        if getattr(dest_runner, "paused", False):
            return

        # Get the world/engine from runners
        source_world = getattr(source_runner, "world", None)
        dest_world = getattr(dest_runner, "world", None)
        if not source_world or not dest_world:
            return

        # Get eligible entities (fish and plants via snapshot_type protocol)
        entities_list = getattr(source_world, "entities_list", [])
        eligible_entities = [e for e in entities_list if _is_migratable(e)]

        if not eligible_entities:
            return  # No entities to migrate

        # Select random entity
        entity = random.choice(eligible_entities)
        entity_id = id(entity)
        entity_type = _get_entity_type(entity)

        # Perform the migration
        try:
            from backend.transfer_history import log_transfer
            from core.transfer.entity_transfer import (
                serialize_entity_for_transfer,
                try_deserialize_entity,
            )

            # Serialize entity
            entity_data = serialize_entity_for_transfer(entity)
            if entity_data is None:
                logger.warning(f"Cannot serialize {entity_type} for migration")
                return

            # Track energy leaving the tank (for fish only)
            if (
                entity_type == "fish"
                and hasattr(entity, "ecosystem")
                and entity.ecosystem is not None
            ):
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            # Check destination first (Check)
            outcome = try_deserialize_entity(entity_data, dest_world)
            if not outcome.ok:
                # SILENT FAIL check
                if outcome.error and outcome.error.code == "no_root_spots":
                    # Just return, no restore needed
                    return

                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=None,
                    source_world_id=connection.source_world_id,
                    source_world_name=source_instance.name,
                    destination_world_id=connection.destination_world_id,
                    destination_world_name=dest_instance.name,
                    success=False,
                    error=(
                        outcome.error.message
                        if outcome.error
                        else "Failed to deserialize in destination"
                    ),
                )
                return

            # Remove from source (Commit)
            source_world.engine.request_remove(entity, reason="migration_out")

            new_entity = outcome.value
            if new_entity is None:
                return
            dest_world.engine.request_spawn(new_entity, reason="migration_in")

            # Track energy entering the destination tank (for fish only)
            if _get_entity_type(new_entity) == "fish":
                ecosystem = getattr(new_entity, "ecosystem", None)
                energy = getattr(new_entity, "energy", None)
                if ecosystem is not None and isinstance(energy, (int, float)):
                    ecosystem.record_energy_gain("migration_in", float(energy))

            # Try to invalidate cached SimulationRunner state so frontends update
            try:
                if hasattr(source_runner, "invalidate_state_cache"):
                    source_runner.invalidate_state_cache()
                if hasattr(dest_runner, "invalidate_state_cache"):
                    dest_runner.invalidate_state_cache()
            except Exception:
                logger.debug("Failed to invalidate runner caches after migration", exc_info=True)

            # Log successful migration
            log_transfer(
                entity_type=entity_type,
                entity_old_id=entity_id,
                entity_new_id=id(new_entity),
                source_world_id=connection.source_world_id,
                source_world_name=source_instance.name,
                destination_world_id=connection.destination_world_id,
                destination_world_name=dest_instance.name,
                success=True,
            )

            logger.debug(
                f"Migrated {entity_type} from {source_instance.name} to "
                f"{dest_instance.name} (probability={connection.probability}%)"
            )

        except Exception as e:
            logger.error(f"Local migration failed: {e}", exc_info=True)

    async def _perform_remote_migration(self, connection) -> None:
        """Perform a migration between worlds on different servers.

        Args:
            connection: The TankConnection (cross-server)
        """
        # Check if we have the necessary services
        if not self.discovery_service or not self.server_client:
            logger.warning(
                "Cannot perform remote migration: discovery service or server client not available"
            )
            return

        # Get source world (must be local)
        source_instance = self.world_manager.get_world(connection.source_world_id)
        if not source_instance:
            logger.warning(
                f"Remote migration failed: source world not found: {connection.source_world_id[:8]}"
            )
            return

        source_runner = source_instance.runner
        source_world = getattr(source_runner, "world", None)
        if not source_world:
            return

        # Skip migration if source world is paused
        if getattr(source_runner, "paused", False):
            return

        # Get eligible entities via snapshot_type protocol
        entities_list = getattr(source_world, "entities_list", [])
        eligible_entities = [e for e in entities_list if _is_migratable(e)]

        if not eligible_entities:
            return  # No entities to migrate

        # Select random entity
        entity = random.choice(eligible_entities)
        entity_id = id(entity)
        entity_type = _get_entity_type(entity)

        try:
            from backend.transfer_history import log_transfer
            from core.transfer.entity_transfer import (
                deserialize_entity,
                serialize_entity_for_transfer,
            )

            # Serialize entity
            entity_data = serialize_entity_for_transfer(entity)
            if entity_data is None:
                logger.warning(f"Cannot serialize {entity_type} for remote migration")
                return

            # Get destination server info
            dest_server = await self.discovery_service.get_server(connection.destination_server_id)
            if not dest_server:
                logger.warning(
                    f"Remote migration failed: destination server not found: {connection.destination_server_id}"
                )
                return

            # Track energy leaving the tank (for fish only)
            if (
                entity_type == "fish"
                and hasattr(entity, "ecosystem")
                and entity.ecosystem is not None
            ):
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            # Remove from source world
            source_world.engine.request_remove(entity, reason="remote_migration_out")

            # Send to remote server
            result = await self.server_client.remote_transfer_entity(
                server=dest_server,
                destination_world_id=connection.destination_world_id,
                entity_data=entity_data,
                source_server_id=self.local_server_id,
                source_world_id=connection.source_world_id,
            )

            if result and result.get("success"):
                # Remote transfer succeeded
                logger.info(
                    f"Remote migration: {entity_type} from {source_instance.name} "
                    f"to {connection.destination_server_id}:{connection.destination_tank_id[:8]} "
                    f"(probability={connection.probability}%)"
                )

                # Log locally
                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=result.get("entity", {}).get("new_id", -1),
                    source_world_id=connection.source_world_id,
                    source_world_name=source_instance.name,
                    destination_world_id=f"{connection.destination_server_id}:{connection.destination_world_id}",
                    destination_world_name=f"Remote tank on {connection.destination_server_id}",
                    success=True,
                )
            else:
                # Remote transfer failed - restore entity
                restored = deserialize_entity(entity_data, source_world)
                if restored:
                    source_world.engine.request_spawn(restored, reason="remote_migration_restore")

                error_msg = (
                    result.get("error", "Unknown error")
                    if result
                    else "No response from remote server"
                )

                # SILENT FAIL check
                if error_msg == "no_root_spots":
                    # Restore silently
                    return

                logger.warning(f"Remote migration failed: {error_msg}")

                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=None,
                    source_world_id=connection.source_world_id,
                    source_world_name=source_instance.name,
                    destination_world_id=f"{connection.destination_server_id}:{connection.destination_world_id}",
                    destination_world_name=f"Remote tank on {connection.destination_server_id}",
                    success=False,
                    error=error_msg,
                )

        except Exception as e:
            logger.error(f"Remote migration failed: {e}", exc_info=True)

            # Try to restore entity
            from core.transfer.entity_transfer import (
                deserialize_entity,
                serialize_entity_for_transfer,
            )

            try:
                entity_data = serialize_entity_for_transfer(entity)
                if entity_data:
                    restored = deserialize_entity(entity_data, source_world)
                    if restored:
                        source_world.engine.request_spawn(
                            restored, reason="remote_migration_restore_error"
                        )
            except Exception as restore_error:
                logger.error(
                    f"Failed to restore entity {entity_id} after migration failure: {restore_error}",
                    exc_info=True,
                )
