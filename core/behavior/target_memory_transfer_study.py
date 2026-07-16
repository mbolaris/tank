"""Multi-run aggregation for the target-memory transfer study.

The per-seed benchmark (benchmarks/tank/target_memory_transfer.py) is a
single observation at a deliberately small, CI-fast budget; its scores are
trajectory-sensitive and must never be read as a transfer conclusion. This
module turns many independent observations - larger budgets, several
evolution runs per arm, many outer seeds - into an aggregate report with
uncertainty: mean/median effects, bootstrap confidence intervals, the
fraction of seeds showing a positive effect, and per-ball-family breakdowns.

The decision rule is deliberately conservative and symmetric:

- ``positive``/``negative`` verdicts require the 95% bootstrap CI of the
  mean effect to exclude zero;
- anything else is ``inconclusive`` - a valid, reportable finding, not a
  failure (demonstrating that food specialization does not transfer, or
  actively hurts, is itself a result worth keeping).

No champion should be created from an inconclusive verdict; see
docs/EVO_CONTRIBUTING.md for the evidence bar.

Run via scripts/run_target_memory_transfer_study.py.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import asdict
from typing import Any

from core.behavior.target_memory_transfer_evolution import (
    TransferStudyConfig,
    evaluate_target_memory_transfer,
)
from core.behavior.target_memory_transfer_scenarios import SCENARIO_SET_VERSION

# The scaled budget for real evidence runs: within the ranges the study
# design calls for (32-64 individuals, 30-50 generations, 5 independent
# runs, 16-32 training scenarios, 8-16 validation, 16+ held-out) while
# staying tractable on a single machine (~10 min/seed single-core).
SCALED_STUDY_CONFIG = TransferStudyConfig(
    population_size=32,
    generations=30,
    evolution_runs=5,
    food_train_count=16,
    food_validation_count=8,
    ball_held_out_count=16,
    ball_train_count=16,
    ball_validation_count=8,
)

# Twelve outer seeds: ten consecutive plus the two historically-reported
# ones (42, 123 - see CLAUDE.md's multi-seed guidance), fixed so studies
# are comparable across runs of the tool.
DEFAULT_STUDY_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 42, 123)

_BOOTSTRAP_ITERATIONS = 10_000
_BOOTSTRAP_RNG_SEED = 1234


def seed_row(seed: int, config: TransferStudyConfig) -> dict[str, Any]:
    """Run one full transfer evaluation and flatten it into a report row."""
    evaluation = evaluate_target_memory_transfer(seed, config)
    groups = evaluation.group_summaries
    food = groups["food_trained"]
    default = groups["default_params"]
    neutral = groups["neutral_evolution"]

    family_effect_vs_default = {
        fam: food.family_fitness[fam] - default.family_fitness[fam]
        for fam in sorted(default.family_fitness)
        if fam in food.family_fitness
    }

    # Validity ladder gains
    memory_mechanism_gain = default.overall_score - groups["naive_greedy"].overall_score
    source_learning_gain = (
        evaluation.food_validation_score_food_trained - evaluation.food_validation_score_default
        if evaluation.food_validation_score_food_trained is not None
        and evaluation.food_validation_score_default is not None
        else 0.0
    )
    target_learnability_gain = groups["ball_trained"].overall_score - default.overall_score

    return {
        "seed": seed,
        "group_scores": {name: summary.overall_score for name, summary in groups.items()},
        "transfer_vs_disjoint": food.overall_score - default.overall_score,
        "transfer_vs_neutral": food.overall_score - neutral.overall_score,
        "memory_mechanism_gain": memory_mechanism_gain,
        "source_learning_gain": source_learning_gain,
        "target_learnability_gain": target_learnability_gain,
        "family_effect_vs_default": family_effect_vs_default,
        "adaptation_reference_established": evaluation.adaptation_reference_established,
        "adaptation_reference_gap": evaluation.adaptation_reference_gap,
        "adaptation_generations_food": evaluation.adaptation_generations_food,
        "adaptation_generations_default": evaluation.adaptation_generations_default,
        "food_trained_genomes": evaluation.food_trained_genomes,
        "ball_trained_genomes": evaluation.ball_trained_genomes,
        "diagnostics": {
            name: {
                "mean_switches": summary.mean_switches,
                "mean_stale_pursuit_frames": summary.mean_stale_pursuit_frames,
                "mean_reacquisition_frames": summary.mean_reacquisition_frames,
                "mean_distance_traveled": summary.mean_distance_traveled,
                "mean_occlusion_survived_ratio": summary.mean_occlusion_survived_ratio,
                "mean_occlusion_dropped_ratio": summary.mean_occlusion_dropped_ratio,
                "mean_wasted_frames": summary.mean_wasted_frames,
                "mean_chasing_stale_frames": summary.mean_chasing_stale_frames,
                "mean_distance_error_at_reappearance": summary.mean_distance_error_at_reappearance,
            }
            for name, summary in groups.items()
        },
    }


def bootstrap_ci(
    values: list[float],
    iterations: int = _BOOTSTRAP_ITERATIONS,
    rng_seed: int = _BOOTSTRAP_RNG_SEED,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Deterministic percentile bootstrap CI for the mean of ``values``."""
    if not values:
        raise ValueError("bootstrap_ci needs at least one value")
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(rng_seed)
    n = len(values)
    means = sorted(sum(rng.choice(values) for _ in range(n)) / n for _ in range(iterations))
    alpha = (1.0 - confidence) / 2.0
    lo_idx = int(alpha * iterations)
    hi_idx = min(iterations - 1, int((1.0 - alpha) * iterations))
    return (means[lo_idx], means[hi_idx])


