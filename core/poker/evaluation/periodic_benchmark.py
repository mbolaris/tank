"""Bounded, isolated live poker skill evaluation for evolving fish.

The evaluator reuses the frozen poker ladder used by
``benchmarks/poker/ladder_20k.py``.  It intentionally evaluates fresh strategy
copies and preserves Python's module-level random state because some legacy
strategies still use it internally.
"""

from __future__ import annotations

import copy
import importlib
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from random import Random
from typing import TYPE_CHECKING, Any

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    SingleBenchmarkResult,
    evaluate_vs_single_benchmark_duplicate,
)
from core.skill.ladder import RungResult, SkillLadderSummary, ladder_position_index
from core.skill.snapshots import SkillSnapshot, SkillSnapshotStore

if TYPE_CHECKING:
    from core.entities.fish import Fish

logger = logging.getLogger(__name__)
_RANDOM_MODULE = importlib.import_module("random")

POKER_LADDER_RUNGS: tuple[str, ...] = (
    "random",
    "loose_passive",
    "tight_aggressive",
    "gto_expert",
)
LIVE_HANDS_PER_MATCH = 50
LIVE_NUM_DUPLICATE_SETS = 5
LIVE_MAX_FISH_PER_PASS = 3
LIVE_HISTORY_MAX = 100


def _poker_net_energy(fish: Fish) -> float:
    """Return the fish's existing net poker energy for subject selection."""
    stats = fish.poker_stats
    return stats.get_net_energy() if stats is not None else 0.0


def make_live_benchmark_config(base_seed: int = 42) -> BenchmarkEvalConfig:
    """Build the reduced, frozen live poker ladder configuration."""
    return BenchmarkEvalConfig(
        hands_per_match=LIVE_HANDS_PER_MATCH,
        num_duplicate_sets=LIVE_NUM_DUPLICATE_SETS,
        base_seed=base_seed,
        benchmark_opponents=list(POKER_LADDER_RUNGS),
        benchmark_weights=dict.fromkeys(POKER_LADDER_RUNGS, 1.0),
    )


@contextmanager
def _preserve_global_random_state() -> Iterator[None]:
    """Keep legacy strategy calls from perturbing the simulation RNG stream."""
    state = _RANDOM_MODULE.getstate()
    try:
        yield
    finally:
        _RANDOM_MODULE.setstate(state)


def _clone_strategy(source: Any, seed: int) -> Any:
    """Reconstruct a strategy from serialized genes, never reuse the live object."""
    clone: Any
    try:
        data = source.to_dict()
        if data.get("type") == "ComposablePokerStrategy":
            from core.poker.strategy.composable import ComposablePokerStrategy

            clone = ComposablePokerStrategy.from_dict(data)
        else:
            from core.poker.strategy.implementations.base import PokerStrategyAlgorithm

            clone = PokerStrategyAlgorithm.from_dict(data)
    except (AttributeError, KeyError, TypeError, ValueError):
        # A few historical strategies do not expose a complete codec. Deep copy
        # is still isolated from the fish and is preferable to skipping a fish.
        clone = copy.deepcopy(source)

    clone.rng = Random(seed)
    return clone


