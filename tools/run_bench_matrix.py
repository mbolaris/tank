#!/usr/bin/env python3
"""Run a benchmark across a seed list and output matrix results JSON.

Usage:
    python tools/run_bench_matrix.py path/to/benchmark.py --seeds 42,7,123 --out result.json
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

# Add repo root to sys.path so we can import tools and core
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_bench import load_benchmark_module, run_benchmark, expected_runtime_seconds
from tools.validate_improvement import get_champion_record, check_config_compatibility
from core.solutions.config_hash import compute_config_hash
from core.research.attempt_ledger import log_attempt


def main():
    parser = argparse.ArgumentParser(description="Run a benchmark matrix")
    parser.add_argument("benchmark_path", help="Path to benchmark python file")
    parser.add_argument(
        "--seeds",
        default="42,7,123",
        help="Comma-separated list of random seeds (default: 42,7,123)",
    )
    parser.add_argument("--out", help="Output JSON path")
    parser.add_argument(
        "--champion",
        help="Path to champion JSON to compare against and decide exit status",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-9,
        help="Floating point tolerance for score comparison",
    )

    args = parser.parse_args()

    try:
        seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    except ValueError:
        print("Error: --seeds must be a comma-separated list of integers.")
        sys.exit(1)

    if not seeds:
        print("Error: No seeds specified.")
        sys.exit(1)

    try:
        bench_module = load_benchmark_module(args.benchmark_path)
    except Exception as e:
        print(f"Error loading benchmark: {e}")
        sys.exit(1)

    if not hasattr(bench_module, "run") or not hasattr(bench_module, "BENCHMARK_ID"):
        print(
            f"Error: {args.benchmark_path} does not match benchmark contract (needs run() and BENCHMARK_ID)"
        )
        sys.exit(1)

    benchmark_id = bench_module.BENCHMARK_ID
    print(f"Running benchmark matrix: {benchmark_id}")
    print(f"Seeds to evaluate: {seeds}")

    per_seed = {}
    scores = []
    runtimes = []
    start_total = time.time()

    for idx, seed in enumerate(seeds):
        print(f"[{idx+1}/{len(seeds)}] Running seed {seed}...")
        start_run = time.time()
        try:
            res = run_benchmark(bench_module, seed)
            run_elapsed = time.time() - start_run
            if "runtime_seconds" not in res:
                res["runtime_seconds"] = run_elapsed
            scores.append(res["score"])
            runtimes.append(res["runtime_seconds"])
            per_seed[str(seed)] = res
        except Exception as e:
            print(f"Seed {seed} failed: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    total_elapsed = time.time() - start_total
    n = len(seeds)
    mean_score = sum(scores) / n
    min_score = min(scores)
    max_score = max(scores)
    stdev_score = statistics.stdev(scores) if n >= 2 else 0.0

    print("\nMatrix Results Summary:")
    print(f"  Seeds: {seeds}")
    print(f"  Scores: {[round(s, 6) for s in scores]}")
    print(f"  Mean:   {mean_score:.6f}")
    print(f"  Min:    {min_score:.6f}")
    print(f"  Max:    {max_score:.6f}")
    print(f"  Stdev:  {stdev_score:.6f}")
    print(f"  Total Runtime: {total_elapsed:.1f}s")

    primary_seed = seeds[0]
    config_hash = compute_config_hash(
        benchmark_id, primary_seed, getattr(bench_module, "CONFIG", None)
    )

    # Construct the matrix result structure
    result = {
        "benchmark_id": benchmark_id,
        "score": mean_score,  # Standard key
        "seed": primary_seed,  # Standard key (integer)
        "seeds": seeds,
        "scores": scores,
        "mean": mean_score,
        "min": min_score,
        "max": max_score,
        "stdev": stdev_score,
        "n": n,
        "runtime_seconds": total_elapsed,
        "expected_runtime_seconds": expected_runtime_seconds(bench_module),
        "config_hash": config_hash,
        "per_seed": per_seed,
        "timestamp": time.time(),
    }

    if args.out:
        print(f"Writing matrix results to {args.out}...")
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Matrix results written to {args.out}")

    # If champion comparison is requested
    if args.champion:
        try:
            with open(args.champion, encoding="utf-8") as f:
                champion_data = json.load(f)
            champion_record = get_champion_record(champion_data)
        except FileNotFoundError:
            print(
                f"No existing champion found at {args.champion}. Treating candidate as new champion."
            )
            sys.exit(0)

        # Check configuration compatibility for the primary seed
        config_error = check_config_compatibility(result, champion_data)
        if config_error:
            print(config_error)
            # Log config error to ledger
            log_attempt(
                benchmark_id=benchmark_id,
                verdict="error",
                candidate_score=mean_score,
                champion_score=float(champion_record["score"]) if champion_record else None,
                seed=seeds,
                config_hash=config_hash,
                description=f"Matrix config error: {config_error.splitlines()[0]}",
            )
            sys.exit(1)

        # Compare scores
        # We need to decide if we beat the champion on a majority of seeds.
        # Let's see if the champion has multi-seed results recorded.
        champ_per_seed = champion_record.get("per_seed", {})

        wins = 0
        losses = 0
        ties = 0
        compared_seeds = []

        for seed in seeds:
            seed_str = str(seed)
            if seed_str in champ_per_seed:
                cand_s = per_seed[seed_str]["score"]
                champ_s = champ_per_seed[seed_str]["score"]
                compared_seeds.append(seed)
                diff = cand_s - champ_s
                if diff > args.tolerance:
                    wins += 1
                elif diff < -args.tolerance:
                    losses += 1
                else:
                    ties += 1

        if compared_seeds:
            print(f"\nSeed-by-seed comparison (n={len(compared_seeds)} overlapping seeds):")
            for seed in compared_seeds:
                seed_str = str(seed)
                cand_s = per_seed[seed_str]["score"]
                champ_s = champ_per_seed[seed_str]["score"]
                print(
                    f"  Seed {seed}: Candidate={cand_s:.6f} vs Champion={champ_s:.6f} (diff={cand_s-champ_s:+.6f})"
                )

            n_compared = len(compared_seeds)
            print(f"Comparison summary: {wins} wins, {losses} losses, {ties} ties")

            # Majority win is defined as wins > n_compared / 2
            is_better = wins > (n_compared / 2)
            verdict = "accepted" if is_better else "rejected"
            desc = f"Matrix: {wins}/{n_compared} wins, {losses} losses, {ties} ties"
        else:
            # Fallback if no overlapping seeds:
            # Check if champion is single-seed on primary seed or seed 42
            champ_seed = champion_record.get("seed")
            if champ_seed is not None and str(champ_seed) in per_seed:
                cand_s = per_seed[str(champ_seed)]["score"]
                champ_s = float(champion_record["score"])
                diff = cand_s - champ_s
                is_better = diff > args.tolerance
                verdict = "accepted" if is_better else "rejected"
                desc = f"Matrix fallback (seed {champ_seed}): Candidate={cand_s:.6f} vs Champion={champ_s:.6f} (diff={diff:+.6f})"
                print(f"\nComparing on matching seed {champ_seed}:")
                print(f"  {desc}")
            else:
                # Compare overall mean/score against champion score
                cand_s = mean_score
                champ_s = float(champion_record["score"])
                diff = cand_s - champ_s
                is_better = diff > args.tolerance
                verdict = "accepted" if is_better else "rejected"
                desc = f"Matrix fallback (mean): Candidate mean={cand_s:.6f} vs Champion score={champ_s:.6f} (diff={diff:+.6f})"
                print("\nComparing mean vs single champion score:")
                print(f"  {desc}")

        log_attempt(
            benchmark_id=benchmark_id,
            verdict=verdict,
            candidate_score=mean_score,
            champion_score=float(champion_record["score"]),
            seed=seeds,
            config_hash=config_hash,
            description=desc,
        )

        if not is_better:
            print("\nFAILURE: Candidate failed to improve on the champion.")
            sys.exit(1)
        else:
            print("\nSUCCESS: Candidate improved on the champion!")
            sys.exit(0)


if __name__ == "__main__":
    main()
