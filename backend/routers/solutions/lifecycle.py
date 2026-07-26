"""Endpoints that evaluate or submit an already-captured solution."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from backend.routers.solutions.models import SubmitRequest
from core.solutions import SolutionBenchmark, SolutionTracker

logger = logging.getLogger(__name__)


def register(router: APIRouter, tracker: SolutionTracker, benchmark: SolutionBenchmark) -> None:
    """Attach the evaluate/submit endpoints to ``router``."""

    @router.post("/evaluate/{solution_id}")
    async def evaluate_solution(solution_id: str, background_tasks: BackgroundTasks):
        """Evaluate a solution against benchmark opponents.

        Args:
            solution_id: The solution to evaluate

        Returns:
            Status message (evaluation runs in background)
        """
        try:
            solutions = tracker.load_all_solutions()
            target = None
            for sol in solutions:
                if sol.metadata.solution_id.startswith(solution_id):
                    target = sol
                    break

            if target is None:
                raise HTTPException(status_code=404, detail=f"Solution not found: {solution_id}")

            def run_evaluation():
                result = benchmark.evaluate_solution(target, verbose=True)
                target.benchmark_result = result
                tracker.save_solution(target)
                logger.info(f"Evaluation complete for {solution_id}: Elo {result.elo_rating:.0f}")

            background_tasks.add_task(run_evaluation)

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Evaluation started for {target.metadata.name}",
                    "solution_id": target.metadata.solution_id,
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error evaluating solution {solution_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.post("/submit")
    async def submit_solution(request: SubmitRequest):
        """Submit a solution to git.

        Args:
            request: Submit configuration

        Returns:
            Success status
        """
        try:
            solutions = tracker.load_all_solutions()
            target = None
            for sol in solutions:
                if sol.metadata.solution_id.startswith(request.solution_id):
                    target = sol
                    break

            if target is None:
                raise HTTPException(
                    status_code=404, detail=f"Solution not found: {request.solution_id}"
                )

            success = tracker.submit_to_git(
                target,
                commit_message=request.commit_message,
                push=request.push,
            )

            if success:
                return JSONResponse(
                    {
                        "success": True,
                        "message": f"Solution {target.metadata.name} submitted to git",
                        "solution_id": target.metadata.solution_id,
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to submit to git")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting solution: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
