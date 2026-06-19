"""Validate benchmark result against champion.

Usage:
    python tools/validate_improvement.py result.json path/to/champion.json [--update-champion]
"""

import argparse
import json
import sys
import time
from typing import Any


def get_champion_record(champion_data: dict[str, Any]) -> dict[str, Any]:
    """Extract the champion record, supporting both formats.

    Standard format nests the record under a "champion" key; legacy format
    stores score/seed/metadata at the top level (as written by run_bench.py).
    """
    if "champion" in champion_data:
        return champion_data["champion"]
    return champion_data


def check_config_compatibility(
    new_result: dict[str, Any], champion_data: dict[str, Any] | None
) -> str | None:
    """Return an error message if the result and champion configs are incomparable.

    Scores are only comparable when both runs used the same effective
    configuration (same benchmark config, same core config, same seed).
    Returns None when comparison is allowed; a legacy champion without a
    config_hash is allowed through (the backfill script adds hashes).
    """
    if not champion_data:
        return None

    new_hash = new_result.get("config_hash")
    old_hash = get_champion_record(champion_data).get("config_hash")

    if old_hash is None or new_hash is None:
        return None

    if new_hash != old_hash:
        return (
            f"CONFIG MISMATCH: result config_hash={new_hash} but champion "
            f"config_hash={old_hash}.\n"
            "The benchmark/core configuration (or seed) changed since the champion "
            "was recorded, so a score comparison would be meaningless.\n"
            "Config changed - re-baseline: re-run the benchmark on the champion's "
            "code to record a new champion, then compare against that."
        )

    return None


def is_improvement(
    new_result: dict[str, Any], champion_data: dict[str, Any] | None, tolerance: float = 1e-9
) -> bool:
    """Check if new result is strictly better than champion."""
    if not champion_data:
        # If no champion exists, any valid result is an "improvement" (or rather, the new champion)
        return True

    try:
        new_score = float(new_result["score"])
        old_score = float(get_champion_record(champion_data)["score"])
    except (KeyError, TypeError, ValueError):
        return False

    # Check for strictly better score
    return new_score - old_score > tolerance


def update_champion_data(
    champion_data: dict[str, Any] | None,
    new_result: dict[str, Any],
    retired_reason: str = "Superseded by a higher-scoring champion.",
) -> dict[str, Any]:
    """Create updated champion data structure."""
    version = 1
    history = []

    if champion_data:
        version = champion_data.get("version", 1) + 1
        history = champion_data.get("history", [])

        # Archive current champion to history (handles legacy flat format too)
        old_record = dict(get_champion_record(champion_data))
        old_record["benchmark_id"] = champion_data.get(
            "benchmark_id", new_result.get("benchmark_id", "unknown")
        )
        old_record["retired_at"] = time.time()
        old_record["retired_reason"] = retired_reason
        old_record["version"] = champion_data.get("version", 1)
        # Prepend so history stays newest-first; test_champion_provenance
        # enforces strictly descending versions. Appending broke that ordering
        # whenever existing history was already newest-first.
        history.insert(0, old_record)

    new_champion: dict[str, Any] = {
        "score": new_result["score"],
        "seed": new_result["seed"],
        "timestamp": new_result.get("timestamp", time.time()),
        "metadata": new_result.get("metadata", {}),
    }
    if "config_hash" in new_result:
        new_champion["config_hash"] = new_result["config_hash"]

    return {
        "benchmark_id": new_result.get("benchmark_id", "unknown"),
        "version": version,
        "champion": new_champion,
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark improvement")
    parser.add_argument("result_path", help="Path to result JSON")
    parser.add_argument("champion_path", help="Path to champion JSON")
    parser.add_argument(
        "--update-champion", action="store_true", help="Overwrite champion if strictly better"
    )
    parser.add_argument(
        "--rebaseline",
        action="store_true",
        help=(
            "Record this result as the new champion regardless of score, archiving the "
            "old one. Use when the existing champion no longer reproduces (e.g. after a "
            "determinism fix). Still requires a matching config_hash."
        ),
    )
    parser.add_argument(
        "--tolerance", type=float, default=1e-9, help="Floating point tolerance for equality"
    )

    args = parser.parse_args()

    try:
        with open(args.result_path) as f:
            result = json.load(f)

        # Check if champion exists
        champion: dict[str, Any] | None = None
        try:
            with open(args.champion_path) as f:
                champion = json.load(f)
        except FileNotFoundError:
            print(
                f"No existing champion found at {args.champion_path}. Treating result as new champion."
            )

        config_error = check_config_compatibility(result, champion)
        if config_error:
            print(config_error)
            sys.exit(1)

        new_score = float(result["score"])

        # Re-baseline: forcibly record the result as the new champion. Used when
        # the existing champion no longer reproduces (config_hash still matches,
        # checked above). Bypasses the strictly-better requirement.
        if args.rebaseline:
            reason = (
                "Re-baselined: prior champion no longer reproduced on current "
                "code (cross-process determinism fix, ADR-012)."
            )
            new_champion_data = update_champion_data(champion, result, retired_reason=reason)
            with open(args.champion_path, "w") as f:
                json.dump(new_champion_data, f, indent=2)
            old = f"{float(get_champion_record(champion)['score']):.6f}" if champion else "none"
            print(f"Re-baselined {args.champion_path}: {old} -> {new_score:.6f}")
            return

        if champion:
            old_score = get_champion_record(champion)["score"]
            diff = new_score - float(old_score)

            print(f"New Score: {new_score:.6f}")
            print(f"Old Score: {old_score:.6f}")
            print(f"Diff:      {diff:+.6f}")

            if diff < -args.tolerance:
                print("FAILURE: Regression detected.")
                sys.exit(1)
            elif abs(diff) <= args.tolerance:
                print("Result matches champion (within tolerance).")
            else:
                print("SUCCESS: Improvement detected!")
        else:
            print(f"New Score: {new_score:.6f} (Initial Champion)")

        # Update champion logic
        if args.update_champion:
            if is_improvement(result, champion, args.tolerance):
                new_champion_data = update_champion_data(champion, result)

                with open(args.champion_path, "w") as f:
                    json.dump(new_champion_data, f, indent=2)
                print(f"Updated champion at {args.champion_path}")
            else:
                print("Not updating champion (not strictly better).")

    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
