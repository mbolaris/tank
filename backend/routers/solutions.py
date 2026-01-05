"""Solution management API endpoints.

This router provides endpoints for:
- Listing all submitted solutions
- Getting solution details
- Capturing best solutions from simulations
- Submitting solutions
- Viewing leaderboards and comparisons
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.world_manager import WorldManager
from core.solutions import SolutionBenchmark, SolutionTracker
from core.solutions.benchmark import SolutionBenchmarkConfig

logger = logging.getLogger(__name__)


class CaptureRequest(BaseModel):
    """Request to capture a solution from a tank."""

    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    evaluate: bool = False

    # How to choose the fish to capture from the live tank.
    # - heuristic_elo: existing fast heuristic (default)
    # - tournament: evaluate a candidate pool head-to-head vs best submitted solutions
    selection_mode: Literal["heuristic_elo", "tournament"] = "heuristic_elo"

    # Tournament selection tuning (only used when selection_mode="tournament")
    candidate_pool_size: int = 12
    hands_per_matchup: int = 500
    opponent_limit: int = 8


class SubmitRequest(BaseModel):
    """Request to submit a solution to git."""

    solution_id: str
    commit_message: Optional[str] = None
    push: bool = True


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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/capture/{tank_id}")
    async def capture_solution(
        tank_id: str,
        request: CaptureRequest,
        background_tasks: BackgroundTasks,
    ):
        """Capture the best solution from a running tank.

        Args:
            tank_id: The tank to capture from
            request: Capture configuration

        Returns:
            The captured solution record
        """
        instance = world_manager.get_world(tank_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {tank_id}")

        try:
            # Get the best fish from the world
            from core.entities import Fish

            runner = instance.runner
            world = getattr(runner, "world", None)
            if not world:
                raise HTTPException(status_code=400, detail="World has no entities")

            entities_list = getattr(world, "entities_list", [])
            fish_list = [e for e in entities_list if isinstance(e, Fish)]

            if not fish_list:
                raise HTTPException(status_code=400, detail="No fish in tank")

            selection_detail = {}

            if request.selection_mode == "tournament":
                # Select opponents: best solution per author (by existing Elo), limited to top-N.
                all_solutions = tracker.load_all_solutions()
                by_author = {}
                for sol in all_solutions:
                    author = (sol.metadata.author or "unknown").strip() or "unknown"
                    current = by_author.get(author)
                    current_elo = (
                        current.benchmark_result.elo_rating
                        if current and current.benchmark_result
                        else 0.0
                    )
                    sol_elo = sol.benchmark_result.elo_rating if sol.benchmark_result else 0.0
                    if current is None or sol_elo > current_elo:
                        by_author[author] = sol

                opponents = list(by_author.values())
                opponents.sort(
                    key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0.0,
                    reverse=True,
                )
                opponents = opponents[: max(1, request.opponent_limit)]

                best_fish = tracker.identify_best_fish_for_tournament(
                    fish_list,
                    opponents,
                    candidate_pool_size=request.candidate_pool_size,
                    hands_per_matchup=request.hands_per_matchup,
                    top_n=1,
                    verbose=False,
                )
                if not best_fish:
                    raise HTTPException(
                        status_code=400, detail="No fish with sufficient games for capture"
                    )

                fish, score = best_fish[0]
                selection_detail = {
                    "selection_mode": "tournament",
                    "tournament_avg_win_rate": score,
                    "candidate_pool_size": request.candidate_pool_size,
                    "hands_per_matchup": request.hands_per_matchup,
                    "opponents_used": len(opponents),
                }
            else:
                best_fish = tracker.identify_best_fish(fish_list, metric="elo", top_n=1)
                if not best_fish:
                    raise HTTPException(
                        status_code=400, detail="No fish with sufficient games for capture"
                    )

                fish, score = best_fish[0]
                selection_detail = {
                    "selection_mode": "heuristic_elo",
                    "estimated_elo": score,
                }

            # Capture the solution
            solution = tracker.capture_solution(
                fish,
                name=request.name,
                description=request.description,
                author=request.author or "TankWorld",
            )

            # Save immediately
            filepath = tracker.save_solution(solution)

            # Optionally evaluate in background
            if request.evaluate:

                def evaluate_and_save():
                    result = benchmark.evaluate_solution(solution, verbose=True)
                    solution.benchmark_result = result
                    tracker.save_solution(solution)

                background_tasks.add_task(evaluate_and_save)

            return JSONResponse(
                {
                    "success": True,
                    "solution_id": solution.metadata.solution_id,
                    "filepath": filepath,
                    "fish_id": fish.fish_id,
                    **selection_detail,
                    "evaluating": request.evaluate,
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error capturing solution from tank {tank_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))

    return router
