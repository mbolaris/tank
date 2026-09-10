"""Run the Theme 10.6 control-arm campaign and publish its evidence.

Theme 10.5 built a non-AI parameter search (``tools/non_ai_baseline.py``) and
nobody ever ran it at a budget worth reporting.  This module runs it, re-scores
what it accepts on a held-out evaluator, and writes the whole trace — accepted,
rejected and errored alike — to a committed directory rather than the
gitignored default ledger.

Two design rules are enforced here rather than left to the operator:

* **An instrument must be shown to respond before it is trusted.**
  :func:`probe_operator_sensitivity` spends a handful of evaluations proving the
  mutation operator can move the benchmark at all.  A benchmark that cannot
  respond yields a 0% acceptance rate that looks like a finding about search and
  is really a fact about the instrument.
* **Evidence is written as it is produced.**  Every candidate is appended to the
  ledger the moment it is scored, so an interrupted campaign is still publishable
  at its true candidate count instead of being lost.

The preregistered criteria this module reports against live in
``docs/CONTROL_ARM_PREREGISTRATION.md``, committed before any result existed.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from core.research.attempt_ledger import log_attempt

CONTROL_ARM_AGENT_ID = "non-ai-random-search"
SENSITIVITY_TOLERANCE = 1e-9
# Matches tools/validate_reproduction.py: a champion must reproduce exactly.
REPRODUCTION_TOLERANCE = 1e-9
DEFAULT_PROBES = 5
DEFAULT_SEEDS = (42, 7, 123)


def _as_float(value: object) -> float:
    """Narrow a JSON-shaped value to a float instead of leaving it untyped."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"expected a number, got {type(value).__name__}")


def _as_int(value: object) -> int:
    """Narrow a JSON-shaped value to an int."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise TypeError(f"expected an integer, got {type(value).__name__}")


@dataclass(frozen=True)
class SensitivityReport:
    """Whether the mutation operator can move a benchmark's score at all."""

    benchmark_id: str
    seed: int
    baseline_score: float
    probe_scores: tuple[float, ...]
    mutation_counts: tuple[int, ...]

    @property
    def deltas(self) -> tuple[float, ...]:
        return tuple(score - self.baseline_score for score in self.probe_scores)

    @property
    def responsive(self) -> bool:
        """True when at least one probe moved the score beyond tolerance."""
        return any(abs(delta) > SENSITIVITY_TOLERANCE for delta in self.deltas)

    @property
    def mutations_applied(self) -> int:
        return sum(self.mutation_counts)

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "seed": self.seed,
            "baseline_score": self.baseline_score,
            "probe_scores": list(self.probe_scores),
            "mutation_counts": list(self.mutation_counts),
            "deltas": list(self.deltas),
            "mutations_applied": self.mutations_applied,
            "responsive": self.responsive,
        }


def champion_seed_scores(champion: dict[str, object]) -> dict[str, float]:
    """Return the champion's recorded score for each seed it actually covers.

    Matrix-format champions (``tank/survival_5k`` among them) store the *mean*
    across several seeds as the top-level ``score`` while ``seed`` names only the
    primary one.  Comparing that mean against a single-seed run is the trap
    ``tools/validate_reproduction.py`` documents, and it manufactures a
    reproduction failure out of a champion that reproduces exactly.
    """
    per_seed = champion.get("per_seed")
    if isinstance(per_seed, dict) and per_seed:
        scores: dict[str, float] = {}
        for seed, payload in per_seed.items():
            if isinstance(payload, dict) and "score" in payload:
                scores[str(seed)] = _as_float(payload["score"])
        if scores:
            return scores
    return {str(_as_int(champion["seed"])): _as_float(champion["score"])}


@dataclass(frozen=True)
class ReferenceCheck:
    """Whether a committed champion record reproduces *on this machine*.

    Compares like with like: each seed the champion records against a local run
    of that same seed.  A champion that does not reproduce is not a usable
    acceptance reference, because the gap between machines would be scored as
    though the arm's mutations had caused it.
    """

    benchmark_id: str
    champion_scores: dict[str, float]
    local_scores: dict[str, float]
    tolerance: float

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(sorted(int(seed) for seed in self.champion_scores))

    @property
    def deltas(self) -> dict[str, float]:
        return {
            seed: self.local_scores[seed] - score
            for seed, score in self.champion_scores.items()
            if seed in self.local_scores
        }

    @property
    def max_abs_delta(self) -> float:
        deltas = self.deltas
        return max((abs(delta) for delta in deltas.values()), default=0.0)

    @property
    def reproduces(self) -> bool:
        """True when every recorded seed reproduces within tolerance."""
        if set(self.champion_scores) != set(self.local_scores):
            return False
        return self.max_abs_delta <= self.tolerance

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "seeds": list(self.seeds),
            "champion_scores": self.champion_scores,
            "local_scores": self.local_scores,
            "tolerance": self.tolerance,
            "deltas": self.deltas,
            "max_abs_delta": self.max_abs_delta,
            "reproduces": self.reproduces,
        }


