"""Run all tank benchmarks and return structured results.

Usage:
    python tools/experiment.py --seed 42
    python tools/experiment.py --seed 42 --benchmarks tank/survival_5k tank/ecosystem_health_10k
    python tools/experiment.py --seed 42 --out results.json
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BENCHMARK_DIR = ROOT / "benchmarks"
CHAMPION_DIR = ROOT / "champions"

# All known benchmarks (benchmark_id -> file path)
KNOWN_BENCHMARKS: dict[str, Path] = {}


def _discover_benchmarks() -> dict[str, Path]:
    """Discover all benchmark files under benchmarks/."""
    benchmarks: dict[str, Path] = {}
    for py_file in BENCHMARK_DIR.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue
        # Try to load and check for BENCHMARK_ID
        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            bid = getattr(module, "BENCHMARK_ID", None)
            if bid and hasattr(module, "run"):
                benchmarks[bid] = py_file
        except Exception:
            continue
    return benchmarks


def _load_benchmark(path: Path):
    """Load a benchmark module from file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load benchmark from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_champion(benchmark_id: str) -> dict[str, Any] | None:
    """Load champion data for a benchmark."""
    # benchmark_id like "tank/survival_5k" -> champions/tank/survival_5k.json
    champion_path = CHAMPION_DIR / f"{benchmark_id}.json"
    if not champion_path.exists():
        return None
    with open(champion_path) as f:
        return json.load(f)


def run_benchmark(benchmark_id: str, seed: int) -> dict[str, Any]:
    """Run a single benchmark and return results with champion comparison.

    Args:
        benchmark_id: e.g. "tank/survival_5k"
        seed: Random seed for determinism

    Returns:
        Result dict with score, metadata, and champion comparison
    """
    global KNOWN_BENCHMARKS
    if not KNOWN_BENCHMARKS:
        KNOWN_BENCHMARKS = _discover_benchmarks()

    path = KNOWN_BENCHMARKS.get(benchmark_id)
    if path is None:
        raise ValueError(f"Unknown benchmark: {benchmark_id}. Known: {list(KNOWN_BENCHMARKS)}")

    module = _load_benchmark(path)
    result = module.run(seed)

    # Add champion comparison
    champion = load_champion(benchmark_id)
    if champion:
        champion_score = champion.get("score") if "champion" not in champion else None
        if champion_score is None and "champion" in champion:
            champion_score = champion["champion"].get("score")
        if champion_score is None:
            champion_score = champion.get("score")

        if champion_score is not None:
            diff = result["score"] - float(champion_score)
            pct = (diff / abs(float(champion_score))) * 100 if champion_score != 0 else 0
            result["champion_comparison"] = {
                "champion_score": float(champion_score),
                "diff": diff,
                "pct_change": round(pct, 4),
                "is_improvement": diff > 1e-9,
            }

    return result


def run_all_benchmarks(seed: int, benchmark_ids: list[str] | None = None) -> dict[str, Any]:
    """Run all (or specified) benchmarks and return structured results.

    Args:
        seed: Random seed
        benchmark_ids: Optional list of specific benchmarks to run

    Returns:
        Dict with overall summary and per-benchmark results
    """
    global KNOWN_BENCHMARKS
    if not KNOWN_BENCHMARKS:
        KNOWN_BENCHMARKS = _discover_benchmarks()

    if benchmark_ids is None:
        # Default: run all tank benchmarks
        benchmark_ids = [bid for bid in KNOWN_BENCHMARKS if bid.startswith("tank/")]

    results: dict[str, Any] = {}
    total_time = 0.0
    improvements = 0
    regressions = 0

    for bid in sorted(benchmark_ids):
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Running: {bid} (seed={seed})", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        start = time.time()
        try:
            result = run_benchmark(bid, seed)
            elapsed = time.time() - start
            total_time += elapsed
            results[bid] = result

            # Report
            score = result["score"]
            print(f"  Score: {score:.6f} ({elapsed:.1f}s)", file=sys.stderr)

            comp = result.get("champion_comparison")
            if comp:
                sign = "+" if comp["diff"] > 0 else ""
                print(
                    f"  vs Champion: {comp['champion_score']:.6f} "
                    f"({sign}{comp['diff']:.6f}, {sign}{comp['pct_change']:.2f}%)",
                    file=sys.stderr,
                )
                if comp["is_improvement"]:
                    improvements += 1
                elif comp["diff"] < -1e-9:
                    regressions += 1

        except Exception as e:
            elapsed = time.time() - start
            total_time += elapsed
            results[bid] = {"error": str(e), "benchmark_id": bid}
            print(f"  ERROR: {e}", file=sys.stderr)

    return {
        "seed": seed,
        "timestamp": time.time(),
        "total_runtime_seconds": round(total_time, 2),
        "summary": {
            "benchmarks_run": len(results),
            "improvements": improvements,
            "regressions": regressions,
        },
        "benchmarks": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run tank benchmarks")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--benchmarks", nargs="*", help="Specific benchmark IDs to run (default: all tank)"
    )
    parser.add_argument("--out", help="Output JSON path")

    args = parser.parse_args()

    results = run_all_benchmarks(args.seed, args.benchmarks)

    # Print summary
    s = results["summary"]
    print(f"\n{'='*60}", file=sys.stderr)
    print(
        f"Done: {s['benchmarks_run']} benchmarks, "
        f"{s['improvements']} improvements, {s['regressions']} regressions "
        f"({results['total_runtime_seconds']:.1f}s)",
        file=sys.stderr,
    )
    print(f"{'='*60}", file=sys.stderr)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {args.out}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
