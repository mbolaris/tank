"""Single-solution lookup by ID (prefix match).

``GET /{solution_id}`` is a catch-all for any single path segment under the
solutions prefix, so this module's router must be attached *after*
``reports``'s (see the note there and in ``solutions/__init__.py``).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.solutions import SolutionTracker

logger = logging.getLogger(__name__)


def register(router: APIRouter, tracker: SolutionTracker) -> None:
    """Attach the single-solution lookup endpoint to ``router``."""

    @router.get("/{solution_id}")
    async def get_solution(solution_id: str):
        """Get details of a specific solution.

        Args:
            solution_id: The solution ID (or prefix)

        Returns:
            Full solution record
        """
        try:
            solutions = tracker.load_all_solutions()
            for sol in solutions:
                if sol.metadata.solution_id.startswith(solution_id):
                    return JSONResponse(sol.to_dict())

            raise HTTPException(status_code=404, detail=f"Solution not found: {solution_id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting solution {solution_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
