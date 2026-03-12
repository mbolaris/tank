#!/usr/bin/env python3
"""Self-improvement orchestrator for Tank World.

Runs automated parameter evolution: mutate algorithm parameters, benchmark,
keep improvements, discard regressions. No external API needed.

Usage:
    # Run 5 generations of evolution
    python tools/evolve.py --generations 5 --seed 42

    # Target only composable params
    python tools/evolve.py --generations 10 --target composable

    # Target specific algorithm
    python tools/evolve.py --generations 10 --target greedy_food_seeker

    # Dry run (don't write changes to source)
    python tools/evolve.py --generations 3 --dry-run

    # Aggressive exploration
    python tools/evolve.py --generations 20 --mutation-rate 0.5 --mutation-strength 0.25
"""

import argparse
import copy
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run_benchmarks(seed: int, benchmark_ids: list[str] | None = None) -> dict[str, Any]:
    """Run benchmarks and return results. Imports lazily to allow patching first."""
    from tools.experiment import run_all_benchmarks

    return run_all_benchmarks(seed, benchmark_ids)


def _compute_fitness(results: dict[str, Any]) -> float:
    """Compute aggregate fitness score from benchmark results.

    Uses geometric mean of per-benchmark scores so that improvements must be
    broad (not just gaming one benchmark at the expense of another).
    """
    scores = []
    for bid, result in results.get("benchmarks", {}).items():
        if "error" in result:
            return 0.0  # Any benchmark failure is fatal
        scores.append(max(result["score"], 1e-6))  # Avoid log(0)

    if not scores:
        return 0.0

    # Geometric mean
    import math

    log_sum = sum(math.log(s) for s in scores)
    return math.exp(log_sum / len(scores))


def _apply_param_patch(
    composable_defaults: dict[str, float] | None = None,
    algo_bound_overrides: dict[str, dict[str, tuple[float, float]]] | None = None,
) -> tuple[dict, dict]:
    """Monkey-patch parameter dicts at runtime. Returns originals for restore."""
    from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
    from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS

    orig_sub = dict(SUB_BEHAVIOR_PARAMS)
    orig_algo = copy.deepcopy(ALGORITHM_PARAMETER_BOUNDS)

    if composable_defaults:
        # Shift bounds to center on new defaults while keeping same range
        for param, new_default in composable_defaults.items():
            if param in SUB_BEHAVIOR_PARAMS:
                old_lo, old_hi = SUB_BEHAVIOR_PARAMS[param]
                half_range = (old_hi - old_lo) / 2
                # Shift bounds, but clamp to original bounds
                new_lo = max(old_lo, new_default - half_range)
                new_hi = min(old_hi, new_default + half_range)
                SUB_BEHAVIOR_PARAMS[param] = (new_lo, new_hi)

    if algo_bound_overrides:
        for algo_id, params in algo_bound_overrides.items():
            if algo_id in ALGORITHM_PARAMETER_BOUNDS:
                for param, (new_lo, new_hi) in params.items():
                    if param in ALGORITHM_PARAMETER_BOUNDS[algo_id]:
                        ALGORITHM_PARAMETER_BOUNDS[algo_id][param] = (new_lo, new_hi)

    return orig_sub, orig_algo


def _restore_params(orig_sub: dict, orig_algo: dict) -> None:
    """Restore original parameter dicts after experiment."""
    from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
    from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS

    SUB_BEHAVIOR_PARAMS.clear()
    SUB_BEHAVIOR_PARAMS.update(orig_sub)

    ALGORITHM_PARAMETER_BOUNDS.clear()
    ALGORITHM_PARAMETER_BOUNDS.update(orig_algo)


def _write_composable_changes(new_params: dict[str, tuple[float, float]]) -> list[str]:
    """Write improved composable parameter bounds to definitions.py.

    Returns list of changes made.
    """
    from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS

    defs_path = ROOT / "core" / "algorithms" / "composable" / "definitions.py"
    content = defs_path.read_text()

    changes = []
    for param, (new_lo, new_hi) in new_params.items():
        if param not in SUB_BEHAVIOR_PARAMS:
            continue

        old_lo, old_hi = SUB_BEHAVIOR_PARAMS[param]
        if abs(new_lo - old_lo) < 1e-9 and abs(new_hi - old_hi) < 1e-9:
            continue

        # Find and replace the line in source
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if f'"{param}"' in line and ":" in line:
                # Extract any trailing comment
                comment = ""
                if "#" in line:
                    comment_idx = line.index("#")
                    comment = "  " + line[comment_idx:].strip()

                indent = line[: len(line) - len(line.lstrip())]
                lines[i] = f'{indent}"{param}": ({new_lo:.4f}, {new_hi:.4f}),{comment}'
                changes.append(
                    f"composable.{param}: ({old_lo:.4f}, {old_hi:.4f}) -> ({new_lo:.4f}, {new_hi:.4f})"
                )
                break

        content = "\n".join(lines)

    if changes:
        defs_path.write_text(content)

    return changes


