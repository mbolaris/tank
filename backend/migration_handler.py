"""Backend implementation of migration handler for entity transfers."""

import logging
import random
from typing import TYPE_CHECKING, Any

from backend.entity_transfer import deserialize_entity, serialize_entity_for_transfer
from backend.transfer_history import log_transfer

if TYPE_CHECKING:
    from core.entities.fish import Fish

logger = logging.getLogger(__name__)


class BackendMigrationHandler:
    """Handles entity migrations between tanks in the backend.

    This class implements the migration logic that was previously embedded in
    Fish entity, properly decoupling core from backend concerns.
    """

    def __init__(self, connection_manager, tank_registry):
        """Initialize migration handler.

        Args:
            connection_manager: Manager for inter-tank connections
            tank_registry: Registry of all active tanks
        """
        self.connection_manager = connection_manager
        self.tank_registry = tank_registry

    def attempt_entity_migration(
        self, entity: Any, direction: str, source_tank_id: str
    ) -> bool:
        """Attempt to migrate an entity to a connected tank.

        Args:
            entity: The entity attempting to migrate
            direction: "left" or "right" - which boundary was hit
            source_tank_id: ID of the source tank

        Returns:
            True if migration successful, False otherwise
        """
        # Find connections for this tank and direction
        connections = self.connection_manager.get_connections_for_tank(
            source_tank_id, direction
        )

        if not connections:
            return False  # No connection in this direction

        logger.debug(
            f"Entity {type(entity).__name__} hit {direction} boundary in tank "
            f"{source_tank_id[:8]}, found {len(connections)} connection(s)"
        )

        # Pick a random connection if multiple exist
        connection = random.choice(connections)

        # Get destination tank
        dest_manager = self.tank_registry.get_tank(connection.destination_tank_id)
        if not dest_manager:
            logger.warning(f"Destination tank {connection.destination_tank_id} not found")
            return False

        # Check if destination allows transfers
        if not dest_manager.tank_info.allow_transfers:
            logger.debug(
                f"Destination tank {dest_manager.tank_info.name} does not allow transfers"
            )
            return False

        # Get source manager for logging
        source_manager = self.tank_registry.get_tank(source_tank_id)
        if not source_manager:
            logger.warning(f"Source tank {source_tank_id} not found")
            return False

        # Perform the migration
        try:
            # Track energy leaving the source tank (for fish only)
            from core.entities.fish import Fish
            if isinstance(entity, Fish) and hasattr(entity, 'ecosystem') and entity.ecosystem is not None:
                entity.ecosystem.record_energy_burn("migration", entity.energy)

            # Serialize the entity (pass direction for plants to select appropriate edge spot)
            entity_data = serialize_entity_for_transfer(entity, migration_direction=direction)
            if entity_data is None:
                logger.error("Failed to serialize entity for transfer")
                return False

            old_id = id(entity)

            # Deserialize in destination
            new_entity = deserialize_entity(entity_data, dest_manager.world)
            if new_entity is None:
                log_transfer(
                    entity_type=type(entity).__name__.lower(),
                    entity_old_id=old_id,
                    entity_new_id=None,
                    source_tank_id=source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    destination_tank_id=connection.destination_tank_id,
                    destination_tank_name=dest_manager.tank_info.name,
                    success=False,
                    error="Failed to deserialize in destination",
                    generation=getattr(entity, "generation", None),
                )
                return False

            # Position entity at opposite edge of destination tank
            if direction == "left":
                new_entity.pos.x = (
                    dest_manager.world.config.screen_width - new_entity.width - 10
                )
            else:  # right
                new_entity.pos.x = 10

            dest_manager.world.engine.add_entity(new_entity)

            # Track energy entering the destination tank (for fish only)
            if isinstance(new_entity, Fish) and hasattr(new_entity, 'ecosystem') and new_entity.ecosystem is not None:
                new_entity.ecosystem.record_energy_gain("migration_in", new_entity.energy)

            # Invalidate cached state on destination and source runners so
            # websocket clients immediately see updated stats (e.g., max generation).
            try:
                dest_runner = getattr(dest_manager, "_runner", None)
                if dest_runner and hasattr(dest_runner, "_invalidate_state_cache"):
                    dest_runner._invalidate_state_cache()

                source_runner = getattr(source_manager, "_runner", None)
                if source_runner and hasattr(source_runner, "_invalidate_state_cache"):
                    source_runner._invalidate_state_cache()
            except Exception:
                # Non-fatal: cache invalidation is best-effort
                logger.debug("Failed to invalidate runner cache after migration", exc_info=True)

            # Log successful migration
            generation = getattr(entity, "generation", None)
            log_transfer(
                entity_type=type(entity).__name__.lower(),
                entity_old_id=old_id,
                entity_new_id=id(new_entity),
                source_tank_id=source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                destination_tank_id=connection.destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name,
                success=True,
                generation=generation,
            )

            logger.info(
                f"{type(entity).__name__} (Gen {generation}) migrated {direction} from "
                f"{source_manager.tank_info.name} to {dest_manager.tank_info.name}"
            )

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            # Log failed transfer
            log_transfer(
                entity_type=type(entity).__name__.lower(),
                entity_old_id=id(entity),
                entity_new_id=None,
                source_tank_id=source_tank_id,
                source_tank_name=source_manager.tank_info.name if source_manager else "unknown",
                destination_tank_id=connection.destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name if dest_manager else "unknown",
                success=False,
                error=str(e),
                generation=getattr(entity, "generation", None),
            )
            return False
