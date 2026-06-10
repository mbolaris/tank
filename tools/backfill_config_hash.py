"""Backfill config_hash into existing champion records.

One-shot migration for docs/IMPROVEMENT_PROPOSALS.md section 1.1: stamps every
champions/**/*.json champion record with the config hash of the *current*
configuration. This is only valid when the champions still reproduce under the
current config (which tools/verify_all_champions.py checks in CI).

Usage:
    python tools/backfill_config_hash.py [--dry-run]
"""

import argparse
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.solutions.config_hash import compute_config_hash


def load_benchmark_module(path: str):
    module_name = os.path.basename(path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load benchmark from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill config_hash into champions")
    parser.add_argument("--dry-run", action="store_true", help="Print hashes without writing")
    args = parser.parse_args()

    champion_files = sorted(
        glob.glob(os.path.join(ROOT / "champions", "**", "*.json"), recursive=True)
    )
    if not champion_files:
        print("No champions found.")
        return 0

    failed = False
    for champ_path in champion_files:
        with open(champ_path) as f:
            champ_data = json.load(f)

        bench_id = champ_data.get("benchmark_id")
        record = champ_data.get("champion", champ_data)
        seed = record.get("seed")
        if not bench_id or seed is None:
            print(f"SKIP {champ_path}: missing benchmark_id or seed")
            failed = True
            continue

        bench_path = ROOT / "benchmarks" / f"{bench_id}.py"
        if not bench_path.exists():
            print(f"SKIP {champ_path}: benchmark file {bench_path} not found")
            failed = True
            continue

        bench_module = load_benchmark_module(str(bench_path))
        config_hash = compute_config_hash(
            bench_id, int(seed), getattr(bench_module, "CONFIG", None)
        )

        existing = record.get("config_hash")
        if existing == config_hash:
            print(f"OK   {champ_path}: config_hash already {config_hash}")
            continue

        verb = "would set" if args.dry_run else "set"
        print(
            f"{'PLAN' if args.dry_run else 'DONE'} {champ_path}: {verb} config_hash={config_hash}"
        )

        if not args.dry_run:
            record["config_hash"] = config_hash
            if "champion" in champ_data:
                champ_data["champion"] = record
            with open(champ_path, "w") as f:
                json.dump(champ_data, f, indent=2)
                f.write("\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