def _effect_stats(values: list[float]) -> dict[str, Any]:
    ci_low, ci_high = bootstrap_ci(values)
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "fraction_positive": sum(1 for v in values if v > 0) / len(values),
        "verdict": _verdict(ci_low, ci_high),
    }


def _verdict(ci_low: float, ci_high: float) -> str:
    if ci_low > 0.0:
        return "positive"
    if ci_high < 0.0:
        return "negative"
    return "inconclusive"


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold per-seed rows into the uncertainty-aware aggregate report."""
    if not rows:
        raise ValueError("aggregate_rows needs at least one per-seed row")
    rows = sorted(rows, key=lambda r: r["seed"])

    effects = {
        "transfer_vs_disjoint": _effect_stats([r["transfer_vs_disjoint"] for r in rows]),
        "transfer_vs_neutral": _effect_stats([r["transfer_vs_neutral"] for r in rows]),
        "memory_mechanism_gain": _effect_stats([r["memory_mechanism_gain"] for r in rows]),
        "source_learning": _effect_stats([r["source_learning_gain"] for r in rows]),
        "target_learnability": _effect_stats([r["target_learnability_gain"] for r in rows]),
    }

    family_names = sorted({fam for r in rows for fam in r["family_effect_vs_default"]})
    family_effects = {}
    for fam in family_names:
        values = [
            r["family_effect_vs_default"][fam] for r in rows if fam in r["family_effect_vs_default"]
        ]
        family_effects[fam] = _effect_stats(values)

    established = [r for r in rows if r["adaptation_reference_established"]]
    adaptation: dict[str, Any] = {
        "seeds_with_reference": len(established),
        "seeds_total": len(rows),
        "reference_gaps": [r["adaptation_reference_gap"] for r in rows],
    }
    if established:
        accels = [
            r["adaptation_generations_default"] - r["adaptation_generations_food"]
            for r in established
        ]
        adaptation["acceleration_generations"] = {
            "values": accels,
            "mean": statistics.fmean(accels),
            "median": statistics.median(accels),
            "fraction_positive": sum(1 for a in accels if a > 0) / len(accels),
        }
    else:
        adaptation["acceleration_generations"] = None

    # Aggregate evolved genomes
    food_genomes = []
    ball_genomes = []
    for r in rows:
        if r.get("food_trained_genomes"):
            food_genomes.extend(r["food_trained_genomes"])
        if r.get("ball_trained_genomes"):
            ball_genomes.extend(r["ball_trained_genomes"])

    param_keys = [
        "memory_duration",
        "confidence_decay",
        "switch_threshold",
        "commitment_strength",
        "motion_extrapolation_duration",
        "mutation_rate",
        "mutation_strength",
    ]
    founder_defaults = {
        "memory_duration": 90.0,
        "confidence_decay": 0.02,
        "switch_threshold": 1.4,
        "commitment_strength": 0.5,
        "motion_extrapolation_duration": 30.0,
        "mutation_rate": 1.0,
        "mutation_strength": 1.0,
    }

    evolved_params = {}
    for key in param_keys:
        food_vals = [g[key] for g in food_genomes if key in g]
        ball_vals = [g[key] for g in ball_genomes if key in g]

        evolved_params[key] = {
            "founder": founder_defaults[key],
            "food_mean": statistics.fmean(food_vals) if food_vals else founder_defaults[key],
            "food_stdev": statistics.stdev(food_vals) if len(food_vals) > 1 else 0.0,
            "ball_mean": statistics.fmean(ball_vals) if ball_vals else founder_defaults[key],
            "ball_stdev": statistics.stdev(ball_vals) if len(ball_vals) > 1 else 0.0,
        }

    return {
        "effects": effects,
        "family_effects": family_effects,
        "adaptation": adaptation,
        "evolved_params": evolved_params,
        "overall_verdict": effects["transfer_vs_disjoint"]["verdict"],
    }


def build_report(
    rows: list[dict[str, Any]],
    config: TransferStudyConfig,
) -> dict[str, Any]:
    """Assemble the full study report (deterministic for fixed rows/config)."""
    rows = sorted(rows, key=lambda r: r["seed"])
    return {
        "study": {
            "name": "target_memory_transfer_multi_run",
            "scenario_set_version": SCENARIO_SET_VERSION,
            "config": asdict(config),
            "seeds": [r["seed"] for r in rows],
            "primary_effect": "transfer_vs_disjoint",
            "decision_rule": (
                "verdict is positive/negative only when the 95% bootstrap CI "
                "of the mean effect excludes zero; otherwise inconclusive"
            ),
        },
        "aggregate": aggregate_rows(rows),
        "per_seed": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Human-readable summary of a study report."""
    study = report["study"]
    agg = report["aggregate"]
    cfg = study["config"]

    def fmt_effect(name: str, e: dict[str, Any]) -> str:
        return (
            f"| {name} | {e['mean']:+.4f} | {e['median']:+.4f} | "
            f"[{e['ci95_low']:+.4f}, {e['ci95_high']:+.4f}] | "
            f"{e['fraction_positive']:.0%} | {e['verdict']} |"
        )

    lines = [
        "# Target Memory Transfer - Multi-Run Study Report",
        "",
        f"Scenario sets: `{study['scenario_set_version']}` | "
        f"budget: {cfg['population_size']} individuals x {cfg['generations']} generations "
        f"x {cfg['evolution_runs']} runs | seeds: {study['seeds']}",
        "",
        f"**Overall verdict ({study['primary_effect']}): " f"{agg['overall_verdict'].upper()}**",
        "",
        f"_{study['decision_rule']}_",
        "",
        "## Effects (zero-shot, held-out ball set)",
        "",
        "| effect | mean | median | 95% CI | seeds positive | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for name, e in agg["effects"].items():
        lines.append(fmt_effect(name, e))

    # Add the Validity Ladder
    lines += [
        "",
        "## Validity Ladder",
        "",
        "| step | metric | mean | median | 95% CI | seeds positive | verdict |",
        "|---|---|---|---|---|---|---|",
        fmt_effect(
            "1. memory mechanism gain (default - naive on ball)",
            agg["effects"]["memory_mechanism_gain"],
        ),
        fmt_effect(
            "2. source learning (food_trained - default on food val)",
            agg["effects"]["source_learning"],
        ),
        fmt_effect(
            "3. target learnability (ball_trained - default on ball)",
            agg["effects"]["target_learnability"],
        ),
        fmt_effect(
            "4. zero-shot transfer (food_trained - default on ball)",
            agg["effects"]["transfer_vs_disjoint"],
        ),
        fmt_effect(
            "5. selection-specific transfer (food_trained - neutral)",
            agg["effects"]["transfer_vs_neutral"],
        ),
    ]

    # Add Evolved Genomes table
    lines += [
        "",
        "## Evolved Genomes (Parameter Drift)",
        "",
        "| Parameter | Founder | Food-Trained (Mean ± SD) | Ball-Trained (Mean ± SD) |",
        "|---|---|---|---|",
    ]
    for key, p in agg["evolved_params"].items():
        lines.append(
            f"| {key} | {p['founder']:.4f} | {p['food_mean']:.4f} ± {p['food_stdev']:.4f} | "
            f"{p['ball_mean']:.4f} ± {p['ball_stdev']:.4f} |"
        )

    lines += [
        "",
        "## Per-family effects (food_trained - default)",
        "",
        "| ball family | mean | median | 95% CI | seeds positive | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for fam, e in agg["family_effects"].items():
        lines.append(fmt_effect(fam, e))

    adaptation = agg["adaptation"]
    lines += [
        "",
        "## Adaptation",
        "",
        f"Reference established on {adaptation['seeds_with_reference']} of "
        f"{adaptation['seeds_total']} seeds.",
    ]
    accel = adaptation["acceleration_generations"]
    if accel is not None:
        lines.append(
            f"Where established, adaptation acceleration (default - food, generations): "
            f"mean {accel['mean']:+.1f}, median {accel['median']:+.1f}, "
            f"{accel['fraction_positive']:.0%} of established seeds positive."
        )
    else:
        lines.append(
            "No seed established a reference bar, so adaptation speed is not "
            "measurable at this budget."
        )
    lines.append("")
    return "\n".join(lines)
