"""Tank inspection operations (lineage, evaluation, benchmark, stats, snapshot)."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


def setup_inspection_subrouter(
    router: APIRouter,
    tank_registry: TankRegistry,
) -> None:
    """Attach inspection endpoints to the router.

    Endpoints:
        GET /api/tanks/{tank_id}/evaluation-history
        GET /api/tanks/{tank_id}/evolution-benchmark
        GET /api/tanks/{tank_id}/lineage
        GET /api/tanks/{tank_id}/snapshot
        GET /api/tanks/{tank_id}/transfer-stats
    """

    @router.get("/{tank_id}/evaluation-history")
    async def get_tank_evaluation_history(tank_id: str):
        """Get the full auto-evaluation history for a specific tank."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )
        return JSONResponse(manager.runner.get_full_evaluation_history())

    @router.get("/{tank_id}/evolution-benchmark")
    async def get_tank_evolution_benchmark(tank_id: str):
        """Get evolution benchmark tracking data for a specific tank."""
        manager = tank_registry.get_tank(tank_id)
        if manager is None:
            return JSONResponse(
                {"error": f"Tank not found: {tank_id}"},
                status_code=404,
            )

        data = manager.runner.get_evolution_benchmark_data()
        if isinstance(data, dict):
            data = {
                **data,
                "tank_id": manager.tank_id,
                "tank_name": manager.tank_info.name,
            }
        return JSONResponse(data)

    @router.get("/{tank_id}/lineage")
    async def get_tank_lineage(tank_id: str):
        """Get phylogenetic lineage data for a specific tank."""
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
        """Get a single state snapshot for a tank (for thumbnails)."""
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
        """Get transfer statistics for a tank."""
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
