"""Run a benchmark and output results JSON.

Usage:
    python tools/run_bench.py path/to/benchmark.py --seed 123 --out result.json
"""

import argparse
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path

# Add repo root to sys.path so benchmarks can import core regardless of cwd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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


def run_benchmark(bench_module, seed: int, fingerprint_recorder=None):
    """Run a benchmark, attaching fingerprint recording when supported."""
    parameters = inspect.signature(bench_module.run).parameters
    if fingerprint_recorder is not None and "fingerprint_callback" not in parameters:
        raise ValueError(
            f"{bench_module.BENCHMARK_ID} does not support fingerprint artifacts "
            "(run() needs fingerprint_callback)"
        )
    if fingerprint_recorder is None:
        return bench_module.run(seed)
    return bench_module.run(seed, fingerprint_callback=fingerprint_recorder.record)


def create_fingerprint_recorder(path: str, bench_module, seed: int, interval: int):
    from core.replay.fingerprint_stream import FingerprintStreamRecorder

    return FingerprintStreamRecorder(
        path,
        benchmark_id=bench_module.BENCHMARK_ID,
        seed=seed,
        interval=interval,
    )


def second_fingerprint_path(path: str) -> str:
    fingerprint_path = Path(path)
    return str(fingerprint_path.with_name(f"{fingerprint_path.stem}.run2{fingerprint_path.suffix}"))


def main():
    parser = argparse.ArgumentParser(description="Run a benchmark")
    parser.add_argument("benchmark_path", help="Path to benchmark python file")
    parser.add_argument("--seed", type=int, required=True, help="Random seed")
    parser.add_argument("--out", help="Output JSON path")
    parser.add_argument(
        "--verify-determinism", action="store_true", help="Run twice and assert identical output"
    )
    parser.add_argument("--fingerprint-out", help="Write periodic snapshot fingerprints as JSONL")
    parser.add_argument(
        "--fingerprint-every",
        type=int,
        default=100,
        help="Fingerprint interval in frames (default: 100)",
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
        recorder = None
        if args.fingerprint_out:
            recorder = create_fingerprint_recorder(
                args.fingerprint_out,
                bench_module,
                args.seed,
                args.fingerprint_every,
            )
        try:
            result1 = run_benchmark(bench_module, args.seed, recorder)
            if recorder is not None:
                recorder.finish(result1)
        except Exception:
            if recorder is not None:
                recorder.close()
            raise

        if args.verify_determinism:
            print("Verifying determinism (Run 2)...")
            recorder2 = None
            if args.fingerprint_out:
                recorder2 = create_fingerprint_recorder(
                    second_fingerprint_path(args.fingerprint_out),
                    bench_module,
                    args.seed,
                    args.fingerprint_every,
                )
            try:
                result2 = run_benchmark(bench_module, args.seed, recorder2)
                if recorder2 is not None:
                    recorder2.finish(result2)
            except Exception:
                if recorder2 is not None:
                    recorder2.close()
                raise

            # Compare critical fields
            score_diff = abs(result1["score"] - result2["score"])
            if score_diff > 1e-9:
                print(
                    f"FATAL: Non-deterministic result! Score {result1['score']} != {result2['score']}"
                )
                sys.exit(1)

            if args.fingerprint_out:
                from core.replay.fingerprint_stream import compare_fingerprint_streams

                comparison = compare_fingerprint_streams(
                    args.fingerprint_out, second_fingerprint_path(args.fingerprint_out)
                )
                print(f"Fingerprint comparison: {json.dumps(comparison, sort_keys=True)}")
                if comparison["rounded"] is not None:
                    print("FATAL: Rounded snapshot fingerprints diverged.")
                    sys.exit(1)

            # Compare metadata recursively if needed, but score is the main gate
            print("Determinism check PASSED.")

        # Add environment info
        result1["timestamp"] = __import__("time").time()

        # Stamp the effective-config hash so validators can refuse to compare
        # scores recorded under different configurations (see
        # core/solutions/config_hash.py).
        from core.solutions.config_hash import compute_config_hash

        result1["config_hash"] = compute_config_hash(
            bench_module.BENCHMARK_ID, args.seed, getattr(bench_module, "CONFIG", None)
        )

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
