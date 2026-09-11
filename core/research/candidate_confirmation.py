"""Re-score an accepted control-arm candidate on seeds it was never selected on.

The campaign's acceptance rule looks at the seeds it searched. That is enough to
rank candidates and no more: a mutation can win the mean on three seeds and still
have a failure mode on a fourth. Candidate 27 of the first published campaign did
exactly that, which is why this module exists — it won the tuning benchmark by
17.2%, transferred to the held-out evaluator, improved `ecosystem_health_10k` on
every seed tried, and pushed `survival_5k` past its starvation validity gate on
an unsearched seed, scoring zero.

So "accepted" and "confirmed" are deliberately different words here. Confirmation
asks a stricter question than "is the mean higher": it asks whether the candidate
ever turns a run that was *valid* into one that is not. A benchmark that gates
itself invalid is reporting that the ecosystem broke, and a mean improvement does
not buy that back.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from tools.param_mutator import MutationPlan

# Seeds the first campaign searched. Confirmation must not reuse them.
CAMPAIGN_SEEDS = (42, 7, 123)
DEFAULT_CONFIRMATION_SEEDS = (1, 2, 999)


def _as_float(value: object) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"expected a number, got {type(value).__name__}")


def run_validity(result: object) -> bool:
    """Whether a benchmark result reports itself valid.

    Benchmarks that carry a validity gate say so in metadata (``survival_5k``
    zeroes its score when starvation exceeds a maximum rate). Those that do not
    are treated as always valid rather than guessed at.
    """
    if not isinstance(result, dict):
        return True
    metadata = result.get("metadata")
    if isinstance(metadata, dict) and "score_valid" in metadata:
        return bool(metadata["score_valid"])
    return True


def invalid_reason(result: object) -> str | None:
    """The benchmark's own explanation for gating itself invalid, if any."""
    if not isinstance(result, dict):
        return None
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        reason = metadata.get("score_invalid_reason")
        if isinstance(reason, str) and reason:
            return reason
    return None


@dataclass(frozen=True)
class SeedOutcome:
    """One unseen seed, scored with and without the candidate."""

    seed: int
    baseline_score: float
    candidate_score: float
    baseline_valid: bool
    candidate_valid: bool
    candidate_invalid_reason: str | None = None

    @property
    def delta(self) -> float:
        return self.candidate_score - self.baseline_score

    @property
    def invalidated(self) -> bool:
        """The candidate broke a run that the baseline kept valid."""
        return self.baseline_valid and not self.candidate_valid

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "baseline_score": self.baseline_score,
            "candidate_score": self.candidate_score,
            "delta": self.delta,
            "baseline_valid": self.baseline_valid,
            "candidate_valid": self.candidate_valid,
            "invalidated": self.invalidated,
            "candidate_invalid_reason": self.candidate_invalid_reason,
        }


@dataclass(frozen=True)
class ConfirmationReport:
    """Whether an accepted candidate survives seeds it was not selected on."""

    benchmark_id: str
    outcomes: tuple[SeedOutcome, ...]

    @property
    def invalidated(self) -> tuple[SeedOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.invalidated)

    @property
    def regressions(self) -> tuple[SeedOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.delta < 0)

    @property
    def mean_delta(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(outcome.delta for outcome in self.outcomes) / len(self.outcomes)

    @property
    def confirmed(self) -> bool:
        """Confirmed only when nothing broke and the mean did not fall.

        Invalidating any previously-valid run is disqualifying on its own: that
        is the benchmark saying the ecosystem stopped working, which no average
        is allowed to outvote.
        """
        return not self.invalidated and self.mean_delta >= 0 and bool(self.outcomes)

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "seeds": [outcome.seed for outcome in self.outcomes],
            "mean_delta": self.mean_delta,
            "invalidated_seeds": [outcome.seed for outcome in self.invalidated],
            "regressed_seeds": [outcome.seed for outcome in self.regressions],
            "confirmed": self.confirmed,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


def confirm_candidate(
    benchmark: ModuleType,
    plan: MutationPlan,
    seeds: tuple[int, ...] = DEFAULT_CONFIRMATION_SEEDS,
) -> ConfirmationReport:
    """Score ``plan`` against the unmutated baseline on each of ``seeds``."""
    from tools.non_ai_baseline import evaluate_plan

    overlap = set(seeds) & set(CAMPAIGN_SEEDS)
    if overlap:
        raise ValueError(
            f"confirmation seeds must be disjoint from the searched seeds; {sorted(overlap)} overlap"
        )

    outcomes: list[SeedOutcome] = []
    for seed in seeds:
        baseline = evaluate_plan(benchmark, (seed,), None)
        candidate = evaluate_plan(benchmark, (seed,), plan)
        baseline_run = baseline["per_seed"][str(seed)]
        candidate_run = candidate["per_seed"][str(seed)]
        outcomes.append(
            SeedOutcome(
                seed=seed,
                baseline_score=_as_float(baseline["score"]),
                candidate_score=_as_float(candidate["score"]),
                baseline_valid=run_validity(baseline_run),
                candidate_valid=run_validity(candidate_run),
                candidate_invalid_reason=invalid_reason(candidate_run),
            )
        )
    return ConfirmationReport(benchmark_id=str(benchmark.BENCHMARK_ID), outcomes=tuple(outcomes))
