"""Solution management API endpoints.

This router provides endpoints for:
- Listing all submitted solutions
- Getting solution details
- Capturing best solutions from simulations
- Submitting solutions
- Viewing leaderboards and comparisons

The endpoint implementations are split across sibling modules by concern;
this module only creates the shared tracker/benchmark instances and
assembles the sub-routers in the order route-matching requires.
"""

from fastapi import APIRouter

from backend.routers.solutions import capture, catalog, detail, lifecycle, reports
from backend.world_manager import WorldManager
from core.solutions import SolutionBenchmark, SolutionTracker
from core.solutions.benchmark import SolutionBenchmarkConfig


def create_solutions_router(world_manager: WorldManager) -> APIRouter:
    """Create the solutions API router.

    Args:
        world_manager: Manager for all worlds

    Returns:
        FastAPI router with solution endpoints
    """
    router = APIRouter(prefix="/api/solutions", tags=["solutions"])

    # Shared tracker and benchmark instances
    tracker = SolutionTracker()
    benchmark = SolutionBenchmark(
        SolutionBenchmarkConfig(
            hands_per_opponent=200,
            num_duplicate_sets=10,
        )
    )

    catalog.register(router, tracker)
    # `reports` owns the literal single-path-segment routes ("/leaderboard",
    # "/compare", "/report"). It must be registered before `detail`, whose
    # "/{solution_id}" is a same-segment-count catch-all: Starlette matches
    # routes in registration order, so registering the catch-all first would
    # shadow these literal routes and make them permanently unreachable
    # (verified against the pre-split router — see the note in reports.py).
    reports.register(router, tracker, benchmark)
    detail.register(router, tracker)
    capture.register(router, world_manager, tracker, benchmark)
    lifecycle.register(router, tracker, benchmark)

    return router
