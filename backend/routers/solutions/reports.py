"""Literal-path aggregate report endpoints: leaderboard, compare, report.

**Bug fix, not just a move.** In the pre-split monolith, these three routes
were registered *after* ``GET /{solution_id}`` (now ``detail.register``).
Starlette matches routes in registration order, and ``/{solution_id}`` is a
same-segment-count catch-all, so requests to ``/leaderboard``, ``/compare``,
and ``/report`` were always captured by the catch-all first and returned
``404 Solution not found: <name>`` instead of ever reaching these handlers —
confirmed via a TestClient probe against the pre-split router. They are
documented as working endpoints in ``solutions/README.md``. This module must
be registered before ``detail`` (see ``solutions/__init__.py``) so the routes
are actually reachable.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.solutions import SolutionBenchmark, SolutionTracker

logger = logging.getLogger(__name__)


def register(router: APIRouter, tracker: SolutionTracker, benchmark: SolutionBenchmark) -> None:
    """Attach the aggregate report endpoints to ``router``."""

    @router.get("/leaderboard")
    async def get_leaderboard():
        """Get the solution leaderboard.

        Returns:
            Ranked list of solutions by Elo rating
        """
        try:
            solutions = tracker.load_all_solutions()
            leaderboard = tracker.generate_leaderboard(solutions)
            return JSONResponse(
                {
                    "leaderboard": leaderboard,
                    "generated_at": solutions[0].metadata.submitted_at if solutions else None,
                }
            )
        except Exception as e:
            logger.error(f"Error generating leaderboard: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/compare")
    async def compare_solutions():
        """Compare all solutions and return rankings.

        Returns:
            Comparison results with head-to-head data
        """
        try:
            solutions = tracker.load_all_solutions()
            if len(solutions) < 2:
                return JSONResponse(
                    {
                        "message": "Need at least 2 solutions to compare",
                        "count": len(solutions),
                    }
                )

            # Only compare solutions that have been evaluated
            evaluated = [s for s in solutions if s.benchmark_result is not None]
            if len(evaluated) < 2:
                return JSONResponse(
                    {
                        "message": "Need at least 2 evaluated solutions to compare",
                        "evaluated_count": len(evaluated),
                        "total_count": len(solutions),
                    }
                )

            comparison = benchmark.compare_solutions(evaluated)
            return JSONResponse(comparison.to_dict())

        except Exception as e:
            logger.error(f"Error comparing solutions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/report")
    async def get_benchmark_report():
        """Generate a benchmark report for all solutions.

        Returns:
            Text report of solution rankings and performance
        """
        try:
            solutions = tracker.load_all_solutions()
            if not solutions:
                return JSONResponse(
                    {
                        "report": "No solutions found.",
                        "count": 0,
                    }
                )

            report = benchmark.generate_report(solutions)
            return JSONResponse(
                {
                    "report": report,
                    "count": len(solutions),
                }
            )

        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