def _write_algorithm_changes(new_bounds: dict[str, dict[str, tuple[float, float]]]) -> list[str]:
    """Write improved algorithm parameter bounds to base.py.

    Returns list of changes made.
    """
    from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS

    base_path = ROOT / "core" / "algorithms" / "base.py"
    content = base_path.read_text()

    changes = []
    for algo_id, params in new_bounds.items():
        if algo_id not in ALGORITHM_PARAMETER_BOUNDS:
            continue

        for param, (new_lo, new_hi) in params.items():
            if param not in ALGORITHM_PARAMETER_BOUNDS[algo_id]:
                continue

            old_lo, old_hi = ALGORITHM_PARAMETER_BOUNDS[algo_id][param]
            if abs(new_lo - old_lo) < 1e-9 and abs(new_hi - old_hi) < 1e-9:
                continue

            # Find and replace in source
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if f'"{param}"' in line and ":" in line:
                    # Check context: is this line under the right algorithm?
                    # Look backwards for the algorithm_id
                    for j in range(i - 1, max(i - 10, -1), -1):
                        if f'"{algo_id}"' in lines[j]:
                            indent = line[: len(line) - len(line.lstrip())]
                            comment = ""
                            if "#" in line:
                                comment_idx = line.index("#")
                                comment = "  " + line[comment_idx:].strip()
                            lines[i] = f'{indent}"{param}": ({new_lo:.4f}, {new_hi:.4f}),{comment}'
                            changes.append(
                                f"{algo_id}.{param}: ({old_lo:.4f}, {old_hi:.4f}) -> ({new_lo:.4f}, {new_hi:.4f})"
                            )
                            break
                    break

            content = "\n".join(lines)

    if changes:
        base_path.write_text(content)

    return changes


