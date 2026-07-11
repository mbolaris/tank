"""Run a benchmark and output results JSON.

Usage:
    python tools/run_bench.py path/to/benchmark.py --seed 123 --out result.json
"""

import argparse
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
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


def expected_runtime_seconds(bench_module) -> float | None:
    """Return the benchmark's advertised wall-clock budget, if any."""
    budget = getattr(bench_module, "EXPECTED_RUNTIME_SECONDS", None)
    if budget is None:
        return None
    return float(budget)


def format_runtime_summary(elapsed_seconds: float | None, budget_seconds: float | None) -> str:
    """Format the benchmark runtime line printed after completion."""
    if elapsed_seconds is None:
        return "Runtime: unavailable"
    if budget_seconds is None:
        return f"Runtime: {elapsed_seconds:.1f}s (no budget recorded)"
    return f"Runtime: {elapsed_seconds:.1f}s (budget ~{budget_seconds:g}s)"


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
    parser.add_argument(
        "--record-skill",
        action="store_true",
        help="Append frozen-ruler skill rows to the longitudinal skill ledger",
    )
    parser.add_argument(
        "--skill-ledger",
        default="research/skill_history.jsonl",
        help="Skill ledger path used with --record-skill",
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
        budget_seconds = expected_runtime_seconds(bench_module)
        # Timeout for each subprocess: 3× budget if available, else 10 minutes.
        subprocess_timeout = int(budget_seconds * 3) if budget_seconds else 600

        if not args.verify_determinism:
            # Normal single run (in-process).
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
        else:
            # Determinism verification: run both checks as fresh subprocesses
            # so in-process global state (threads, WorldRegistry, asyncio loops)
            # cannot prevent clean exit. Explicit timeouts prevent CI from hanging.
            print("Verifying determinism (subprocess-vs-subprocess)...", flush=True)
            temp_out1 = tempfile.NamedTemporaryFile(suffix=".json", delete=False)  # noqa: SIM115
            temp_out2 = tempfile.NamedTemporaryFile(suffix=".json", delete=False)  # noqa: SIM115
            temp_out1.close()
            temp_out2.close()

            cmd_base = [sys.executable, __file__, args.benchmark_path, "--seed", str(args.seed)]

            # Run 1
            cmd1 = cmd_base + ["--out", temp_out1.name]
            if args.fingerprint_out:
                cmd1 += [
                    "--fingerprint-out",
                    args.fingerprint_out,
                    "--fingerprint-every",
                    str(args.fingerprint_every),
                ]
            print("Running determinism check: Run 1...", flush=True)
            try:
                res1 = subprocess.run(
                    cmd1, capture_output=True, text=True, timeout=subprocess_timeout
                )
            except subprocess.TimeoutExpired:
                print(
                    f"Error: Run 1 timed out after {subprocess_timeout}s",
                    file=sys.stderr,
                )
                sys.exit(1)
            if res1.returncode != 0:
                print(
                    f"Error: Run 1 failed with exit code {res1.returncode}\nSTDOUT:\n{res1.stdout}\nSTDERR:\n{res1.stderr}",
                    file=sys.stderr,
                )
                sys.exit(res1.returncode)

            # Run 2
            cmd2 = cmd_base + ["--out", temp_out2.name]
            if args.fingerprint_out:
                cmd2 += [
                    "--fingerprint-out",
                    second_fingerprint_path(args.fingerprint_out),
                    "--fingerprint-every",
                    str(args.fingerprint_every),
                ]
            print("Running determinism check: Run 2...", flush=True)
            try:
                res2 = subprocess.run(
                    cmd2, capture_output=True, text=True, timeout=subprocess_timeout
                )
            except subprocess.TimeoutExpired:
                print(
                    f"Error: Run 2 timed out after {subprocess_timeout}s",
                    file=sys.stderr,
                )
                sys.exit(1)
            if res2.returncode != 0:
                print(
                    f"Error: Run 2 failed with exit code {res2.returncode}\nSTDOUT:\n{res2.stdout}\nSTDERR:\n{res2.stderr}",
                    file=sys.stderr,
                )
                sys.exit(res2.returncode)

            # Parse output JSONs (result1 comes from the subprocess, not in-process)
            with open(temp_out1.name) as f:
                result1 = json.load(f)
            with open(temp_out2.name) as f:
                result2 = json.load(f)

            # Cleanup temp files
            try:
                os.unlink(temp_out1.name)
                os.unlink(temp_out2.name)
            except Exception:
                pass

            # Compare critical fields
            score_diff = abs(result1["score"] - result2["score"])
            if score_diff > 1e-9:
                print(
                    f"FATAL: Non-deterministic result! Score {result1['score']} != {result2['score']}",
                    file=sys.stderr,
                )
                sys.exit(1)

            if args.fingerprint_out:
                from core.replay.fingerprint_stream import compare_fingerprint_streams

                comparison = compare_fingerprint_streams(
                    args.fingerprint_out, second_fingerprint_path(args.fingerprint_out)
                )
                print(f"Fingerprint comparison: {json.dumps(comparison, sort_keys=True)}")
                if comparison["rounded"] is not None:
                    print("FATAL: Rounded snapshot fingerprints diverged.", file=sys.stderr)
                    sys.exit(1)

            print("Determinism check PASSED.")

        result1["expected_runtime_seconds"] = budget_seconds
        elapsed_seconds = result1.get("runtime_seconds")
        elapsed_for_summary = (
            float(elapsed_seconds) if isinstance(elapsed_seconds, (int, float)) else None
        )
        print(format_runtime_summary(elapsed_for_summary, budget_seconds))

        # Add environment info
        result1["timestamp"] = time.time()

        # Stamp the effective-config hash so validators can refuse to compare
        # scores recorded under different configurations (see
        # core/solutions/config_hash.py).
        from core.solutions.config_hash import compute_config_hash

        result1["config_hash"] = compute_config_hash(
            bench_module.BENCHMARK_ID, args.seed, getattr(bench_module, "CONFIG", None)
        )

        if args.record_skill:
            from core.research.skill_ledger import append_skill_history
            from core.skill import SkillLadderSummary

            skill_data = result1.get("metadata", {}).get("skill")
            if not isinstance(skill_data, dict):
                raise ValueError(
                    f"{bench_module.BENCHMARK_ID} did not emit metadata.skill; "
                    "--record-skill requires a frozen-ruler benchmark"
                )
            rows = append_skill_history(
                SkillLadderSummary.from_dict(skill_data),
                seeds=[args.seed],
                config_hash=result1["config_hash"],
                ledger_path=args.skill_ledger,
                command=" ".join(sys.argv),
            )
            print(f"Skill history appended: {rows} rows to {args.skill_ledger}")

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