def check_reference_validity(
    benchmark: ModuleType,
    champion: dict[str, object],
    *,
    tolerance: float = REPRODUCTION_TOLERANCE,
) -> ReferenceCheck:
    """Re-run every seed the champion records and report whether each reproduces."""
    from tools.non_ai_baseline import evaluate_plan

    champion_scores = champion_seed_scores(champion)
    local_scores: dict[str, float] = {}
    for seed in sorted(int(seed) for seed in champion_scores):
        result = evaluate_plan(benchmark, (seed,), None)
        local_scores[str(seed)] = _as_float(result["score"])
    return ReferenceCheck(
        benchmark_id=str(benchmark.BENCHMARK_ID),
        champion_scores=champion_scores,
        local_scores=local_scores,
        tolerance=tolerance,
    )


@dataclass(frozen=True)
class CandidateOutcome:
    """One control-arm candidate: its tuning score and any held-out re-score."""

    index: int
    accepted: bool
    score: float
    per_seed: dict[str, float]
    mutation_digest: str | None
    runtime_seconds: float
    heldout_score: float | None = None
    heldout_per_seed: dict[str, float] = field(default_factory=dict)
    heldout_transferred: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate": self.index,
            "accepted": self.accepted,
            "score": self.score,
            "per_seed": self.per_seed,
            "mutation_digest": self.mutation_digest,
            "runtime_seconds": self.runtime_seconds,
            "heldout_score": self.heldout_score,
            "heldout_per_seed": self.heldout_per_seed,
            "heldout_transferred": self.heldout_transferred,
        }


def binomial_interval(successes: int, trials: int) -> tuple[float, float]:
    """Return a Wilson score 95% interval for ``successes``/``trials``.

    Wilson rather than the normal approximation because this campaign expects a
    small numerator: the normal interval famously returns ``(0.0, 0.0)`` at zero
    successes, which would report certainty the arm can never succeed.
    """
    if trials <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (proportion + z * z / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / trials + z * z / (4 * trials * trials))
        / denominator
    )
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def _seed_scores(result: dict[str, object]) -> dict[str, float]:
    """Pull the per-seed score map out of an ``evaluate_plan`` result."""
    per_seed = result.get("per_seed")
    if not isinstance(per_seed, dict):
        return {}
    scores: dict[str, float] = {}
    for seed, payload in per_seed.items():
        if isinstance(payload, dict) and "score" in payload:
            scores[str(seed)] = float(payload["score"])
    return scores


