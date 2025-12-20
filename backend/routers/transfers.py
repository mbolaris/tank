"""Entity transfer and connection management API endpoints."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.connection_manager import ConnectionManager, TankConnection
from backend.entity_transfer import deserialize_entity, serialize_entity_for_transfer
from backend.models import RemoteTransferRequest
from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


router = APIRouter(tags=["transfers"])


def log_transfer_success(
    entity_data: Dict[str, Any],
    old_id: int,
    new_id: int,
    source_tank_id: str,
    source_tank_name: str,
    dest_tank_id: str,
    dest_tank_name: str,
) -> None:
    """Log a successful entity transfer.

    Args:
        entity_data: Serialized entity data
        old_id: Original entity ID
        new_id: New entity ID in destination tank
        source_tank_id: Source tank identifier
        source_tank_name: Source tank name
        dest_tank_id: Destination tank identifier
        dest_tank_name: Destination tank name
    """
    from backend.transfer_history import log_transfer

    log_transfer(
        entity_type=entity_data.get("type", "unknown"),
        entity_old_id=old_id,
        entity_new_id=new_id,
        source_tank_id=source_tank_id,
        source_tank_name=source_tank_name,
        destination_tank_id=dest_tank_id,
        destination_tank_name=dest_tank_name,
        success=True,
    )


def log_transfer_failure(
    entity_data: Dict[str, Any],
    old_id: int,
    source_tank_id: str,
    source_tank_name: str,
    dest_tank_id: str,
    dest_tank_name: str,
    error: str,
) -> None:
    """Log a failed entity transfer.

    Args:
        entity_data: Serialized entity data
        old_id: Original entity ID
        source_tank_id: Source tank identifier
        source_tank_name: Source tank name
        dest_tank_id: Destination tank identifier
        dest_tank_name: Destination tank name
        error: Error message describing the failure
    """
    from backend.transfer_history import log_transfer

    log_transfer(
        entity_type=entity_data.get("type", "unknown"),
        entity_old_id=old_id,
        entity_new_id=None,
        source_tank_id=source_tank_id,
        source_tank_name=source_tank_name,
        destination_tank_id=dest_tank_id,
        destination_tank_name=dest_tank_name,
        success=False,
        error=error,
    )


def setup_router(
    tank_registry: TankRegistry,
    connection_manager: ConnectionManager,
) -> APIRouter:
    """Setup the transfers router with required dependencies.

    Args:
        tank_registry: The tank registry instance
        connection_manager: The connection manager instance

    Returns:
        Configured APIRouter
    """

    @router.post("/api/tanks/{source_tank_id}/transfer")
    async def transfer_entity(source_tank_id: str, entity_id: int, destination_tank_id: str):
        """Transfer an entity from one tank to another.

        Args:
            source_tank_id: The tank ID containing the entity
            entity_id: The entity ID to transfer
            destination_tank_id: The tank ID to transfer to

        Returns:
            Success message with entity data, or error if transfer fails
        """
        # Get source tank
        source_manager = tank_registry.get_tank(source_tank_id)
        if source_manager is None:
            return JSONResponse({"error": f"Source tank not found: {source_tank_id}"}, status_code=404)

        # Get destination tank
        dest_manager = tank_registry.get_tank(destination_tank_id)
        if dest_manager is None:
            return JSONResponse({"error": f"Destination tank not found: {destination_tank_id}"}, status_code=404)

        # Check if source tank allows transfers
        if not source_manager.tank_info.allow_transfers:
            return JSONResponse(
                {"error": f"Tank '{source_manager.tank_info.name}' does not allow entity transfers"},
                status_code=403,
            )

        # Check if destination tank allows transfers
        if not dest_manager.tank_info.allow_transfers:
            return JSONResponse(
                {"error": f"Tank '{dest_manager.tank_info.name}' does not allow entity transfers"},
                status_code=403,
            )

        # Find entity in source tank
        source_entity = None
        for entity in source_manager.world.engine.entities_list:
            if entity.id == entity_id:
                source_entity = entity
                break

        if source_entity is None:
            return JSONResponse({"error": f"Entity not found in source tank: {entity_id}"}, status_code=404)

        # Serialize entity
        entity_data = serialize_entity_for_transfer(source_entity)
        if entity_data is None:
            return JSONResponse(
                {"error": f"Entity type {type(source_entity).__name__} cannot be transferred"},
                status_code=400,
            )

        try:
            # Remove from source tank
            # Record migration outflow for Fish entities
            if entity_data.get("type") == "fish" and source_manager.world.ecosystem:
                source_manager.world.ecosystem.record_energy_burn("migration", source_entity.energy)

            source_manager.world.engine.remove_entity(source_entity)
            logger.info(f"Removed entity {entity_id} from tank {source_tank_id[:8]}")

            # Deserialize and add to destination tank
            outcome = try_deserialize_entity(entity_data, dest_manager.world)
            if not outcome.ok:
                # SILENT FAIL check
                if outcome.error and outcome.error.code == "no_root_spots":
                    # Restore to source silently
                    restored_entity = deserialize_entity(entity_data, source_manager.world)
                    if restored_entity:
                        source_manager.world.engine.add_entity(restored_entity)
                    return JSONResponse(
                        {"error": "no_root_spots", "message": "No available root spots in destination"},
                        status_code=409,  # Conflict/No space
                    )

                # Transfer failed - try to restore to source tank
                restored_entity = deserialize_entity(entity_data, source_manager.world)
                if restored_entity:
                    source_manager.world.engine.add_entity(restored_entity)

                # Log failed transfer
                log_transfer_failure(
                    entity_data=entity_data,
                    old_id=entity_id,
                    source_tank_id=source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    dest_tank_id=destination_tank_id,
                    dest_tank_name=dest_manager.tank_info.name,
                    error=outcome.error.message if outcome.error else "Failed to deserialize entity in destination tank",
                )

                return JSONResponse(
                    {"error": outcome.error.message if outcome.error else "Failed to deserialize entity in destination tank"},
                    status_code=500,
                )

            new_entity = outcome.value
            dest_manager.world.engine.add_entity(new_entity)

            # Record migration inflow for Fish entities
            if entity_data.get("type") == "fish" and dest_manager.world.ecosystem:
                 dest_manager.world.ecosystem.record_energy_gain("migration_in", new_entity.energy)

            logger.info(f"Added entity {new_entity.id} to tank {destination_tank_id[:8]} (was {entity_id})")

            # Invalidate cached state so websocket clients see updated stats immediately
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
                logger.debug("Failed to invalidate runner caches after transfer", exc_info=True)

            # Log successful transfer
            log_transfer_success(
                entity_data=entity_data,
                old_id=entity_id,
                new_id=new_entity.id,
                source_tank_id=source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                dest_tank_id=destination_tank_id,
                dest_tank_name=dest_manager.tank_info.name,
            )

            return JSONResponse({
                "success": True,
                "message": "Entity transferred successfully",
                "entity": {
                    "old_id": entity_id,
                    "new_id": new_entity.id,
                    "type": entity_data["type"],
                    "source_tank": source_tank_id,
                    "destination_tank": destination_tank_id,
                },
            })
        except Exception as e:
            logger.error(f"Transfer failed: {e}", exc_info=True)

            # Log failed transfer
            log_transfer_failure(
                entity_data=entity_data,
                old_id=entity_id,
                source_tank_id=source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                dest_tank_id=destination_tank_id,
                dest_tank_name=dest_manager.tank_info.name,
                error=str(e),
            )

            return JSONResponse(
                {"error": f"Transfer failed: {str(e)}"},
                status_code=500,
            )

    @router.post("/api/remote-transfer")
    async def remote_transfer_entity(request: RemoteTransferRequest):
        """Receive an entity from a remote server for cross-server migration.

        This endpoint is called by remote servers to transfer entities to this server.

        Args:
            request: Remote transfer request containing destination tank, entity data, and source info

        Returns:
            Success message with new entity ID, or error
        """
        destination_tank_id = request.destination_tank_id
        entity_data = request.entity_data
        source_server_id = request.source_server_id
        source_tank_id = request.source_tank_id

        # Construct remote source identifiers
        remote_source_id = f"{source_server_id}:{source_tank_id}"
        remote_source_name = f"Remote tank on {source_server_id}"

        # Get destination tank
        dest_manager = tank_registry.get_tank(destination_tank_id)
        if dest_manager is None:
            return JSONResponse(
                {"error": f"Destination tank not found: {destination_tank_id}"},
                status_code=404,
            )

        # Check if destination tank allows transfers
        if not dest_manager.tank_info.allow_transfers:
            return JSONResponse(
                {
                    "error": f"Tank '{dest_manager.tank_info.name}' does not allow entity transfers"
                },
                status_code=403,
            )

        try:
            # Deserialize and add to destination tank
            from backend.entity_transfer import try_deserialize_entity
            outcome = try_deserialize_entity(entity_data, dest_manager.world)
            if not outcome.ok:
                # SILENT FAIL check
                if outcome.error and outcome.error.code == "no_root_spots":
                    # No log_transfer_failure call here
                    return JSONResponse(
                        {"error": "no_root_spots", "message": "No available root spots"},
                        status_code=409,
                    )

                # Log failed transfer
                log_transfer_failure(
                    entity_data=entity_data,
                    old_id=entity_data.get("id", -1),
                    source_tank_id=remote_source_id,
                    source_tank_name=remote_source_name,
                    dest_tank_id=destination_tank_id,
                    dest_tank_name=dest_manager.tank_info.name,
                    error=outcome.error.message if outcome.error else "Failed to deserialize entity",
                )

                return JSONResponse(
                    {"error": outcome.error.message if outcome.error else "Failed to deserialize entity"},
                    status_code=500,
                )

            new_entity = outcome.value
            dest_manager.world.engine.add_entity(new_entity)

            # Record migration inflow for Fish entities
            if entity_data.get("type") == "fish" and dest_manager.world.ecosystem:
                 dest_manager.world.ecosystem.record_energy_gain("migration_in", new_entity.energy)

            # Invalidate cached state so websocket clients see updated stats immediately
            try:
                dest_runner = getattr(dest_manager, "_runner", None)
                if dest_runner and hasattr(dest_runner, "invalidate_state_cache"):
                    dest_runner.invalidate_state_cache()
                elif dest_runner and hasattr(dest_runner, "_invalidate_state_cache"):
                    dest_runner._invalidate_state_cache()
            except Exception:
                logger.debug("Failed to invalidate runner cache after remote transfer", exc_info=True)

            # Get entity ID based on type
            entity_id = getattr(new_entity, 'fish_id', None) or getattr(new_entity, 'plant_id', None) or getattr(new_entity, 'id', None)

            logger.info(
                f"Remote transfer: Added entity {entity_id} from {source_server_id}:{source_tank_id[:8]} "
                f"to {destination_tank_id[:8]} (was {entity_data.get('id', '?')})"
            )

            # Log successful transfer
            log_transfer_success(
                entity_data=entity_data,
                old_id=entity_data.get("id", -1),
                new_id=entity_id,
                source_tank_id=remote_source_id,
                source_tank_name=remote_source_name,
                dest_tank_id=destination_tank_id,
                dest_tank_name=dest_manager.tank_info.name,
            )

            return JSONResponse(
                {
                    "success": True,
                    "message": "Entity transferred successfully from remote server",
                    "entity": {
                        "old_id": entity_data.get("id", -1),
                        "new_id": entity_id,
                        "type": entity_data.get("type", "unknown"),
                        "source_server": source_server_id,
                        "source_tank": source_tank_id,
                        "destination_tank": destination_tank_id,
                    },
                }
            )
        except Exception as e:
            logger.error(f"Remote transfer failed: {e}", exc_info=True)

            # Log failed transfer
            log_transfer_failure(
                entity_data=entity_data,
                old_id=entity_data.get("id", -1),
                source_tank_id=remote_source_id,
                source_tank_name=remote_source_name,
                dest_tank_id=destination_tank_id,
                dest_tank_name=dest_manager.tank_info.name if dest_manager else "Unknown",
                error=str(e),
            )

            return JSONResponse(
                {"error": f"Remote transfer failed: {str(e)}"},
                status_code=500,
            )

    @router.get("/api/transfers")
    async def get_transfers(limit: int = 50, tank_id: Optional[str] = None, success_only: bool = False):
        """Get transfer history.

        Args:
            limit: Maximum number of records to return (default 50)
            tank_id: Filter by tank ID (source or destination)
            success_only: Only return successful transfers

        Returns:
            List of transfer records
        """
        from backend.transfer_history import get_transfer_history

        transfers = get_transfer_history(limit=limit, tank_id=tank_id, success_only=success_only)
        return JSONResponse({
            "transfers": transfers,
            "count": len(transfers),
        })

    @router.get("/api/transfers/{transfer_id}")
    async def get_transfer(transfer_id: str):
        """Get a specific transfer by ID.

        Args:
            transfer_id: The transfer UUID

        Returns:
            Transfer record or 404 if not found
        """
        from backend.transfer_history import get_transfer_by_id

        transfer = get_transfer_by_id(transfer_id)
        if transfer is None:
            return JSONResponse({"error": f"Transfer not found: {transfer_id}"}, status_code=404)

        return JSONResponse(transfer)

    @router.get("/api/connections")
    async def list_connections(tank_id: Optional[str] = None):
        """List tank connections.

        Args:
            tank_id: Optional tank ID to filter by

        Returns:
            List of connections
        """
        if tank_id:
            connections = connection_manager.get_connections_for_tank(tank_id)
        else:
            connections = connection_manager.list_connections()

        return JSONResponse({
            "connections": [c.to_dict() for c in connections],
            "count": len(connections),
        })

    @router.post("/api/connections")
    async def create_connection(connection_data: Dict):
        """Create or update a tank connection.

        Args:
            connection_data: Connection data (sourceId, destinationId, probability, direction)

        Returns:
            The created connection
        """
        try:
            connection = TankConnection.from_dict(connection_data)
            connection_manager.add_connection(connection)

            # Save connections to disk
            try:
                from backend.connection_persistence import save_connections
                save_connections(connection_manager)
            except Exception as save_error:
                logger.warning(f"Failed to save connections after create: {save_error}")

            return JSONResponse(connection.to_dict())
        except Exception as e:
            logger.error(f"Error creating connection: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=400)

    @router.delete("/api/connections/{connection_id}")
    async def delete_connection(connection_id: str):
        """Delete a tank connection.

        Args:
            connection_id: The connection ID to delete

        Returns:
            Success message
        """
        if connection_manager.remove_connection(connection_id):
            # Save connections to disk
            try:
                from backend.connection_persistence import save_connections
                save_connections(connection_manager)
            except Exception as save_error:
                logger.warning(f"Failed to save connections after delete: {save_error}")

            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Connection not found"}, status_code=404)

    return router