@dataclass
class PeriodicBenchmarkEvaluator:
    """Evaluate top fish against the frozen poker ladder with bounded work."""

    cfg: BenchmarkEvalConfig = field(default_factory=make_live_benchmark_config)
    eval_interval_frames: int = 20_000
    last_eval_frame: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    store: SkillSnapshotStore = field(default_factory=SkillSnapshotStore)
    max_fish_per_pass: int = LIVE_MAX_FISH_PER_PASS
    history_max: int = LIVE_HISTORY_MAX
    phase_offset_frames: int | None = None

    def __post_init__(self) -> None:
        self.eval_interval_frames = max(1, int(self.eval_interval_frames))
        self.max_fish_per_pass = max(1, int(self.max_fish_per_pass))
        self.history_max = max(1, int(self.history_max))
        # A production caller supplies interval // 2 to stay off S1's cadence.
        # Direct callers retain the old first-run-at-interval behavior.
        self._next_eval_frame = max(
            1,
            (
                self.eval_interval_frames
                if self.phase_offset_frames is None
                else int(self.phase_offset_frames)
            ),
        )
        self._active = False
        self._eval_counter = 0
        self._subjects: list[Any] = []
        self._subject_index = 0
        self._rung_index = 0
        self._current_frame = 0
        self._current_results: dict[str, SingleBenchmarkResult] = {}

    @property
    def active(self) -> bool:
        """Whether a bounded multi-frame evaluation pass is in progress."""
        return self._active

    @staticmethod
    def _fish_strategy(fish: Any) -> Any | None:
        try:
            return fish.genome.behavioral.poker_strategy.value
        except AttributeError:
            # Compatibility for old restored entities with a missing trait.
            return fish.get_poker_strategy()

    def _top_fish(self, fish_population: list[Fish]) -> list[Any]:
        """Select individual poker-playing fish by net poker energy."""
        eligible = [fish for fish in fish_population if self._fish_strategy(fish) is not None]
        return sorted(eligible, key=_poker_net_energy, reverse=True)[: self.max_fish_per_pass]

    def maybe_run(self, frame: int, fish_population: list[Fish]) -> None:
        """Start or advance a pass, evaluating at most one fish/rung per call."""
        if self._active:
            self._advance(frame)
            return

        if frame < self._next_eval_frame:
            return

        subjects = self._top_fish(fish_population)
        if not subjects:
            self._next_eval_frame = frame + self.eval_interval_frames
            return

        self._active = True
        self.last_eval_frame = frame
        self._current_frame = frame
        self._eval_counter += 1
        self._subjects = subjects
        self._subject_index = 0
        self._rung_index = 0
        self._current_results = {}
        self._advance(frame)

    def _advance(self, frame: int) -> None:
        fish = self._subjects[self._subject_index]
        rung_id = POKER_LADDER_RUNGS[self._rung_index]
        result = self._evaluate_rung(fish, rung_id)
        self._current_results[rung_id] = result

        if self._rung_index + 1 < len(POKER_LADDER_RUNGS):
            self._rung_index += 1
            return

        self._record_subject(fish)
        if self._subject_index + 1 < len(self._subjects):
            self._subject_index += 1
            self._rung_index = 0
            self._current_results = {}
            return

        self._active = False
        self._subjects = []
        self._next_eval_frame = frame + self.eval_interval_frames

    def _evaluate_rung(self, fish: Any, rung_id: str) -> SingleBenchmarkResult:
        """Evaluate one fish/rung using a fresh strategy and private seeds."""
        fish_id = int(fish.fish_id)
        rung_index = POKER_LADDER_RUNGS.index(rung_id)
        seed = self.cfg.base_seed + self._eval_counter * 100_000 + fish_id * 100 + rung_index
        strategy = _clone_strategy(self._fish_strategy(fish), seed)
        cfg = replace(
            self.cfg,
            benchmark_opponents=[rung_id],
            benchmark_weights={rung_id: 1.0},
            base_seed=seed,
        )
        with _preserve_global_random_state():
            return evaluate_vs_single_benchmark_duplicate(strategy, rung_id, cfg)

    def _record_subject(self, fish: Any) -> None:
        fish_id = int(fish.fish_id)
        lineage_id = str(fish.parent_id if fish.parent_id is not None else fish.fish_id)
        rung_results: list[RungResult] = []
        per_benchmark: dict[str, dict[str, Any]] = {}

        for rung_index, rung_id in enumerate(POKER_LADDER_RUNGS):
            result = self._current_results[rung_id]
            beaten = result.is_statistically_significant and result.bb_per_100 > 0.0
            rung_results.append(
                RungResult(
                    rung=f"L{rung_index}",
                    rung_id=rung_id,
                    metric=result.bb_per_100,
                    ci_95=result.bb_per_100_ci_95,
                    beaten=beaten,
                    detail={
                        "hands_played": result.hands_played,
                        "sample_size_note": (
                            f"{self.cfg.num_duplicate_sets} duplicate sets x "
                            f"{self.cfg.hands_per_match} hands x 2 seats; live sample"
                        ),
                    },
                )
            )
            per_benchmark[rung_id] = {
                "bb_per_100": result.bb_per_100,
                "bb_ci_95": result.bb_per_100_ci_95,
                "hands_played": result.hands_played,
                "significant": result.is_statistically_significant,
                "beaten": beaten,
            }

        summary = SkillLadderSummary(
            domain="poker",
            benchmark_id="poker/ladder_live",
            metric_name="bb_per_100",
            skill_index=ladder_position_index(tuple(rung_results)),
            rungs=tuple(rung_results),
            notes=(
                "Live per-fish evaluation against frozen random, loose_passive, "
                "tight_aggressive, and gto_expert rungs. Beaten requires a "
                f"positive CI-backed bb/100 result; live samples use "
                f"{self.cfg.num_duplicate_sets} duplicate sets x "
                f"{self.cfg.hands_per_match} hands x 2 seats and are noisier "
                "than ladder_20k."
            ),
        )
        total_hands = sum(result.hands_played for result in self._current_results.values())
        bb_values = [result.bb_per_100 for result in self._current_results.values()]
        strategy = self._fish_strategy(fish)
        previous = next(
            (
                snapshot
                for snapshot in reversed(self.store.get_snapshots(domain="poker"))
                if snapshot.subject_fish_ids == [fish_id]
            ),
            None,
        )
        previous_score = previous.summary.skill_index if previous is not None else None
        personal_best = self.store.get_personal_best([fish_id], domain="poker")
        personal_best = max(personal_best, summary.skill_index)
        tank_best = max(self.store.get_tank_best("poker"), summary.skill_index)

        self.history.append(
            {
                "frame": self._current_frame,
                "fish_id": fish_id,
                "algorithm_id": strategy.strategy_id if strategy is not None else "unknown",
                "weighted_bb_per_100": sum(bb_values) / max(len(bb_values), 1),
                "weighted_bb_ci_95": (
                    min(result.bb_per_100_ci_95[0] for result in self._current_results.values()),
                    max(result.bb_per_100_ci_95[1] for result in self._current_results.values()),
                ),
                "total_hands": total_hands,
                "per_benchmark": per_benchmark,
                "summary": summary.to_dict(),
            }
        )
        if len(self.history) > self.history_max:
            self.history = self.history[-self.history_max :]

        self.store.add_snapshot(
            SkillSnapshot(
                domain="poker",
                generation=int(fish.generation),
                frame=self._current_frame,
                subject_fish_ids=[fish_id],
                subject_lineage_ids=[lineage_id],
                summary=summary,
                previous_score=previous_score,
                personal_best=personal_best,
                tank_best=tank_best,
                sample_size=total_hands,
            )
        )

    def get_history(self) -> list[dict[str, Any]]:
        """Return bounded evaluation history."""
        return list(self.history)

    def get_latest_results(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the most recent bounded evaluation records."""
        return self.history[-n:] if n > 0 else []
