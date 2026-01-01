"""Tank persistence operations (save, load, snapshots)."""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.routers.world_guards import get_tank_manager_or_error
from backend.tank_registry import CreateTankRequest, TankRegistry
from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def setup_persistence_subrouter(
    router: APIRouter,
    tank_registry: TankRegistry,
    world_manager: Optional[WorldManager] = None,
) -> None:
    """Attach persistence endpoints to the router.

    Endpoints:
        POST /api/tanks/{tank_id}/save
        POST /api/tanks/load
        GET /api/tanks/{tank_id}/snapshots
        DELETE /api/tanks/{tank_id}/snapshots/{snapshot_filename}
    """

    @router.post("/{tank_id}/save")
    async def save_tank(tank_id: str, request: Request):
        """Save tank state to a snapshot file."""
        from backend.tank_persistence import cleanup_old_snapshots, save_tank_state

        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        # Save the tank state
        snapshot_path = save_tank_state(tank_id, manager)
        if snapshot_path is None:
            return JSONResponse({"error": "Failed to save tank state"}, status_code=500)

        # Cleanup old snapshots (keep last 10)
        cleanup_old_snapshots(tank_id, max_snapshots=10)

        return JSONResponse({
            "success": True,
            "message": "Tank saved successfully",
            "snapshot_path": snapshot_path,
            "tank_id": tank_id,
        })

    @router.post("/load")
    async def load_tank(snapshot_path: str):
        """Load a tank from a snapshot file."""
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

        new_manager = tank_registry.create_tank(
            name=create_request.name,
            description=create_request.description,
            seed=create_request.seed,
            owner=create_request.owner,
            is_public=create_request.is_public,
            allow_transfers=create_request.allow_transfers,
            tank_id=create_request.tank_id,
        )
        if new_manager is None:
            return JSONResponse({"error": "Failed to create tank"}, status_code=500)

        # Restore state into the new tank
        if not restore_tank_from_snapshot(snapshot, new_manager.world):
            # Cleanup failed tank
            tank_registry.remove_tank(tank_id)
            return JSONResponse({"error": "Failed to restore tank state"}, status_code=500)

        return JSONResponse({
            "success": True,
            "message": "Tank loaded successfully",
            "tank_id": tank_id,
            "frame": snapshot["frame"],
            "entity_count": len(snapshot["entities"]),
        })

    @router.get("/{tank_id}/snapshots")
    async def list_snapshots(tank_id: str, request: Request):
        """List all available snapshots for a tank."""
        from backend.tank_persistence import list_tank_snapshots

        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        snapshots = list_tank_snapshots(tank_id)
        return JSONResponse({
            "tank_id": tank_id,
            "snapshots": snapshots,
            "count": len(snapshots),
        })

    @router.delete("/{tank_id}/snapshots/{snapshot_filename}")
    async def delete_tank_snapshot(tank_id: str, snapshot_filename: str, request: Request):
        """Delete a specific snapshot file."""
        from backend.tank_persistence import DATA_DIR, delete_snapshot

        manager, error = get_tank_manager_or_error(
            tank_registry,
            tank_id,
            request=request,
            world_manager=world_manager,
        )
        if error is not None:
            return error

        # Build snapshot path
        snapshot_path = DATA_DIR / tank_id / "snapshots" / snapshot_filename

        # Validate filename to prevent directory traversal
        try:
            snapshot_path.relative_to(DATA_DIR / tank_id / "snapshots")
        except ValueError:
            return JSONResponse({"error": "Invalid snapshot filename"}, status_code=400)

        if not snapshot_path.exists():
            return JSONResponse({"error": f"Snapshot not found: {snapshot_filename}"}, status_code=404)

        if delete_snapshot(str(snapshot_path)):
            return JSONResponse({"message": f"Snapshot {snapshot_filename} deleted"})
        else:
            return JSONResponse({"error": "Failed to delete snapshot"}, status_code=500)
