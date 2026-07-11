#!/usr/bin/env python3
"""Run a deterministic non-AI parameter-search control arm.

This tool uses the same benchmark ``run(seed)`` contract and seed-matrix shape
as the agent validation tooling. It deliberately makes no source edits: each
candidate is applied in memory, scored, restored, and written to the attempt
ledger as ``agent_id=non-ai-random-search``. That makes it suitable as a fair
control arm for research claims about AI-generated mutations.

Example:
    py -3 tools/non_ai_baseline.py benchmarks/tank/foraging_gym.py \
        --candidates 5 --seeds 42,7,123 --ledger control.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.attempt_ledger import log_attempt
from core.solutions.config_hash import compute_config_hash
from tools.evolve import _apply_param_patch, _restore_params
from tools.param_mutator import (
    MutationPlan,
    mutate_algorithm_params,
    mutate_all_algorithms,
    mutate_composable_params,
)
from tools.run_bench import load_benchmark_module, run_benchmark
from tools.validate_improvement import get_champion_record


def parse_seeds(raw: str) -> tuple[int, ...]:
    """Parse and validate a comma-separated seed matrix."""
    try:
        seeds = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("--seeds must be a comma-separated list of integers") from exc
    if not seeds:
        raise ValueError("--seeds must contain at least one integer")
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must not contain duplicates")
    return seeds


def _mutation_digest(plan: MutationPlan | None) -> str | None:
    """Return a stable digest for the exact mutation proposal."""
    if plan is None:
        return None
    payload = json.dumps(plan.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _plan_for(
    *, target: str, seed: int, generation: int, mutation_rate: float, mutation_strength: float
) -> MutationPlan:
    """Generate one deterministic non-AI mutation proposal."""
    if target == "composable":
        return mutate_composable_params(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            seed=seed,
            generation=generation,
        )
    if target == "all":
        return mutate_all_algorithms(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            seed=seed,
            generation=generation,
        )
    return mutate_algorithm_params(
        target,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        seed=seed,
        generation=generation,
    )


def evaluate_plan(
    benchmark: ModuleType,
    seeds: tuple[int, ...],
    plan: MutationPlan | None,
) -> dict[str, Any]:
    """Evaluate one plan on every seed using the normal benchmark runner."""
    original_sub: dict[str, Any] | None = None
    original_algo: dict[str, Any] | None = None
    if plan is not None:
        from tools.param_mutator import (
            apply_mutations_to_algorithm_bounds,
            apply_mutations_to_definitions,
        )

        original_sub, original_algo = _apply_param_patch(
            apply_mutations_to_definitions(plan),
            apply_mutations_to_algorithm_bounds(plan),
        )

    started = time.perf_counter()
    try:
        per_seed: dict[str, dict[str, Any]] = {}
        for seed in seeds:
            result = dict(run_benchmark(benchmark, seed))
            per_seed[str(seed)] = result
    finally:
        if original_sub is not None and original_algo is not None:
            _restore_params(original_sub, original_algo)

    scores = [float(per_seed[str(seed)]["score"]) for seed in seeds]
    primary_seed = seeds[0]
    return {
        "benchmark_id": benchmark.BENCHMARK_ID,
        "seed": primary_seed,
        "seeds": list(seeds),
        "scores": scores,
        "score": statistics.fmean(scores),
        "mean": statistics.fmean(scores),
        "stdev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "runtime_seconds": time.perf_counter() - started,
        "config_hash": compute_config_hash(
            benchmark.BENCHMARK_ID, primary_seed, getattr(benchmark, "CONFIG", None)
        ),
        "mutation_digest": _mutation_digest(plan),
        "per_seed": per_seed,
    }


def _reference_scores(reference: dict[str, Any], seeds: tuple[int, ...]) -> dict[str, float]:
    """Extract comparable per-seed scores from a matrix or single result."""
    per_seed = reference.get("per_seed")
    if isinstance(per_seed, dict):
        return {
            str(seed): float(per_seed[str(seed)]["score"])
            for seed in seeds
            if str(seed) in per_seed
        }
    primary_seed = reference.get("seed")
    if primary_seed in seeds or str(primary_seed) in {str(seed) for seed in seeds}:
        return {str(primary_seed): float(reference["score"])}
    return {}


def majority_improvement(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    *,
    tolerance: float = 1e-9,
    max_regression_pct: float = 0.10,
) -> bool:
    """Apply the control arm's pre-registered mean/majority comparison rule."""
    candidate_scores = _reference_scores(candidate, tuple(candidate["seeds"]))
    reference_scores = _reference_scores(reference, tuple(candidate["seeds"]))
    overlapping = sorted(set(candidate_scores) & set(reference_scores))
    if not overlapping:
        return float(candidate["score"]) - float(reference["score"]) > tolerance

    candidate_mean = statistics.fmean(candidate_scores[seed] for seed in overlapping)
    reference_mean = statistics.fmean(reference_scores[seed] for seed in overlapping)
    if candidate_mean - reference_mean <= tolerance:
        return False

    wins = 0
    for seed in overlapping:
        candidate_score = candidate_scores[seed]
        reference_score = reference_scores[seed]
        if (
            reference_score > 0
            and (reference_score - candidate_score) / reference_score > max_regression_pct
        ):
            return False
        if candidate_score - reference_score > tolerance:
            wins += 1
    return wins > len(overlapping) / 2


