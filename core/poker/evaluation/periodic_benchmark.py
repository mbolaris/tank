"""Periodic benchmark evaluation for evolving poker strategies.

This module provides a hook that runs calibrated benchmark evaluations
periodically during simulation to track poker strategy evolution over time.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    BenchmarkSuiteResult,
    evaluate_vs_benchmark_suite,
)

if TYPE_CHECKING:
    from core.entities.fish import Fish


def _poker_net_energy(fish: "Fish") -> float:
    """Net poker energy (won - lost - house cuts) as the poker-skill proxy.

    ``fish.poker_stats`` is ``None`` until the fish has actually played poker.
    """
    stats = fish.poker_stats
    return stats.get_net_energy() if stats is not None else 0.0


@dataclass
class PeriodicBenchmarkEvaluator:
    """Manages periodic benchmark evaluations during simulation."""

    cfg: BenchmarkEvalConfig
    eval_interval_frames: int = 10_000

    last_eval_frame: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def maybe_run(
        self,
        frame: int,
        fish_population: list["Fish"],
    ) -> None:
        """Run evaluation if enough frames have passed.

        Args:
            frame: Current simulation frame
            fish_population: List of all fish in the ecosystem
        """
        if frame - self.last_eval_frame < self.eval_interval_frames:
            return

        # Rank by net poker energy (won - lost - house cuts); see _poker_net_energy.
        top_fish = sorted(fish_population, key=_poker_net_energy, reverse=True)[:10]

        for fish in top_fish:
            # Get poker strategy from fish
            # Fish may have poker_strategy directly or through behavior algorithm
            if hasattr(fish, "poker_strategy"):
                algo = fish.poker_strategy

            else:
                continue

            result: BenchmarkSuiteResult = evaluate_vs_benchmark_suite(algo, self.cfg)

            self.history.append(
                {
                    "frame": frame,
                    "fish_id": getattr(fish, "fish_id", id(fish)),
                    "algorithm_id": getattr(algo, "strategy_id", "unknown"),
                    "weighted_bb_per_100": result.weighted_bb_per_100,
                    "weighted_bb_ci_95": result.weighted_bb_per_100_ci_95,
                    "total_hands": result.total_hands,
                    "per_benchmark": {
                        bid: {
                            "bb_per_100": br.bb_per_100,
                            "bb_ci_95": br.bb_per_100_ci_95,
                            "hands_played": br.hands_played,
                            "significant": br.is_statistically_significant,
                        }
                        for bid, br in result.per_benchmark.items()
                    },
                }
            )

        self.last_eval_frame = frame

    def get_history(self) -> list[dict[str, Any]]:
        """Get evaluation history.

        Returns:
            List of evaluation records
        """
        return self.history

    def get_latest_results(self, n: int = 10) -> list[dict[str, Any]]:
        """Get most recent evaluation results.

        Args:
            n: Number of recent results to return

        Returns:
            List of most recent evaluation records
        """
        return self.history[-n:] if self.history else []
