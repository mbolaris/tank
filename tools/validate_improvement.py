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
        record: dict[str, Any] = champion_data["champion"]
        return record
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
    if "score_breakdown" in new_result:
        new_champion["score_breakdown"] = new_result["score_breakdown"]
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
        with open(args.result_path, encoding="utf-8") as f:
            result = json.load(f)

        # Check if champion exists
        champion: dict[str, Any] | None = None
        try:
            with open(args.champion_path, encoding="utf-8") as f:
                champion = json.load(f)
        except FileNotFoundError:
            print(
                f"No existing champion found at {args.champion_path}. Treating result as new champion."
            )

        config_error = check_config_compatibility(result, champion)
        if config_error:
            print(config_error)
            try:
                from core.research.attempt_ledger import log_attempt

                log_attempt(
                    benchmark_id=result.get("benchmark_id", "unknown"),
                    verdict="error",
                    candidate_score=float(result["score"]) if "score" in result else None,
                    champion_score=(
                        float(get_champion_record(champion)["score"]) if champion else None
                    ),
                    seed=result.get("seed"),
                    config_hash=result.get("config_hash"),
                    description=f"Config error: {config_error.splitlines()[0]}",
                )
            except Exception as le:
                print(f"Warning: Failed to log attempt: {le}")
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
            with open(args.champion_path, "w", encoding="utf-8") as f:
                json.dump(new_champion_data, f, indent=2)
            old = f"{float(get_champion_record(champion)['score']):.6f}" if champion else "none"
            print(f"Re-baselined {args.champion_path}: {old} -> {new_score:.6f}")
            try:
                from core.research.attempt_ledger import log_attempt

                log_attempt(
                    benchmark_id=result.get("benchmark_id", "unknown"),
                    verdict="accepted",
                    candidate_score=new_score,
                    champion_score=(
                        float(get_champion_record(champion)["score"]) if champion else None
                    ),
                    seed=result.get("seed"),
                    config_hash=result.get("config_hash"),
                    description=reason,
                )
            except Exception as le:
                print(f"Warning: Failed to log attempt: {le}")
            return

        new_breakdown = result.get("score_breakdown")
        champion_score = float(get_champion_record(champion)["score"]) if champion else None
        verdict = "rejected"
        description = "No improvement (matches or below tolerance)"

        if champion:
            old_record = get_champion_record(champion)
            old_score = old_record["score"]
            diff = new_score - float(old_score)

            print(f"New Score: {new_score:.6f}")
            print(f"Old Score: {old_score:.6f}")
            print(f"Diff:      {diff:+.6f}")

            # Extract old breakdown
            old_breakdown = old_record.get("score_breakdown")
            if not old_breakdown:
                old_breakdown = old_record.get("metadata", {}).get("score_breakdown")
            if not new_breakdown:
                new_breakdown = result.get("metadata", {}).get("score_breakdown")

            if new_breakdown or old_breakdown:
                print("\nScore Breakdown:")
                keys = sorted(set((new_breakdown or {}).keys()) | set((old_breakdown or {}).keys()))

                weakest_key = None
                weakest_pct = float("inf")
                weakest_new = None
                weakest_old = None

                for key in keys:
                    new_val = (new_breakdown or {}).get(key)
                    old_val = (old_breakdown or {}).get(key)

                    new_str = (
                        f"{new_val:.4f}" if isinstance(new_val, (int, float)) else str(new_val)
                    )
                    old_str = (
                        f"{old_val:.4f}" if isinstance(old_val, (int, float)) else str(old_val)
                    )

                    if new_val is not None and old_val is not None:
                        if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
                            diff_val = new_val - old_val
                            diff_str = f" ({diff_val:+.4f})"
                            # Track weakest component (lowest % change, or absolute diff if old_val is 0)
                            if old_val != 0:
                                pct_change = (new_val - old_val) / abs(old_val)
                            else:
                                pct_change = new_val - old_val
                            if pct_change < weakest_pct:
                                weakest_pct = pct_change
                                weakest_key = key
                                weakest_new = new_val
                                weakest_old = old_val
                        else:
                            diff_str = ""
                        print(f"  {key}: {new_str} (champion: {old_str}){diff_str}")
                    elif new_val is not None:
                        print(f"  {key}: {new_str} (champion: N/A)")
                    elif old_val is not None:
                        print(f"  {key}: N/A (champion: {old_str})")

                if weakest_key is not None:
                    if weakest_old != 0:
                        pct_change_str = f"{weakest_pct * 100:+.2f}%"
                    else:
                        pct_change_str = f"{weakest_pct:+.4f}"
                    print(
                        f"Weakest component: {weakest_key} ({weakest_new:.4f} vs champion {weakest_old:.4f}, {pct_change_str})"
                    )
                print("")

            if diff < -args.tolerance:
                print("FAILURE: Regression detected.")
                verdict = "rejected"
                description = "Regression detected"
                try:
                    from core.research.attempt_ledger import log_attempt

                    log_attempt(
                        benchmark_id=result.get("benchmark_id", "unknown"),
                        verdict=verdict,
                        candidate_score=new_score,
                        champion_score=champion_score,
                        seed=result.get("seed"),
                        config_hash=result.get("config_hash"),
                        description=description,
                    )
                except Exception as le:
                    print(f"Warning: Failed to log attempt: {le}")
                sys.exit(1)
            elif abs(diff) <= args.tolerance:
                print("Result matches champion (within tolerance).")
                verdict = "rejected"
                description = "Result matches champion within tolerance"
            else:
                print("SUCCESS: Improvement detected!")
                verdict = "accepted"
                description = "Improvement detected"
        else:
            print(f"New Score: {new_score:.6f} (Initial Champion)")
            verdict = "accepted"
            description = "Initial champion"
            if new_breakdown:
                print("\nScore Breakdown:")
                for key, val in sorted(new_breakdown.items()):
                    val_str = f"{val:.4f}" if isinstance(val, (int, float)) else str(val)
                    print(f"  {key}: {val_str}")
                print("")

        # Update champion logic
        if args.update_champion:
            if is_improvement(result, champion, args.tolerance):
                new_champion_data = update_champion_data(champion, result)

                with open(args.champion_path, "w", encoding="utf-8") as f:
                    json.dump(new_champion_data, f, indent=2)
                print(f"Updated champion at {args.champion_path}")
            else:
                print("Not updating champion (not strictly better).")

        try:
            from core.research.attempt_ledger import log_attempt

            log_attempt(
                benchmark_id=result.get("benchmark_id", "unknown"),
                verdict=verdict,
                candidate_score=new_score,
                champion_score=champion_score,
                seed=result.get("seed"),
                config_hash=result.get("config_hash"),
                description=description,
            )
        except Exception as le:
            print(f"Warning: Failed to log attempt: {le}")

    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
