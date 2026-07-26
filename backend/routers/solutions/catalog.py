"""Endpoint listing all submitted solutions."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.solutions import SolutionTracker

logger = logging.getLogger(__name__)


def register(router: APIRouter, tracker: SolutionTracker) -> None:
    """Attach the solution-listing endpoint to ``router``."""

    @router.get("")
    async def list_solutions():
        """List all submitted solutions.

        Returns:
            List of solution summaries with rankings
        """
        try:
            solutions = tracker.load_all_solutions()
            leaderboard = tracker.generate_leaderboard(solutions)
            return JSONResponse(
                {
                    "count": len(solutions),
                    "solutions": leaderboard,
                }
            )
        except Exception as e:
            logger.error(f"Error listing solutions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
