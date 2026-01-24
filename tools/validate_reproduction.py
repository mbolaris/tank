"""Validate benchmark result matches champion for reproduction.

Usage:
    python tools/validate_reproduction.py result.json path/to/champion.json
"""

import argparse
import json
import sys
from typing import Any, Dict


def validate_reproduction(
    new_result: Dict[str, Any], champion_record: Dict[str, Any], tolerance: float = 1e-9
) -> bool:
    """Check if new result exactly reproduces champion."""

    new_score = new_result["score"]
    old_score = champion_record["score"]

    # Check score
    score_diff = abs(new_score - old_score)
    if score_diff > tolerance:
        print("FAILURE: Score mismatch!")
        print(f"  Expected: {old_score:.12f}")
        print(f"  Actual:   {new_score:.12f}")
        print(f"  Diff:     {score_diff:.12f}")
        return False

    # Check metadata keys
    # We define a set of keys that MUST match for reproduction.
    # If not specified in the benchmark, we check all keys present in the champion's metadata.

    new_meta = new_result.get("metadata", {})
    old_meta = champion_record.get("metadata", {})

    mismatches = []

    for key in old_meta:
        if key not in new_meta:
            mismatches.append(f"Missing key: {key}")
            continue

        val_old = old_meta[key]
        val_new = new_meta[key]

        if isinstance(val_old, (int, float)) and isinstance(val_new, (int, float)):
            if abs(val_old - val_new) > tolerance:
                mismatches.append(f"Value mismatch for '{key}': expected {val_old}, got {val_new}")
        elif val_old != val_new:
            mismatches.append(f"Value mismatch for '{key}': expected {val_old}, got {val_new}")

    if mismatches:
        print("FAILURE: Metadata mismatch!")
        for m in mismatches:
            print(f"  - {m}")
        return False

    print("SUCCESS: Reproduction confirmed.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark reproduction")
    parser.add_argument("result_path", help="Path to result JSON")
    parser.add_argument("champion_path", help="Path to champion JSON")
    parser.add_argument(
        "--tolerance", type=float, default=1e-9, help="Floating point tolerance for equality"
    )

    args = parser.parse_args()

    try:
        with open(args.result_path) as f:
            result = json.load(f)

        with open(args.champion_path) as f:
            champion_data = json.load(f)

        champion_record = champion_data.get("champion", champion_data)

        if not validate_reproduction(result, champion_record, args.tolerance):
            sys.exit(1)

    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
