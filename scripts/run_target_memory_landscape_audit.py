"""Target Memory Landscape Audit.

Generates 2D grid maps (11x11) for specified parameter pairs to understand:
- Parameter interactions
- Optimality regions
- Ridges of equivalent solutions
- Epistasis vs independence

Pairs:
1. confidence_decay x switch_threshold
2. confidence_decay x commitment_strength
3. switch_threshold x commitment_strength
4. memory_duration x motion_extrapolation_duration

Outputs a JSON and a Markdown file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.behavior.target_memory import TargetMemoryParams, _PARAM_BOUNDS
from core.behavior.target_memory_transfer_gym import (
    evaluate_params_on_set,
    generate_scenario_set,
)

GRID_STEPS = 11

PAIRS = [
    ("memory_duration", "motion_extrapolation_duration"),
]


def _make_params_with(**overrides: float) -> TargetMemoryParams:
    defaults = TargetMemoryParams()
    fields = {
        "memory_duration": defaults.memory_duration,
        "confidence_decay": defaults.confidence_decay,
        "switch_threshold": defaults.switch_threshold,
        "commitment_strength": defaults.commitment_strength,
        "motion_extrapolation_duration": defaults.motion_extrapolation_duration,
    }
    fields.update(overrides)
    return TargetMemoryParams(**fields)


def evaluate_grid_point(
    p1: str,
    v1: float,
    p2: str,
    v2: float,
    scenarios: list,
) -> float:
    params = _make_params_with(**{p1: v1, p2: v2})
    return evaluate_params_on_set(params, scenarios).overall_score


def _run_grid_point_worker(args: tuple) -> tuple[str, int, int, float]:
    pair_idx, i, j, p1, v1, p2, v2, seed, domain, count = args
    if domain == "food":
        scenarios = generate_scenario_set("validation", seed, count=count)
    else:
        scenarios = generate_scenario_set("ball_validation", seed, count=count)
    score = evaluate_grid_point(p1, v1, p2, v2, scenarios)
    return f"{p1}_x_{p2}", i, j, score


def run_landscape_audit(
    seed: int = 42,
    food_count: int = 8,
    ball_count: int = 8,
    max_workers: int = 4,
) -> dict[str, Any]:
    t0 = time.perf_counter()

    results: dict[str, dict[str, Any]] = {"food": {}, "ball": {}}

    for domain in ("food", "ball"):
        count = food_count if domain == "food" else ball_count
        print(f"Mapping grids for {domain} domain...")

        # Initialize empty grids
        for p1, p2 in PAIRS:
            key = f"{p1}_x_{p2}"
            lo1, hi1 = _PARAM_BOUNDS[p1]
            lo2, hi2 = _PARAM_BOUNDS[p2]
            results[domain][key] = {
                "param1": p1,
                "param2": p2,
                "values1": [lo1 + (hi1 - lo1) * i / (GRID_STEPS - 1) for i in range(GRID_STEPS)],
                "values2": [lo2 + (hi2 - lo2) * j / (GRID_STEPS - 1) for j in range(GRID_STEPS)],
                "grid": [[0.0] * GRID_STEPS for _ in range(GRID_STEPS)],
            }

        # Build tasks
        tasks = []
        for pair_idx, (p1, p2) in enumerate(PAIRS):
            key = f"{p1}_x_{p2}"
            grid_meta = results[domain][key]
            for i, v1 in enumerate(grid_meta["values1"]):
                for j, v2 in enumerate(grid_meta["values2"]):
                    tasks.append((pair_idx, i, j, p1, v1, p2, v2, seed, domain, count))

        if max_workers > 1:
            with ProcessPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_run_grid_point_worker, t): t for t in tasks}
                for future in as_completed(futures):
                    key, i, j, score = future.result()
                    results[domain][key]["grid"][i][j] = score
        else:
            for t in tasks:
                key, i, j, score = _run_grid_point_worker(t)
                results[domain][key]["grid"][i][j] = score

    elapsed = time.perf_counter() - t0
    return {
        "audit_version": "v1",
        "seed": seed,
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Target Memory Landscape Audit (2D Grids)",
        "",
        f"Seed: `{report['seed']}` | Grid: {GRID_STEPS}x{GRID_STEPS} | Elapsed: {report['elapsed_seconds']}s",
        "",
    ]

    for domain in ("food", "ball"):
        lines.append(f"## {domain.title()} Domain")
        lines.append("")

        domain_results = report["results"][domain]
        for key, data in domain_results.items():
            p1 = data["param1"]
            p2 = data["param2"]
            v1_list = data["values1"]
            v2_list = data["values2"]
            grid = data["grid"]

            lines.append(f"### {p1} vs {p2}")
            lines.append("")
            # Print as markdown table
            # Columns are v2 values, rows are v1 values
            headers = [f"{p2} = {v:.3f}" for v in v2_list]
            lines.append(f"| {p1} | " + " | ".join(headers) + " |")
            lines.append("|---| " + " | ".join(["---"] * len(v2_list)) + " |")

            for i, v1 in enumerate(v1_list):
                row_cells = [f"{grid[i][j]:.4f}" for j in range(len(v2_list))]
                lines.append(f"| **{v1:.3f}** | " + " | ".join(row_cells) + " |")
            lines.append("")

            # Find min and max
            flat_grid = [grid[i][j] for i in range(len(v1_list)) for j in range(len(v2_list))]
            min_val = min(flat_grid)
            max_val = max(flat_grid)
            default_val = evaluate_grid_point(
                p1,
                getattr(TargetMemoryParams(), p1),
                p2,
                getattr(TargetMemoryParams(), p2),
                generate_scenario_set(
                    "validation" if domain == "food" else "ball_validation", report["seed"], count=8
                ),
            )
            lines.append(
                f"**Stats**: Min: `{min_val:.4f}` | Max: `{max_val:.4f}` | Default: `{default_val:.4f}` | Spread: `{max_val - min_val:.4f}`"
            )
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Target Memory Landscape Audit")
    parser.add_argument(
        "--output", default="research/target_memory_transfer/landscape_audit_v4.json"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("-j", "--workers", type=int, default=4)
    args = parser.parse_args()

    print(f"Running landscape audit with seed={args.seed}, workers={args.workers}")
    report = run_landscape_audit(seed=args.seed, max_workers=args.workers)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}")

    md_path = out_path.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Summary: {md_path}")


if __name__ == "__main__":
    main()
