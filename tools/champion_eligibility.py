"""Shared eligibility checks for benchmark results entering the champion registry."""

from __future__ import annotations

from typing import Any


def result_eligibility_error(result: dict[str, Any]) -> str | None:
    """Return an error when a benchmark result cannot become a champion.

    Older benchmarks may omit ``score_valid``. An explicit false value is a
    hard rejection, both for single-seed results and matrix per-seed records.
    """
    invalid_seeds: list[str] = []
    metadata = result.get("metadata")
    if isinstance(metadata, dict) and metadata.get("score_valid") is False:
        invalid_seeds.append(str(result.get("seed", "primary")))

    per_seed = result.get("per_seed")
    if isinstance(per_seed, dict):
        for seed, record in per_seed.items():
            if not isinstance(record, dict):
                continue
            seed_metadata = record.get("metadata")
            if isinstance(seed_metadata, dict) and seed_metadata.get("score_valid") is False:
                invalid_seeds.append(str(seed))

    if not invalid_seeds:
        return None
    seeds = ", ".join(dict.fromkeys(invalid_seeds))
    return f"result is not eligible for champion use: score_valid=false (seed(s): {seeds})"
