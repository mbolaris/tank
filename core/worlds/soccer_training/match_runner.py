"""Match runner for the soccer training world."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter


@dataclass
class MatchResult:
    frames: int
    score: Dict[str, int]
    team_fitness: Dict[str, float]
    agent_fitness: Dict[str, Dict[str, Any]]


ActionProvider = Callable[[int, SoccerTrainingWorldBackendAdapter], Optional[Dict[str, Any]]]


class SoccerMatchRunner:
    """Runs fixed-length or score-limited soccer training matches."""

    def __init__(self, world: SoccerTrainingWorldBackendAdapter) -> None:
        self.world = world

    def run(
        self,
        *,
        seed: Optional[int] = None,
        max_steps: int = 3000,
        goal_limit: Optional[int] = None,
        action_provider: Optional[ActionProvider] = None,
    ) -> MatchResult:
        self.world.reset(seed=seed)

        for step in range(max_steps):
            actions = action_provider(step, self.world) if action_provider else None
            self.world.step(actions_by_agent=actions)
            if goal_limit is not None:
                score = self.world.get_fitness_summary()["score"]
                if score["left"] >= goal_limit or score["right"] >= goal_limit:
                    break

        summary = self.world.get_fitness_summary()
        return MatchResult(
            frames=self.world.get_current_metrics()["frame"],
            score=summary["score"],
            team_fitness=summary["team_fitness"],
            agent_fitness=summary["agent_fitness"],
        )