def probe_operator_sensitivity(
    benchmark: ModuleType,
    *,
    seed: int = DEFAULT_SEEDS[0],
    probes: int = DEFAULT_PROBES,
    target: str = "composable",
    mutation_rate: float = 0.3,
    mutation_strength: float = 0.15,
    mutation_seed: int = 9000,
) -> SensitivityReport:
    """Check the operator can move this benchmark before spending budget on it.

    Runs ``probes`` mutation plans on a single seed.  Cheap relative to a full
    campaign and decisive: ``tank/foraging_gym`` fails this check with fifty-two
    parameter mutations applied and no score movement whatsoever.
    """
    from tools.non_ai_baseline import _plan_for, evaluate_plan

    baseline = evaluate_plan(benchmark, (seed,), None)
    scores: list[float] = []
    counts: list[int] = []
    for index in range(1, probes + 1):
        plan = _plan_for(
            target=target,
            seed=mutation_seed + index,
            generation=index,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )
        result = evaluate_plan(benchmark, (seed,), plan)
        scores.append(_as_float(result["score"]))
        counts.append(len(plan.to_dict().get("mutations", [])))
    return SensitivityReport(
        benchmark_id=str(benchmark.BENCHMARK_ID),
        seed=seed,
        baseline_score=_as_float(baseline["score"]),
        probe_scores=tuple(scores),
        mutation_counts=tuple(counts),
    )


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    """Append one record, flushing immediately so interruption keeps the trace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()


def run_campaign(
    benchmark: ModuleType,
    *,
    candidates: int,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    heldout: ModuleType | None = None,
    reference: dict[str, object] | None = None,
    target: str = "composable",
    mutation_rate: float = 0.3,
    mutation_strength: float = 0.15,
    mutation_seed: int = 9001,
    results_dir: Path | None = None,
    ledger_path: str | Path | None = None,
    reference_check: ReferenceCheck | None = None,
) -> dict[str, object]:
    """Run the control arm, re-score acceptances held-out, and publish the trace.

    ``reference`` is the champion record the acceptance rule compares against.
    When it is ``None`` the unmutated baseline measured here, on these seeds,
    becomes the reference — a paired comparison against the same code on the same
    machine, which is the only valid choice when a champion recorded elsewhere
    does not reproduce locally (see :func:`check_reference_validity`).
    """
    from tools.non_ai_baseline import _plan_for, evaluate_plan, majority_improvement

    results_dir = Path(results_dir) if results_dir else Path("research/control_arm")
    slug = str(benchmark.BENCHMARK_ID).replace("/", "_")
    trace_path = results_dir / f"{slug}_candidates.jsonl"

    started = time.perf_counter()
    benchmark_runs = 0

    baseline = evaluate_plan(benchmark, seeds, None)
    benchmark_runs += len(seeds)
    comparison = reference if reference is not None else baseline
    outcomes: list[CandidateOutcome] = []
    # The held-out baseline is the same unmutated code on the same seeds every
    # time, so it is measured once on first use rather than per acceptance.
    heldout_baseline: dict[str, object] | None = None

    for index in range(1, candidates + 1):
        plan = _plan_for(
            target=target,
            seed=mutation_seed + index,
            generation=index,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )
        candidate_started = time.perf_counter()
        result = evaluate_plan(benchmark, seeds, plan)
        benchmark_runs += len(seeds)
        accepted = majority_improvement(result, comparison)

        heldout_score: float | None = None
        heldout_seeds: dict[str, float] = {}
        transferred: bool | None = None
        if accepted and heldout is not None:
            if heldout_baseline is None:
                heldout_baseline = evaluate_plan(heldout, seeds, None)
                benchmark_runs += len(seeds)
            heldout_result = evaluate_plan(heldout, seeds, plan)
            benchmark_runs += len(seeds)
            heldout_score = _as_float(heldout_result["score"])
            heldout_seeds = _seed_scores(heldout_result)
            transferred = majority_improvement(heldout_result, heldout_baseline)

        outcome = CandidateOutcome(
            index=index,
            accepted=accepted,
            score=_as_float(result["score"]),
            per_seed=_seed_scores(result),
            mutation_digest=result.get("mutation_digest"),
            runtime_seconds=time.perf_counter() - candidate_started,
            heldout_score=heldout_score,
            heldout_per_seed=heldout_seeds,
            heldout_transferred=transferred,
        )
        outcomes.append(outcome)

        record = outcome.to_dict()
        record["mutation_plan"] = plan.to_dict()
        _append_jsonl(trace_path, record)
        log_attempt(
            benchmark_id=str(benchmark.BENCHMARK_ID),
            verdict="accepted" if accepted else "rejected",
            candidate_score=outcome.score,
            champion_score=_as_float(comparison["score"]),
            seed=list(seeds),
            config_hash=result.get("config_hash"),
            agent_id=CONTROL_ARM_AGENT_ID,
            description=f"Control-arm candidate {index}/{candidates}",
            ledger_path=ledger_path,
            patch_type="parameter-tuning",
            duration=outcome.runtime_seconds,
            accepted_by_gate=accepted,
            champion_updated=False,
        )

    return summarize_campaign(
        benchmark_id=str(benchmark.BENCHMARK_ID),
        heldout_id=str(heldout.BENCHMARK_ID) if heldout is not None else None,
        seeds=seeds,
        baseline=baseline,
        comparison=comparison,
        reference_kind="champion" if reference is not None else "local-paired-baseline",
        reference_check=reference_check,
        outcomes=outcomes,
        wall_clock_seconds=time.perf_counter() - started,
        benchmark_runs=benchmark_runs,
        trace_path=trace_path,
    )


def summarize_campaign(
    *,
    benchmark_id: str,
    heldout_id: str | None,
    seeds: tuple[int, ...],
    baseline: dict[str, object],
    comparison: dict[str, object],
    reference_kind: str,
    outcomes: list[CandidateOutcome],
    reference_check: ReferenceCheck | None = None,
    wall_clock_seconds: float,
    benchmark_runs: int,
    trace_path: Path,
) -> dict[str, object]:
    """Report the campaign against its four preregistered criteria."""
    accepted = [outcome for outcome in outcomes if outcome.accepted]
    transferred = [outcome for outcome in accepted if outcome.heldout_transferred]
    scores = [outcome.score for outcome in outcomes]
    low, high = binomial_interval(len(accepted), len(outcomes))
    best = max(outcomes, key=lambda outcome: outcome.score, default=None)

    return {
        "arm": CONTROL_ARM_AGENT_ID,
        "benchmark_id": benchmark_id,
        "heldout_id": heldout_id,
        "seeds": list(seeds),
        "candidates": len(outcomes),
        "reference_kind": reference_kind,
        "reference_score": _as_float(comparison["score"]),
        "baseline_score": _as_float(baseline["score"]),
        "acceptance": {
            "accepted": len(accepted),
            "rate": len(accepted) / len(outcomes) if outcomes else 0.0,
            "wilson_95": [low, high],
        },
        "transfer": {
            "evaluated": len(accepted),
            "transferred": len(transferred),
            "rate": len(transferred) / len(accepted) if accepted else None,
        },
        "best_achieved": {
            "score": best.score if best else None,
            "candidate": best.index if best else None,
            "delta_vs_reference": (best.score - _as_float(comparison["score"]) if best else None),
        },
        "score_distribution": {
            "mean": statistics.fmean(scores) if scores else None,
            "stdev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        },
        "compute": {
            "wall_clock_seconds": wall_clock_seconds,
            "benchmark_runs": benchmark_runs,
        },
        "reference_check": reference_check.to_dict() if reference_check else None,
        "trace_path": str(trace_path),
        "candidate_outcomes": [outcome.to_dict() for outcome in outcomes],
    }
