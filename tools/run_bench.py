"""Run a benchmark and output results JSON.

Usage:
    python tools/run_bench.py path/to/benchmark.py --seed 123 --out result.json
"""

import argparse
import sys
import json
import importlib.util
import os
from typing import Dict, Any


def load_benchmark_module(path: str):
    """Load benchmark module from file path."""
    module_name = os.path.basename(path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load benchmark from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Run a benchmark")
    parser.add_argument("benchmark_path", help="Path to benchmark python file")
    parser.add_argument("--seed", type=int, required=True, help="Random seed")
    parser.add_argument("--out", help="Output JSON path")
    parser.add_argument(
        "--verify-determinism", action="store_true", help="Run twice and assert identical output"
    )

    args = parser.parse_args()

    try:
        bench_module = load_benchmark_module(args.benchmark_path)

        if not hasattr(bench_module, "run") or not hasattr(bench_module, "BENCHMARK_ID"):
            print(
                f"Error: {args.benchmark_path} does not match benchmark contract (needs run() and BENCHMARK_ID)"
            )
            sys.exit(1)

        print(f"Running benchmark: {bench_module.BENCHMARK_ID} (Seed: {args.seed})...")

        # Run 1
        result1 = bench_module.run(args.seed)

        if args.verify_determinism:
            print("Verifying determinism (Run 2)...")
            result2 = bench_module.run(args.seed)

            # Compare critical fields
            score_diff = abs(result1["score"] - result2["score"])
            if score_diff > 1e-9:
                print(
                    f"FATAL: Non-deterministic result! Score {result1['score']} != {result2['score']}"
                )
                sys.exit(1)

            # Compare metadata recursively if needed, but score is the main gate
            print("Determinism check PASSED.")

        # Add environment info
        result1["timestamp"] = __import__("time").time()

        # Output
        if args.out:
            with open(args.out, "w") as f:
                json.dump(result1, f, indent=2)
            print(f"Result written to {args.out}")
        else:
            print(json.dumps(result1, indent=2))

    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
