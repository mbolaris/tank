"""Background scheduler for automated tank migrations."""

import asyncio
import logging
import random
from typing import TYPE_CHECKING, Optional

from backend.connection_manager import ConnectionManager
from backend.tank_registry import TankRegistry
from core.entities import Fish
from core.entities.plant import Plant

if TYPE_CHECKING:
    from backend.discovery_service import DiscoveryService
    from backend.server_client import ServerClient

logger = logging.getLogger(__name__)


class MigrationScheduler:
    """Schedules and executes automated entity migrations between tanks.

    Supports both local (same-server) and remote (cross-server) migrations.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        tank_registry: TankRegistry,
        check_interval: float = 2.0,
        discovery_service: Optional["DiscoveryService"] = None,
        server_client: Optional["ServerClient"] = None,
        local_server_id: str = "local-server",
    ):
        """Initialize the migration scheduler.

        Args:
            connection_manager: Manager for tank connections
            tank_registry: Registry of all tanks
            check_interval: Seconds between migration checks (default: 10)
            discovery_service: Optional discovery service for cross-server migrations
            server_client: Optional server client for cross-server migrations
            local_server_id: This server's ID
        """
        self.connection_manager = connection_manager
        self.tank_registry = tank_registry
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

                    if check_count % 6 == 0:  # Log every ~60 seconds
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
        """Perform a migration between tanks on the same server.

        Args:
            connection: The TankConnection
        """
        # Get source and destination tanks
        source_manager = self.tank_registry.get_tank(connection.source_tank_id)
        dest_manager = self.tank_registry.get_tank(connection.destination_tank_id)

        if not source_manager or not dest_manager:
            logger.warning(
                f"Migration failed: tank not found (source={connection.source_tank_id[:8]}, "
                f"dest={connection.destination_tank_id[:8]})"
            )
            return

        # Check if both tanks allow transfers
        if not source_manager.tank_info.allow_transfers:
            return
        if not dest_manager.tank_info.allow_transfers:
            return

        # Skip migration if either tank is paused - prevents population explosions
        # in tanks that haven't been viewed yet (fish would accumulate without dying)
        if getattr(source_manager.world, "paused", False):
            return
        if getattr(dest_manager.world, "paused", False):
            return

        # Get eligible entities (fish and plants)
        eligible_entities = []
        for entity in source_manager.world.entities_list:
            if isinstance(entity, (Fish, Plant)):
                eligible_entities.append(entity)

        if not eligible_entities:
            return  # No entities to migrate

        # Select random entity
        entity = random.choice(eligible_entities)
        entity_id = id(entity)
        entity_type = "fish" if isinstance(entity, Fish) else "plant"

        # Perform the migration
        try:
            from backend.entity_transfer import (
                serialize_entity_for_transfer,
                try_deserialize_entity,
            )
            from backend.transfer_history import log_transfer

            # Serialize entity
            entity_data = serialize_entity_for_transfer(entity)
            if entity_data is None:
                logger.warning(f"Cannot serialize {entity_type} for migration")
                return

            # Track energy leaving the tank (for fish only)
            if isinstance(entity, Fish) and hasattr(entity, 'ecosystem') and entity.ecosystem is not None:
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            # Check destination first (Check)
            outcome = try_deserialize_entity(entity_data, dest_manager.world)
            if not outcome.ok:
                # SILENT FAIL check
                if outcome.error and outcome.error.code == "no_root_spots":
                    # Just return, no restore needed
                    return

                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=None,
                    source_tank_id=connection.source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    destination_tank_id=connection.destination_tank_id,
                    destination_tank_name=dest_manager.tank_info.name,
                    success=False,
                    error=outcome.error.message if outcome.error else "Failed to deserialize in destination",
                )
                return

            # Remove from source (Commit)
            source_manager.world.engine.request_remove(entity, reason="migration_out")

            new_entity = outcome.value
            dest_manager.world.engine.request_spawn(new_entity, reason="migration_in")

            # Track energy entering the destination tank (for fish only)
            if isinstance(new_entity, Fish) and hasattr(new_entity, 'ecosystem') and new_entity.ecosystem is not None:
                new_entity.ecosystem.record_energy_gain("migration_in", new_entity.energy)

            # Try to invalidate cached SimulationRunner state so frontends update
            try:
                dest_runner = getattr(dest_manager, "_runner", None)
                if dest_runner and hasattr(dest_runner, "invalidate_state_cache"):
                    dest_runner.invalidate_state_cache()
                elif dest_runner and hasattr(dest_runner, "_invalidate_state_cache"):
                    dest_runner._invalidate_state_cache()

                src_runner = getattr(source_manager, "_runner", None)
                if src_runner and hasattr(src_runner, "invalidate_state_cache"):
                    src_runner.invalidate_state_cache()
                elif src_runner and hasattr(src_runner, "_invalidate_state_cache"):
                    src_runner._invalidate_state_cache()
            except Exception:
                logger.debug("Failed to invalidate runner caches after migration", exc_info=True)

            # Log successful migration
            log_transfer(
                entity_type=entity_type,
                entity_old_id=entity_id,
                entity_new_id=id(new_entity),
                source_tank_id=connection.source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                destination_tank_id=connection.destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name,
                success=True,
            )

            logger.debug(
                f"Migrated {entity_type} from {source_manager.tank_info.name} to "
                f"{dest_manager.tank_info.name} (probability={connection.probability}%)"
            )

        except Exception as e:
            logger.error(f"Local migration failed: {e}", exc_info=True)

    async def _perform_remote_migration(self, connection) -> None:
        """Perform a migration between tanks on different servers.

        Args:
            connection: The TankConnection (cross-server)
        """
        # Check if we have the necessary services
        if not self.discovery_service or not self.server_client:
            logger.warning("Cannot perform remote migration: discovery service or server client not available")
            return

        # Get source tank (must be local)
        source_manager = self.tank_registry.get_tank(connection.source_tank_id)
        if not source_manager:
            logger.warning(f"Remote migration failed: source tank not found: {connection.source_tank_id[:8]}")
            return

        # Check if source tank allows transfers
        if not source_manager.tank_info.allow_transfers:
            return

        # Skip migration if source tank is paused - prevents inconsistent state
        if getattr(source_manager.world, "paused", False):
            return

        # Get eligible entities
        eligible_entities = []
        for entity in source_manager.world.entities_list:
            if isinstance(entity, (Fish, Plant)):
                eligible_entities.append(entity)

        if not eligible_entities:
            return  # No entities to migrate

        # Select random entity
        entity = random.choice(eligible_entities)
        entity_id = id(entity)
        entity_type = "fish" if isinstance(entity, Fish) else "plant"

        try:
            from backend.entity_transfer import serialize_entity_for_transfer
            from backend.transfer_history import log_transfer

            # Serialize entity
            entity_data = serialize_entity_for_transfer(entity)
            if entity_data is None:
                logger.warning(f"Cannot serialize {entity_type} for remote migration")
                return

            # Get destination server info
            dest_server = await self.discovery_service.get_server(connection.destination_server_id)
            if not dest_server:
                logger.warning(f"Remote migration failed: destination server not found: {connection.destination_server_id}")
                return

            # Track energy leaving the tank (for fish only)
            if isinstance(entity, Fish) and hasattr(entity, 'ecosystem') and entity.ecosystem is not None:
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            # Remove from source tank
            source_manager.world.engine.request_remove(entity, reason="remote_migration_out")

            # Send to remote server
            result = await self.server_client.remote_transfer_entity(
                server=dest_server,
                destination_tank_id=connection.destination_tank_id,
                entity_data=entity_data,
                source_server_id=self.local_server_id,
                source_tank_id=connection.source_tank_id,
            )

            if result and result.get("success"):
                # Remote transfer succeeded
                logger.info(
                    f"Remote migration: {entity_type} from {source_manager.tank_info.name} "
                    f"to {connection.destination_server_id}:{connection.destination_tank_id[:8]} "
                    f"(probability={connection.probability}%)"
                )

                # Log locally
                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=result.get("entity", {}).get("new_id", -1),
                    source_tank_id=connection.source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    destination_tank_id=f"{connection.destination_server_id}:{connection.destination_tank_id}",
                    destination_tank_name=f"Remote tank on {connection.destination_server_id}",
                    success=True,
                )
            else:
                # Remote transfer failed - restore entity
                from backend.entity_transfer import deserialize_entity

                restored = deserialize_entity(entity_data, source_manager.world)
                if restored:
                    source_manager.world.engine.request_spawn(restored, reason="remote_migration_restore")

                error_msg = result.get("error", "Unknown error") if result else "No response from remote server"

                # SILENT FAIL check
                if error_msg == "no_root_spots":
                    # Restore silently
                    return

                logger.warning(f"Remote migration failed: {error_msg}")

                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=None,
                    source_tank_id=connection.source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    destination_tank_id=f"{connection.destination_server_id}:{connection.destination_tank_id}",
                    destination_tank_name=f"Remote tank on {connection.destination_server_id}",
                    success=False,
                    error=error_msg,
                )

        except Exception as e:
            logger.error(f"Remote migration failed: {e}", exc_info=True)

            # Try to restore entity
            from backend.entity_transfer import deserialize_entity, serialize_entity_for_transfer

            try:
                entity_data = serialize_entity_for_transfer(entity)
                if entity_data:
                    restored = deserialize_entity(entity_data, source_manager.world)
                    if restored:
                        source_manager.world.engine.request_spawn(restored, reason="remote_migration_restore_error")
            except Exception as restore_error:
                logger.error(
                    f"Failed to restore entity {entity.id} after migration failure: {restore_error}",
                    exc_info=True,
                )
