"""Endpoint capturing the best fish from a running world as a solution."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from backend.routers.solutions.models import CaptureRequest
from backend.world_manager import WorldManager
from core.solutions import SolutionBenchmark, SolutionTracker

logger = logging.getLogger(__name__)


def register(
    router: APIRouter,
    world_manager: WorldManager,
    tracker: SolutionTracker,
    benchmark: SolutionBenchmark,
) -> None:
    """Attach the solution-capture endpoint to ``router``."""

    @router.post("/capture/{world_id}")
    async def capture_solution(
        world_id: str,
        request: CaptureRequest,
        background_tasks: BackgroundTasks,
    ):
        """Capture the best solution from a running world.

        Args:
            world_id: The world to capture from
            request: Capture configuration

        Returns:
            The captured solution record
        """
        instance = world_manager.get_world(world_id)
        if instance is None:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        try:
            # Get the best fish from the world
            runner = instance.runner
            world = getattr(runner, "world", None)
            if not world:
                raise HTTPException(status_code=400, detail="World has no entities")

            entities_list = getattr(world, "entities_list", [])
            # Use snapshot_type for generic entity classification
            fish_list = [e for e in entities_list if getattr(e, "snapshot_type", None) == "fish"]

            if not fish_list:
                raise HTTPException(status_code=400, detail="No fish in world")

            selection_detail = {}

            if request.selection_mode == "tournament":
                # Select opponents: best solution per author (by existing Elo), limited to top-N.
                all_solutions = tracker.load_all_solutions()
                by_author: dict[str, Any] = {}
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
            logger.error(f"Error capturing solution from world {world_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