def run_search(
    benchmark: ModuleType,
    *,
    seeds: tuple[int, ...],
    candidates: int,
    target: str,
    mutation_rate: float,
    mutation_strength: float,
    seed: int,
    champion: dict[str, Any] | None = None,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run baseline plus candidates and return a reproducible search report."""
    command = " ".join(sys.argv)
    baseline = evaluate_plan(benchmark, seeds, None)
    log_attempt(
        benchmark_id=benchmark.BENCHMARK_ID,
        verdict="baseline",
        candidate_score=baseline["score"],
        champion_score=(float(get_champion_record(champion)["score"]) if champion else None),
        seed=list(seeds),
        config_hash=baseline["config_hash"],
        agent_id="non-ai-random-search",
        description="Non-AI control-arm baseline with no parameter mutation",
        ledger_path=ledger_path,
        patch_type="parameter-tuning",
        benchmark_command=command,
        duration=baseline["runtime_seconds"],
        accepted_by_gate=True,
        champion_updated=False,
    )

    reference = get_champion_record(champion) if champion else baseline
    records: list[dict[str, Any]] = []
    best = baseline
    for index in range(1, candidates + 1):
        plan = _plan_for(
            target=target,
            seed=seed + index,
            generation=index,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )
        started = time.perf_counter()
        result = evaluate_plan(benchmark, seeds, plan)
        is_better = majority_improvement(result, reference)
        if is_better and not champion:
            reference = result
            best = result
        record = {
            "candidate": index,
            "accepted": is_better,
            "mutation_plan": plan.to_dict(),
            "result": result,
        }
        records.append(record)
        log_attempt(
            benchmark_id=benchmark.BENCHMARK_ID,
            verdict="accepted" if is_better else "rejected",
            candidate_score=result["score"],
            champion_score=(
                float(get_champion_record(champion)["score"])
                if champion
                else float(reference["score"])
            ),
            seed=list(seeds),
            config_hash=result["config_hash"],
            agent_id="non-ai-random-search",
            description=f"Non-AI candidate {index}/{candidates}; mutation={result['mutation_digest']}",
            ledger_path=ledger_path,
            patch_type="parameter-tuning",
            benchmark_command=command,
            duration=time.perf_counter() - started,
            accepted_by_gate=is_better,
            champion_updated=False,
        )

    return {
        "control_arm": "non-ai-random-search",
        "benchmark_id": benchmark.BENCHMARK_ID,
        "seeds": list(seeds),
        "target": target,
        "candidates": candidates,
        "baseline": baseline,
        "best": best,
        "accepted_candidates": sum(1 for record in records if record["accepted"]),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_path", help="Benchmark module path, as accepted by run_bench.py")
    parser.add_argument("--seeds", default="42,7,123", help="Comma-separated deterministic seeds")
    parser.add_argument("--candidates", type=int, default=3, help="Number of mutation candidates")
    parser.add_argument(
        "--target", default="composable", help="composable, all, or one algorithm ID"
    )
    parser.add_argument("--seed", type=int, default=9001, help="Mutation RNG base seed")
    parser.add_argument("--mutation-rate", type=float, default=0.3)
    parser.add_argument("--mutation-strength", type=float, default=0.15)
    parser.add_argument("--champion", help="Optional champion JSON for the comparison reference")
    parser.add_argument(
        "--ledger", help="Attempt ledger path (defaults to research/attempts.jsonl)"
    )
    parser.add_argument("--out", help="Write the search report to JSON")
    args = parser.parse_args()

    if args.candidates < 1:
        parser.error("--candidates must be >= 1")
    try:
        seeds = parse_seeds(args.seeds)
        benchmark = load_benchmark_module(args.benchmark_path)
        champion = None
        champion_path = (
            Path(args.champion)
            if args.champion
            else ROOT / "champions" / f"{benchmark.BENCHMARK_ID}.json"
        )
        if champion_path.exists():
            champion = json.loads(champion_path.read_text(encoding="utf-8"))
        report = run_search(
            benchmark,
            seeds=seeds,
            candidates=args.candidates,
            target=args.target,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
            seed=args.seed,
            champion=champion,
            ledger_path=args.ledger,
        )
    except (OSError, ValueError, ImportError, KeyError) as exc:
        parser.error(str(exc))

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
