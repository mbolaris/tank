"""Validate benchmark result against champion.

Usage:
    python tools/validate_improvement.py result.json path/to/champion.json [--update-champion]
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, Optional


def is_improvement(
    new_result: Dict[str, Any], champion_data: Optional[Dict[str, Any]], tolerance: float = 1e-9
) -> bool:
    """Check if new result is strictly better than champion."""
    if not champion_data:
        # If no champion exists, any valid result is an "improvement" (or rather, the new champion)
        return True

    try:
        new_score = float(new_result["score"])
        old_score = float(champion_data["champion"]["score"])
    except (KeyError, TypeError, ValueError):
        return False

    # Check for strictly better score
    return new_score - old_score > tolerance


def update_champion_data(
    champion_data: Optional[Dict[str, Any]], new_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Create updated champion data structure."""
    version = 1
    history = []

    if champion_data:
        version = champion_data.get("version", 1) + 1
        history = champion_data.get("history", [])

        # Archive current champion to history
        old_record = champion_data["champion"]
        old_record["retired_at"] = time.time()
        old_record["version"] = champion_data.get("version", 1)
        history.append(old_record)

    return {
        "benchmark_id": new_result.get("benchmark_id", "unknown"),
        "version": version,
        "champion": {
            "score": new_result["score"],
            "seed": new_result["seed"],
            "timestamp": new_result.get("timestamp", time.time()),
            "metadata": new_result.get("metadata", {}),
        },
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
        "--tolerance", type=float, default=1e-9, help="Floating point tolerance for equality"
    )

    args = parser.parse_args()

    try:
        with open(args.result_path) as f:
            result = json.load(f)

        # Check if champion exists
        champion: Optional[Dict[str, Any]] = None
        try:
            with open(args.champion_path) as f:
                champion = json.load(f)
        except FileNotFoundError:
            print(
                f"No existing champion found at {args.champion_path}. Treating result as new champion."
            )

        new_score = float(result["score"])

        if champion:
            old_score = champion["champion"]["score"]
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
