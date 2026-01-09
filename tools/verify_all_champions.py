"""Verify all champions reproduce.

Usage:
    python tools/verify_all_champions.py
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

# Use absolute paths based on script location so this works from any cwd
ROOT = Path(__file__).resolve().parents[1]


def main():
    champions_dir = ROOT / "champions"
    benchmarks_dir = ROOT / "benchmarks"

    champion_files = glob.glob(os.path.join(champions_dir, "**", "*.json"), recursive=True)

    if not champion_files:
        print("No champions found.")
        return

    failed = False

    for champ_path in champion_files:
        print(f"Verifying {champ_path}...")

        try:
            with open(champ_path) as f:
                champ_data = json.load(f)

            bench_id = champ_data.get("benchmark_id")
            if not bench_id:
                print(f"  SKIP: No benchmark_id in {champ_path}")
                continue

            # Support both standard (nested) and legacy (flat) format
            if "champion" in champ_data:
                seed = champ_data["champion"].get("seed")
            else:
                seed = champ_data.get("seed")

            if seed is None:
                print(f"  ERROR: Could not find seed in {champ_path}")
                failed = True
                continue

            # Find benchmark file
            # benchmark_id "tank/survival_30k" -> benchmarks/tank/survival_30k.py
            bench_path = os.path.join(benchmarks_dir, f"{bench_id}.py")
            if not os.path.exists(bench_path):
                print(f"  ERROR: Benchmark file {bench_path} not found")
                failed = True
                continue

            # Run benchmark
            out_file = f"verify_{os.path.basename(bench_id)}.json"
            cmd = [
                sys.executable,
                str(ROOT / "tools" / "run_bench.py"),
                str(bench_path),
                "--seed",
                str(seed),
                "--out",
                out_file,
            ]

            subprocess.check_call(cmd)

            # Validate reproduction
            cmd_val = [
                sys.executable,
                str(ROOT / "tools" / "validate_reproduction.py"),
                out_file,
                champ_path,
            ]

            subprocess.check_call(cmd_val)

            # Clean up
            if os.path.exists(out_file):
                os.remove(out_file)

        except Exception as e:
            print(f"  FAILED: {e}")
            failed = True

    if failed:
        sys.exit(1)
    else:
        print("All champions verified successfully.")


if __name__ == "__main__":
    main()
