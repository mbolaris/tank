"""Tank management API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.tank_registry import TankRegistry, CreateTankRequest

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/tanks", tags=["tanks"])


def setup_router(
    tank_registry: TankRegistry,
    server_id: str,
    start_broadcast_callback,
    stop_broadcast_callback,
) -> APIRouter:
    """Setup the tanks router with required dependencies.

    Args:
        tank_registry: The tank registry instance
        server_id: The local server ID
        start_broadcast_callback: Callback to start broadcast for a tank
        stop_broadcast_callback: Callback to stop broadcast for a tank

    Returns:
        Configured APIRouter
    """

    @router.get("")
    async def list_tanks(include_private: bool = False):
        """List all tanks in the registry.

        Args:
            include_private: If True, include non-public tanks

        Returns:
            List of tank status objects
        """
        tanks = tank_registry.list_tanks(include_private=include_private)
        return JSONResponse({
            "tanks": tanks,
            "count": len(tanks),
            "default_tank_id": tank_registry.default_tank_id,
        })

    @router.post("")
    async def create_tank(
        name: str,
        description: str = "",
        seed: Optional[int] = None,
        owner: Optional[str] = None,
        is_public: bool = True,
        allow_transfers: bool = True,
        server_id_param: str = "local-server",
    ):
        """Create a new tank simulation.

        Args:
            name: Human-readable name for the tank
            description: Description of the tank
            seed: Optional random seed for deterministic behavior
            owner: Optional owner identifier
            is_public: Whether the tank is publicly visible
            allow_transfers: Whether to allow entity transfers
            server_id_param: Which server to create the tank on (default: local-server)

        Returns:
            The created tank's status
        """
        try:
            # Validate server_id - for now, only local-server is supported
            if server_id_param != server_id:
                return JSONResponse(
                    {
                        "error": f"Invalid server_id: {server_id_param}. "
                        f"Only '{server_id}' is supported in this version."
                    },
                    status_code=400,
                )

            manager = tank_registry.create_tank(
                name=name,
                description=description,
                seed=seed,
                owner=owner,
                is_public=is_public,
                allow_transfers=allow_transfers,
                server_id=server_id_param,
            )

            # Inject connection manager and tank registry for migrations
            from backend.connection_manager import ConnectionManager
            if hasattr(tank_registry, '_connection_manager'):
                manager.runner.connection_manager = tank_registry._connection_manager
            manager.runner.tank_registry = tank_registry
            manager.runner.tank_id = manager.tank_id
            manager.runner._update_environment_migration_context()

            # Start the simulation
            manager.start(start_paused=True)

            # Start broadcast task for the new tank
            await start_broadcast_callback(manager)

            logger.info(f"Created new tank via API: {manager.tank_id[:8]} ({name}) on server {server_id_param}")

            return JSONResponse(manager.get_status(), status_code=201)
        except Exception as e:
            logger.error(f"Error creating tank: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @router.get("/{tank_id}")
    async def get_tank(tank_id: str):
        """Get information about a specific tank.

        Args:
            tank_id: The unique tank identifier

        Returns:
            Tank status or 404 if not found
        """
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )
        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/pause")
    async def pause_tank(tank_id: str):
        """Pause a running tank simulation."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)
        if not manager.running:
            return JSONResponse({"error": "Tank is not running"}, status_code=400)

        manager.world.paused = True
        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/resume")
    async def resume_tank(tank_id: str):
        """Resume a paused tank simulation."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)
        if not manager.running:
            return JSONResponse({"error": "Tank is not running"}, status_code=400)

        manager.world.paused = False

        # Ensure broadcast task exists for this tank
        await start_broadcast_callback(manager)

        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/start")
    async def start_tank(tank_id: str):
        """Start a stopped tank simulation."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        if not manager.running:
            manager.start(start_paused=False)

        await start_broadcast_callback(manager)

        return JSONResponse(manager.get_status())

    @router.post("/{tank_id}/stop")
    async def stop_tank(tank_id: str):
        """Stop a running tank simulation and its broadcast task."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        await stop_broadcast_callback(tank_id)

        if manager.running:
            manager.stop()

        manager.world.paused = True

        return JSONResponse(manager.get_status())

    @router.delete("/{tank_id}")
    async def delete_tank(tank_id: str):
        """Delete a tank from the registry.

        Args:
            tank_id: The tank ID to delete

        Returns:
            Success message or 404 if not found
        """
        # Don't allow deleting the default tank
        if tank_id == tank_registry.default_tank_id and tank_registry.tank_count == 1:
            return JSONResponse(
                {"error": "Cannot delete the last remaining tank"},
                status_code=400,
            )

        # Stop broadcast first
        await stop_broadcast_callback(tank_id)

        # Remove from registry
        if tank_registry.remove_tank(tank_id):
            logger.info(f"Deleted tank via API: {tank_id[:8]}")
            return JSONResponse({"message": f"Tank {tank_id} deleted"})
        else:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )

    @router.post("/{tank_id}/save")
    async def save_tank(tank_id: str):
        """Save tank state to a snapshot file.

        Args:
            tank_id: The tank ID to save

        Returns:
            Success message with snapshot info, or error
        """
        from backend.tank_persistence import save_tank_state, cleanup_old_snapshots

        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        # Save the tank state
        snapshot_path = save_tank_state(tank_id, manager)
        if snapshot_path is None:
            return JSONResponse({"error": "Failed to save tank state"}, status_code=500)

        # Cleanup old snapshots (keep last 10)
        cleanup_old_snapshots(tank_id, max_snapshots=10)

        return JSONResponse({
            "success": True,
            "message": f"Tank saved successfully",
            "snapshot_path": snapshot_path,
            "tank_id": tank_id,
        })

    @router.post("/load")
    async def load_tank(snapshot_path: str):
        """Load a tank from a snapshot file.

        Args:
            snapshot_path: Path to the snapshot file

        Returns:
            Success message with tank info, or error
        """
        from backend.tank_persistence import load_tank_state, restore_tank_from_snapshot

        # Load snapshot data
        snapshot = load_tank_state(snapshot_path)
        if snapshot is None:
            return JSONResponse({"error": "Failed to load snapshot"}, status_code=400)

        # Extract metadata
        tank_id = snapshot["tank_id"]
        metadata = snapshot["metadata"]

        # Check if tank already exists
        existing_manager = tank_registry.get_tank(tank_id)
        if existing_manager is not None:
            return JSONResponse(
                {"error": f"Tank {tank_id} already exists. Delete it first or use a different snapshot."},
                status_code=409,
            )

        # Create new tank with same ID and metadata
        create_request = CreateTankRequest(
            tank_id=tank_id,
            name=metadata["name"],
            description=metadata.get("description", ""),
            seed=metadata.get("seed"),
            owner=metadata.get("owner"),
            is_public=metadata.get("is_public", True),
            allow_transfers=metadata.get("allow_transfers", True),
        )

        new_manager = tank_registry.create_tank(create_request)
        if new_manager is None:
            return JSONResponse({"error": "Failed to create tank"}, status_code=500)

        # Restore state into the new tank
        if not restore_tank_from_snapshot(snapshot, new_manager.world):
            # Cleanup failed tank
            tank_registry.remove_tank(tank_id)
            return JSONResponse({"error": "Failed to restore tank state"}, status_code=500)

        return JSONResponse({
            "success": True,
            "message": f"Tank loaded successfully",
            "tank_id": tank_id,
            "frame": snapshot["frame"],
            "entity_count": len(snapshot["entities"]),
        })

    @router.get("/{tank_id}/snapshots")
    async def list_snapshots(tank_id: str):
        """List all available snapshots for a tank.

        Args:
            tank_id: The tank ID

        Returns:
            List of snapshot metadata
        """
        from backend.tank_persistence import list_tank_snapshots

        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        snapshots = list_tank_snapshots(tank_id)
        return JSONResponse({
            "tank_id": tank_id,
            "snapshots": snapshots,
            "count": len(snapshots),
        })

    @router.delete("/{tank_id}/snapshots/{snapshot_filename}")
    async def delete_tank_snapshot(tank_id: str, snapshot_filename: str):
        """Delete a specific snapshot file.

        Args:
            tank_id: The tank ID
            snapshot_filename: Name of the snapshot file to delete

        Returns:
            Success message or error
        """
        from backend.tank_persistence import delete_snapshot, DATA_DIR

        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        # Build snapshot path
        snapshot_path = DATA_DIR / tank_id / "snapshots" / snapshot_filename

        # Validate filename to prevent directory traversal
        if not snapshot_path.is_relative_to(DATA_DIR / tank_id / "snapshots"):
            return JSONResponse({"error": "Invalid snapshot filename"}, status_code=400)

        if not snapshot_path.exists():
            return JSONResponse({"error": f"Snapshot not found: {snapshot_filename}"}, status_code=404)

        if delete_snapshot(str(snapshot_path)):
            return JSONResponse({"message": f"Snapshot {snapshot_filename} deleted"})
        else:
            return JSONResponse({"error": "Failed to delete snapshot"}, status_code=500)

    @router.get("/{tank_id}/lineage")
    async def get_tank_lineage(tank_id: str):
        """Get phylogenetic lineage data for a specific tank.

        Args:
            tank_id: The tank ID to get lineage for

        Returns:
            List of lineage records or 404 if tank not found
        """
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )

        try:
            from core.entities import Fish
            alive_fish_ids = {
                fish.fish_id for fish in manager.world.entities_list
                if isinstance(fish, Fish)
            }
            lineage_data = manager.world.ecosystem.get_lineage_data(alive_fish_ids)
            return JSONResponse(lineage_data)
        except Exception as e:
            logger.error(f"Error getting lineage data for tank {tank_id[:8]}: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @router.get("/{tank_id}/snapshot")
    async def get_tank_snapshot(tank_id: str):
        """Get a single state snapshot for a tank (for thumbnails).

        Args:
            tank_id: The tank ID to get snapshot for

        Returns:
            Current simulation state or 404 if tank not found
        """
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )

        try:
            # Get current state (force full state, no delta)
            state = manager.get_state(force_full=True, allow_delta=False)
            return JSONResponse(state.to_dict())
        except Exception as e:
            logger.error(f"Error getting snapshot for tank {tank_id[:8]}: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @router.get("/{tank_id}/transfer-stats")
    async def get_tank_transfer_stats(tank_id: str):
        """Get transfer statistics for a tank.

        Args:
            tank_id: The tank ID

        Returns:
            Transfer statistics
        """
        from backend.transfer_history import get_tank_transfer_stats

        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

        stats = get_tank_transfer_stats(tank_id)
        return JSONResponse({
            "tank_id": tank_id,
            "tank_name": manager.tank_info.name,
            **stats,
        })

    return router