def evolve(
    generations: int = 5,
    seed: int = 42,
    target: str = "all",
    mutation_rate: float = 0.3,
    mutation_strength: float = 0.15,
    benchmark_ids: list[str] | None = None,
    dry_run: bool = False,
    log_dir: str | None = None,
) -> dict[str, Any]:
    """Run the evolution loop.

    Args:
        generations: Number of mutation-evaluate cycles
        seed: Base random seed
        target: "composable", "all", or a specific algorithm_id
        mutation_rate: Per-parameter mutation probability
        mutation_strength: Gaussian sigma as fraction of param range
        benchmark_ids: Which benchmarks to run (default: all tank)
        dry_run: If True, don't write changes to source files
        log_dir: Directory to write per-generation logs

    Returns:
        Summary dict with evolution history and final results
    """
    from tools.param_mutator import (
        MutationPlan,
        apply_mutations_to_algorithm_bounds,
        apply_mutations_to_definitions,
        mutate_algorithm_params,
        mutate_all_algorithms,
        mutate_composable_params,
    )

    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 70, file=sys.stderr)
    print("Tank World Parameter Evolution", file=sys.stderr)
    print(f"  Generations: {generations}", file=sys.stderr)
    print(f"  Target: {target}", file=sys.stderr)
    print(f"  Mutation rate: {mutation_rate}", file=sys.stderr)
    print(f"  Mutation strength: {mutation_strength}", file=sys.stderr)
    print(f"  Base seed: {seed}", file=sys.stderr)
    print(f"  Dry run: {dry_run}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)

    # Step 1: Establish baseline
    print("\n[Baseline] Running benchmarks...", file=sys.stderr)
    baseline_results = _run_benchmarks(seed, benchmark_ids)
    baseline_fitness = _compute_fitness(baseline_results)
    print(f"[Baseline] Fitness: {baseline_fitness:.6f}", file=sys.stderr)

    for bid, res in baseline_results.get("benchmarks", {}).items():
        if "error" not in res:
            print(f"  {bid}: {res['score']:.6f}", file=sys.stderr)

    # Evolution state
    best_fitness = baseline_fitness
    best_results = baseline_results
    best_plan: MutationPlan | None = None

    history: list[dict[str, Any]] = [
        {
            "generation": 0,
            "type": "baseline",
            "fitness": baseline_fitness,
            "scores": {
                bid: res.get("score", 0)
                for bid, res in baseline_results.get("benchmarks", {}).items()
            },
        }
    ]

    accepted = 0
    rejected = 0

    for gen in range(1, generations + 1):
        gen_seed = seed + gen * 1000  # Deterministic per-generation seed

        print(f"\n{'─'*70}", file=sys.stderr)
        print(
            f"[Gen {gen}/{generations}] Generating mutations (seed={gen_seed})...", file=sys.stderr
        )

        # Generate mutation plan
        if target == "composable":
            plan = mutate_composable_params(
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                seed=gen_seed,
                generation=gen,
            )
        elif target == "all":
            plan = mutate_all_algorithms(
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                seed=gen_seed,
                generation=gen,
            )
        else:
            plan = mutate_algorithm_params(
                target,
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                seed=gen_seed,
                generation=gen,
            )

        if not plan.mutations:
            print(f"[Gen {gen}] No mutations generated, skipping.", file=sys.stderr)
            history.append(
                {
                    "generation": gen,
                    "type": "skip",
                    "reason": "no mutations",
                    "fitness": best_fitness,
                }
            )
            continue

        print(f"[Gen {gen}] {len(plan.mutations)} mutations:", file=sys.stderr)
        print(textwrap.indent(plan.summary(), "  "), file=sys.stderr)

        # Apply mutations (monkey-patch)
        composable_defaults = apply_mutations_to_definitions(plan)
        algo_overrides = apply_mutations_to_algorithm_bounds(plan)

        orig_sub, orig_algo = _apply_param_patch(composable_defaults, algo_overrides)

        try:
            # Run benchmarks with mutated parameters
            print(f"[Gen {gen}] Running benchmarks...", file=sys.stderr)
            gen_results = _run_benchmarks(seed, benchmark_ids)
            gen_fitness = _compute_fitness(gen_results)

            diff = gen_fitness - best_fitness
            pct = (diff / max(abs(best_fitness), 1e-9)) * 100

            for bid, res in gen_results.get("benchmarks", {}).items():
                if "error" not in res:
                    old_score = best_results.get("benchmarks", {}).get(bid, {}).get("score", 0)
                    d = res["score"] - old_score
                    sign = "+" if d > 0 else ""
                    print(f"  {bid}: {res['score']:.6f} ({sign}{d:.6f})", file=sys.stderr)

            gen_record: dict[str, Any] = {
                "generation": gen,
                "fitness": gen_fitness,
                "diff": diff,
                "pct_change": round(pct, 4),
                "mutations": plan.to_dict()["mutations"],
                "scores": {
                    bid: res.get("score", 0)
                    for bid, res in gen_results.get("benchmarks", {}).items()
                },
            }

            if diff > 1e-9:
                # Improvement!
                print(
                    f"[Gen {gen}] IMPROVEMENT: {best_fitness:.6f} -> {gen_fitness:.6f} "
                    f"({pct:+.2f}%)",
                    file=sys.stderr,
                )
                best_fitness = gen_fitness
                best_results = gen_results
                best_plan = plan
                gen_record["type"] = "improvement"
                accepted += 1
            else:
                print(
                    f"[Gen {gen}] No improvement: {gen_fitness:.6f} vs best {best_fitness:.6f} "
                    f"({pct:+.2f}%)",
                    file=sys.stderr,
                )
                gen_record["type"] = "rejected"
                rejected += 1

            history.append(gen_record)

        finally:
            # Always restore original params
            _restore_params(orig_sub, orig_algo)

        # Log per-generation results
        if log_dir:
            gen_log_path = Path(log_dir) / f"gen_{gen:04d}.json"
            with open(gen_log_path, "w") as f:
                json.dump(history[-1], f, indent=2)

    # Step 3: Apply best mutations to source (if improvement found)
    source_changes: list[str] = []
    if not dry_run and best_plan is not None:
        print(f"\n{'='*70}", file=sys.stderr)
        print("Writing best mutations to source files...", file=sys.stderr)

        from tools.param_mutator import (
            apply_mutations_to_algorithm_bounds,
            apply_mutations_to_definitions,
        )

        composable_defaults = apply_mutations_to_definitions(best_plan)
        algo_overrides = apply_mutations_to_algorithm_bounds(best_plan)

        if composable_defaults:
            # Build new bounds from defaults
            from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS

            new_composable_bounds = {}
            for param, new_default in composable_defaults.items():
                if param in SUB_BEHAVIOR_PARAMS:
                    old_lo, old_hi = SUB_BEHAVIOR_PARAMS[param]
                    half_range = (old_hi - old_lo) / 2
                    new_lo = max(old_lo, new_default - half_range)
                    new_hi = min(old_hi, new_default + half_range)
                    new_composable_bounds[param] = (new_lo, new_hi)
            source_changes.extend(_write_composable_changes(new_composable_bounds))

        if algo_overrides:
            source_changes.extend(_write_algorithm_changes(algo_overrides))

        if source_changes:
            print(f"Applied {len(source_changes)} parameter changes:", file=sys.stderr)
            for c in source_changes:
                print(f"  {c}", file=sys.stderr)
        else:
            print("No source changes to write.", file=sys.stderr)
    elif dry_run and best_plan is not None:
        print(
            f"\n[DRY RUN] Would apply {len(best_plan.mutations)} mutations to source.",
            file=sys.stderr,
        )

    # Summary
    print(f"\n{'='*70}", file=sys.stderr)
    print("Evolution Complete", file=sys.stderr)
    print(f"  Generations: {generations}", file=sys.stderr)
    print(f"  Accepted: {accepted}", file=sys.stderr)
    print(f"  Rejected: {rejected}", file=sys.stderr)
    print(f"  Baseline fitness: {baseline_fitness:.6f}", file=sys.stderr)
    print(f"  Best fitness: {best_fitness:.6f}", file=sys.stderr)
    improvement = ((best_fitness - baseline_fitness) / max(abs(baseline_fitness), 1e-9)) * 100
    print(f"  Total improvement: {improvement:+.2f}%", file=sys.stderr)
    if source_changes:
        print(f"  Source changes: {len(source_changes)}", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)

    result = {
        "baseline_fitness": baseline_fitness,
        "best_fitness": best_fitness,
        "improvement_pct": round(improvement, 4),
        "accepted": accepted,
        "rejected": rejected,
        "generations": generations,
        "seed": seed,
        "target": target,
        "source_changes": source_changes,
        "history": history,
        "best_scores": {
            bid: res.get("score", 0) for bid, res in best_results.get("benchmarks", {}).items()
        },
    }

    if log_dir:
        summary_path = Path(log_dir) / "evolution_summary.json"
        with open(summary_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull log written to {log_dir}/", file=sys.stderr)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Tank World Parameter Evolution - Self-Improvement Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              # Quick 3-generation test
              python tools/evolve.py --generations 3 --seed 42

              # Focused evolution on composable behavior params
              python tools/evolve.py --generations 10 --target composable

              # Aggressive exploration with logging
              python tools/evolve.py --generations 20 --mutation-rate 0.5 --strength 0.25 --log-dir logs/evo_001

              # Dry run (no source changes)
              python tools/evolve.py --generations 5 --dry-run

              # Target a specific algorithm
              python tools/evolve.py --generations 10 --target greedy_food_seeker
        """
        ),
    )

    parser.add_argument(
        "--generations", type=int, default=5, help="Number of mutation-evaluate cycles (default: 5)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Base random seed (default: 42)")
    parser.add_argument(
        "--target",
        default="all",
        help="Mutation target: 'composable', 'all', or algorithm_id (default: all)",
    )
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=0.3,
        help="Per-parameter mutation probability (default: 0.3)",
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=0.15,
        help="Mutation strength as fraction of param range (default: 0.15)",
    )
    parser.add_argument(
        "--benchmarks", nargs="*", help="Specific benchmark IDs (default: all tank benchmarks)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't write changes to source files"
    )
    parser.add_argument("--log-dir", help="Directory for per-generation logs")
    parser.add_argument("--out", help="Output summary JSON path")

    args = parser.parse_args()

    result = evolve(
        generations=args.generations,
        seed=args.seed,
        target=args.target,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.strength,
        benchmark_ids=args.benchmarks,
        dry_run=args.dry_run,
        log_dir=args.log_dir,
    )

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSummary written to {args.out}", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
