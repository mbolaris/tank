"""Run the frozen multi-seed Tank selection-response assay.

This is the held-out surface for proposal #6: it runs the normal
``tank/selection_response_10k`` benchmark over the frozen seed set 42/7/123 and
returns both the aggregate score and the per-seed decomposition. The benchmark
module itself remains single-seed compatible with ``tools/run_bench.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.tank import selection_response_10k
from core.solutions.config_hash import compute_config_hash


def run_assay(seeds: tuple[int, ...] = selection_response_10k.FROZEN_SEEDS) -> dict[str, Any]:
    per_seed = []
    started = time.time()
    for seed in seeds:
        result = selection_response_10k.run(seed)
        result["config_hash"] = compute_config_hash(
            selection_response_10k.BENCHMARK_ID,
            seed,
            selection_response_10k.CONFIG,
        )
        per_seed.append(result)

    scores = [float(result["score"]) for result in per_seed]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    metadata = _aggregate_metadata(per_seed)
    return {
        "assay_id": "tank/frozen_selection_response_10k",
        "benchmark_id": selection_response_10k.BENCHMARK_ID,
        "seeds": list(seeds),
        "score": mean_score,
        "runtime_seconds": time.time() - started,
        "metadata": metadata,
        "per_seed": per_seed,
    }


def _aggregate_metadata(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_seed:
        return {}
    metrics = [result.get("metadata", {}) for result in per_seed]
    return {
        "frozen_seeds": [result["seed"] for result in per_seed],
        "mean_score": round(sum(float(result["score"]) for result in per_seed) / len(per_seed), 4),
        "all_selection_detected": all(bool(m.get("selection_detected")) for m in metrics),
        "mean_selected_trait_fraction": _mean(metrics, "selected_trait_fraction"),
        "mean_drift_per_generation_pct": _mean(metrics, "drift_per_generation_pct"),
        "mean_diversity_delta": _mean(metrics, "diversity_delta"),
        "mean_diversity_retention": _mean(metrics, "diversity_retention"),
        "mean_quality_per_generation": _mean(metrics, "quality_per_generation"),
        "mean_generation_rate_per_10k": _mean(metrics, "generation_rate_per_10k"),
        "min_final_diversity": min(float(m.get("diversity_last", 0.0) or 0.0) for m in metrics),
        "score_formula": (
            "mean of per-seed selection_response_10k scores over frozen seeds 42/7/123"
        ),
        "anti_goodhart_note": (
            "Use this as a held-out decomposition. PRs that edit the assay should not "
            "claim score wins from the edited assay in the same change."
        ),
    }


def _mean(items: list[dict[str, Any]], key: str) -> float:
    values = [float(item[key]) for item in items if isinstance(item.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else 0.0


def _parse_seeds(raw: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=selection_response_10k.FROZEN_SEEDS,
        help="Comma-separated seeds; default is the frozen held-out set 42,7,123",
    )
    parser.add_argument("--out", help="Write JSON result to this path")
    args = parser.parse_args()

    result = run_assay(args.seeds)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Result written to {args.out}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
