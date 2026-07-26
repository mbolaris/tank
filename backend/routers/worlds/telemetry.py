"""Per-world observability endpoints: benchmark data and lineage."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.world_manager import WorldManager

logger = logging.getLogger(__name__)


def register(router: APIRouter, world_manager: WorldManager) -> None:
    """Attach per-world telemetry endpoints to ``router``."""

    @router.get("/{world_id}/evolution-benchmark")
    async def get_evolution_benchmark(world_id: str):
        """Get evolution benchmark data for a world.

        Args:
            world_id: The world ID

        Returns:
            Benchmark history, latest snapshot, and improvement metrics
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        data = instance.runner.get_evolution_benchmark_data()
        return JSONResponse(data)

    @router.get("/{world_id}/lineage")
    async def get_world_lineage(world_id: str):
        """Get lineage data for phylogenetic tree visualization.

        Args:
            world_id: The world ID

        Returns:
            List of lineage records with parent-child relationships
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        # Access the lineage data through the runner's world ecosystem
        try:
            runner = instance.runner
            # SimulationRunner has self.world with ecosystem
            if hasattr(runner, "world") and hasattr(runner.world, "ecosystem"):
                ecosystem = runner.world.ecosystem
                if hasattr(ecosystem, "get_lineage_data"):
                    # Get alive fish IDs for enrichment
                    alive_fish_ids = None
                    if hasattr(runner.world, "entities_list"):
                        # Use snapshot_type for generic entity classification
                        alive_fish_ids = {
                            e.fish_id
                            for e in runner.world.entities_list
                            if getattr(e, "snapshot_type", None) == "fish"
                        }
                    lineage_data = ecosystem.get_lineage_data(alive_fish_ids)
                    return JSONResponse(lineage_data)

            # Fallback: lineage not available for this world type
            return JSONResponse([])
        except Exception as e:
            logger.error(f"Error getting lineage data: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error getting lineage data: {e}") from e
