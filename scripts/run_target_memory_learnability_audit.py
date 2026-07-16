"""Target Memory Learnability Audit v1.

Characterizes the fitness landscape of TargetMemoryParams to answer:
1. Which parameters have real selective pressure (gradient)?
2. Which are genetic noise (flat landscape)?
3. Does evolution on individual parameters outperform whole-genome evolution?
4. Does train-vs-validation agreement hold?

Outputs a JSON report and a Markdown summary.

Usage:
    python scripts/run_target_memory_learnability_audit.py [--output PATH] [--seed SEED] [-j WORKERS]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path for direct invocation
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.behavior.target_memory import TargetMemoryParams, _PARAM_BOUNDS
from core.behavior.target_memory_transfer_gym import (
    evaluate_params_on_set,
    generate_scenario_set,
)
from core.behavior.target_memory_transfer_evolution import (
    TargetMemoryGenome,
    run_evolution,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PARAM_NAMES = list(_PARAM_BOUNDS.keys())
SWEEP_STEPS = 21  # number of points per 1-D sweep
ABLATION_POP_SIZE = 32
ABLATION_GENERATIONS = 30
ABLATION_RUNS = 3  # independent evolution runs per ablation
FOOD_TRAIN_COUNT = 16
FOOD_VAL_COUNT = 8
BALL_TRAIN_COUNT = 16
BALL_VAL_COUNT = 8


# ---------------------------------------------------------------------------
# 1. One-dimensional parameter sweeps
# ---------------------------------------------------------------------------
@dataclass
class SweepPoint:
    value: float
    train_score: float
    val_score: float


@dataclass
class ParamSweepResult:
    param_name: str
    default_value: float
    lo: float
    hi: float
    points: list[SweepPoint]
    best_value: float
    best_train_score: float
    best_val_score: float
    default_train_score: float
    default_val_score: float
    improvement_over_default: float
    mutations_producing_change_pct: float
    train_val_correlation: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "param_name": self.param_name,
            "default_value": self.default_value,
            "lo": self.lo,
            "hi": self.hi,
            "points": [
                {"value": p.value, "train": p.train_score, "val": p.val_score} for p in self.points
            ],
            "best_value": self.best_value,
            "best_train_score": self.best_train_score,
            "best_val_score": self.best_val_score,
            "default_train_score": self.default_train_score,
            "default_val_score": self.default_val_score,
            "improvement_over_default": self.improvement_over_default,
            "mutations_producing_change_pct": self.mutations_producing_change_pct,
            "train_val_correlation": self.train_val_correlation,
        }


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


def run_1d_sweep(
    param_name: str,
    train_scenarios: list,
    val_scenarios: list,
) -> ParamSweepResult:
    lo, hi = _PARAM_BOUNDS[param_name]
    default_val = getattr(TargetMemoryParams(), param_name)

    points: list[SweepPoint] = []
    for i in range(SWEEP_STEPS):
        value = lo + (hi - lo) * i / (SWEEP_STEPS - 1)
        params = _make_params_with(**{param_name: value})
        train_score = evaluate_params_on_set(params, train_scenarios).overall_score
        val_score = evaluate_params_on_set(params, val_scenarios).overall_score
        points.append(SweepPoint(value=value, train_score=train_score, val_score=val_score))

    # Default score
    default_params = TargetMemoryParams()
    default_train = evaluate_params_on_set(default_params, train_scenarios).overall_score
    default_val = evaluate_params_on_set(default_params, val_scenarios).overall_score

    # Best by validation
    best_pt = max(points, key=lambda p: p.val_score)

    # What fraction of mutations from the default produce a measurable change?
    # "Measurable" = score differs from default by > 0.001
    threshold = 0.001
    changes = sum(1 for p in points if abs(p.val_score - default_val) > threshold)
    change_pct = 100.0 * changes / len(points)

    # Train-val correlation (Pearson)
    train_scores = [p.train_score for p in points]
    val_scores = [p.val_score for p in points]
    corr = _pearson(train_scores, val_scores)

    return ParamSweepResult(
        param_name=param_name,
        default_value=getattr(TargetMemoryParams(), param_name),
        lo=lo,
        hi=hi,
        points=points,
        best_value=best_pt.value,
        best_train_score=best_pt.train_score,
        best_val_score=best_pt.val_score,
        default_train_score=default_train,
        default_val_score=default_val,
        improvement_over_default=best_pt.val_score - default_val,
        mutations_producing_change_pct=change_pct,
        train_val_correlation=corr,
    )


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx * sy < 1e-12:
        return 0.0
    return cov / (sx * sy)


# ---------------------------------------------------------------------------
# 2. Evolutionary ablations: evolve one param at a time vs all
# ---------------------------------------------------------------------------
@dataclass
class AblationResult:
    label: str  # param name or "all"
    evolved_params: list[str]
    frozen_params: list[str]
    mean_train_score: float
    mean_val_score: float
    improvement_over_default_val: float
    runs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "evolved_params": self.evolved_params,
            "frozen_params": self.frozen_params,
            "mean_train_score": self.mean_train_score,
            "mean_val_score": self.mean_val_score,
            "improvement_over_default_val": self.improvement_over_default_val,
            "runs": self.runs,
        }


class _RestrictedParams(TargetMemoryParams):
    """TargetMemoryParams that only mutates a subset of genes."""

    _mutable_keys: frozenset[str] = frozenset()

    def crossed_over(
        self,
        other: TargetMemoryParams,
        *,
        weight1: float,
        mutation_rate: float,
        mutation_strength: float,
        rng: random.Random,
    ) -> TargetMemoryParams:
        """Blend all, but only mutate the mutable subset."""
        self_values = self.to_dict()
        other_values = other.to_dict()
        blended: dict[str, float] = {}
        for key, (lo, hi) in _PARAM_BOUNDS.items():
            value = self_values[key] * weight1 + other_values[key] * (1.0 - weight1)
            if key in self._mutable_keys and rng.random() < mutation_rate:
                span = hi - lo
                value += rng.gauss(0.0, mutation_strength * span)
            blended[key] = max(lo, min(hi, value))
        return _make_restricted(self._mutable_keys, **blended)


def _make_restricted(mutable_keys: frozenset[str], **kwargs: float) -> _RestrictedParams:
    obj = _RestrictedParams(**kwargs)
    object.__setattr__(obj, "_mutable_keys", mutable_keys)
    return obj


class _RestrictedGenome(TargetMemoryGenome):
    """TargetMemoryGenome wrapping a _RestrictedParams."""

    pass


def run_ablation(
    label: str,
    mutable_params: list[str],
    seed: int,
    train_scenarios: list,
    val_scenarios: list,
) -> AblationResult:
    """Evolve only `mutable_params`, freezing the rest at their defaults."""
    mutable = frozenset(mutable_params)
    frozen = [p for p in PARAM_NAMES if p not in mutable]
    default_val_score = evaluate_params_on_set(TargetMemoryParams(), val_scenarios).overall_score

    run_results = []
    for run_idx in range(ABLATION_RUNS):
        run_rng = random.Random(seed + 20000 + run_idx * 100)

        if label == "all":
            initial_genome = TargetMemoryGenome(params=TargetMemoryParams())
        else:
            initial_params = _make_restricted(mutable)
            initial_genome = TargetMemoryGenome(params=initial_params)

        best_genome, history, _ = run_evolution(
            [initial_genome],
            train_scenarios,
            ABLATION_GENERATIONS,
            ABLATION_POP_SIZE,
            run_rng,
            validation_scenarios=val_scenarios,
        )

        train_score = evaluate_params_on_set(best_genome.params, train_scenarios).overall_score
        val_score = evaluate_params_on_set(best_genome.params, val_scenarios).overall_score

        run_results.append(
            {
                "run": run_idx,
                "train_score": round(train_score, 6),
                "val_score": round(val_score, 6),
                "evolved_params": best_genome.params.to_dict(),
                "history": [round(h, 6) for h in history],
            }
        )

    mean_train = statistics.mean(r["train_score"] for r in run_results)
    mean_val = statistics.mean(r["val_score"] for r in run_results)

    return AblationResult(
        label=label,
        evolved_params=mutable_params,
        frozen_params=frozen,
        mean_train_score=mean_train,
        mean_val_score=mean_val,
        improvement_over_default_val=mean_val - default_val_score,
        runs=run_results,
    )


# ---------------------------------------------------------------------------
# 3. Orchestration
# ---------------------------------------------------------------------------
def _run_sweep_worker(args: tuple) -> ParamSweepResult:
    param_name, seed, domain = args
    if domain == "food":
        train = generate_scenario_set("train", seed, count=FOOD_TRAIN_COUNT)
        val = generate_scenario_set("validation", seed, count=FOOD_VAL_COUNT)
    else:
        train = generate_scenario_set("ball_train", seed, count=BALL_TRAIN_COUNT)
        val = generate_scenario_set("ball_validation", seed, count=BALL_VAL_COUNT)
    return run_1d_sweep(param_name, train, val)


def _run_ablation_worker(args: tuple) -> AblationResult:
    label, mutable_params, seed, domain = args
    if domain == "food":
        train = generate_scenario_set("train", seed, count=FOOD_TRAIN_COUNT)
        val = generate_scenario_set("validation", seed, count=FOOD_VAL_COUNT)
    else:
        train = generate_scenario_set("ball_train", seed, count=BALL_TRAIN_COUNT)
        val = generate_scenario_set("ball_validation", seed, count=BALL_VAL_COUNT)
    return run_ablation(label, mutable_params, seed, train, val)


def run_learnability_audit(
    seed: int = 42,
    max_workers: int = 1,
) -> dict[str, Any]:
    """Run the complete learnability audit for a given seed."""
    t0 = time.perf_counter()

    # Phase 1: 1-D sweeps (both domains)
    sweep_tasks = []
    for domain in ("food", "ball"):
        for param_name in PARAM_NAMES:
            sweep_tasks.append((param_name, seed, domain))

    sweep_results: dict[str, dict[str, Any]] = {"food": {}, "ball": {}}

    if max_workers > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_sweep_worker, t): t for t in sweep_tasks}
            for future in as_completed(futures):
                task = futures[future]
                result = future.result()
                domain = task[2]
                sweep_results[domain][result.param_name] = result.to_dict()
                print(
                    f"  sweep {domain}/{result.param_name}: "
                    f"best_improvement={result.improvement_over_default:+.4f}, "
                    f"gradient_pct={result.mutations_producing_change_pct:.0f}%"
                )
    else:
        for task in sweep_tasks:
            result = _run_sweep_worker(task)
            domain = task[2]
            sweep_results[domain][result.param_name] = result.to_dict()
            print(
                f"  sweep {domain}/{result.param_name}: "
                f"best_improvement={result.improvement_over_default:+.4f}, "
                f"gradient_pct={result.mutations_producing_change_pct:.0f}%"
            )

    # Phase 2: Evolutionary ablations (both domains)
    ablation_tasks = []
    for domain in ("food", "ball"):
        # Single-param ablations
        for param_name in PARAM_NAMES:
            ablation_tasks.append((param_name, [param_name], seed, domain))
        # All-params ablation
        ablation_tasks.append(("all", list(PARAM_NAMES), seed, domain))

    ablation_results: dict[str, dict[str, Any]] = {"food": {}, "ball": {}}

    if max_workers > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_ablation_worker, t): t for t in ablation_tasks}
            for future in as_completed(futures):
                task = futures[future]
                result = future.result()
                domain = task[3]
                ablation_results[domain][result.label] = result.to_dict()
                print(
                    f"  ablation {domain}/{result.label}: "
                    f"improvement={result.improvement_over_default_val:+.4f}"
                )
    else:
        for task in ablation_tasks:
            result = _run_ablation_worker(task)
            domain = task[3]
            ablation_results[domain][result.label] = result.to_dict()
            print(
                f"  ablation {domain}/{result.label}: "
                f"improvement={result.improvement_over_default_val:+.4f}"
            )

    elapsed = time.perf_counter() - t0

    report = {
        "audit_version": "v1",
        "seed": seed,
        "config": {
            "sweep_steps": SWEEP_STEPS,
            "ablation_pop_size": ABLATION_POP_SIZE,
            "ablation_generations": ABLATION_GENERATIONS,
            "ablation_runs": ABLATION_RUNS,
        },
        "sweeps": sweep_results,
        "ablations": ablation_results,
        "elapsed_seconds": round(elapsed, 1),
    }
    return report


# ---------------------------------------------------------------------------
# 4. Markdown renderer
# ---------------------------------------------------------------------------
def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Target Memory Learnability Audit",
        "",
        f"Seed: `{report['seed']}` | "
        f"Sweep: {report['config']['sweep_steps']} points | "
        f"Ablation: {report['config']['ablation_pop_size']} pop × "
        f"{report['config']['ablation_generations']} gen × "
        f"{report['config']['ablation_runs']} runs | "
        f"Elapsed: {report['elapsed_seconds']}s",
        "",
    ]

    for domain in ("food", "ball"):
        lines.append(f"## {domain.title()} Domain")
        lines.append("")

        # Sweep table
        lines.append("### Parameter Sensitivity (1-D Sweeps)")
        lines.append("")
        lines.append(
            "| Parameter | Default | Best | Improvement | " "Gradient % | Train-Val Corr |"
        )
        lines.append("|---|---|---|---|---|---|")

        sweeps = report["sweeps"][domain]
        for param_name in PARAM_NAMES:
            if param_name not in sweeps:
                continue
            s = sweeps[param_name]
            lines.append(
                f"| {param_name} | {s['default_value']:.4f} | "
                f"{s['best_value']:.4f} | "
                f"{s['improvement_over_default']:+.4f} | "
                f"{s['mutations_producing_change_pct']:.0f}% | "
                f"{s['train_val_correlation']:.3f} |"
            )
        lines.append("")

        # Ablation table
        lines.append("### Evolutionary Ablations (evolve single param vs all)")
        lines.append("")
        lines.append("| Evolved | Train Score | Val Score | " "Improvement vs Default |")
        lines.append("|---|---|---|---|")

        ablations = report["ablations"][domain]
        # Single params first, then "all"
        for param_name in PARAM_NAMES:
            if param_name not in ablations:
                continue
            a = ablations[param_name]
            lines.append(
                f"| {param_name} | {a['mean_train_score']:.4f} | "
                f"{a['mean_val_score']:.4f} | "
                f"{a['improvement_over_default_val']:+.4f} |"
            )
        if "all" in ablations:
            a = ablations["all"]
            lines.append(
                f"| **all** | **{a['mean_train_score']:.4f}** | "
                f"**{a['mean_val_score']:.4f}** | "
                f"**{a['improvement_over_default_val']:+.4f}** |"
            )
        lines.append("")

    # Diagnosis
    lines.append("## Diagnosis")
    lines.append("")

    for domain in ("food", "ball"):
        sweeps = report["sweeps"].get(domain, {})
        ablations = report["ablations"].get(domain, {})

        # Rank parameters by improvement
        ranked = sorted(
            [(p, sweeps[p]["improvement_over_default"]) for p in PARAM_NAMES if p in sweeps],
            key=lambda x: -x[1],
        )
        evolvable = [(p, imp) for p, imp in ranked if imp > 0.002]
        noise = [(p, imp) for p, imp in ranked if imp <= 0.002]

        lines.append(f"### {domain.title()} Domain")
        lines.append("")
        if evolvable:
            lines.append("**Evolvable parameters** (improvement > 0.002):")
            for p, imp in evolvable:
                lines.append(f"- `{p}`: best improvement {imp:+.4f}")
        else:
            lines.append("**No parameters show meaningful improvement > 0.002.**")
        lines.append("")
        if noise:
            lines.append("**Genetic noise** (flat landscape, improvement <= 0.002):")
            for p, imp in noise:
                lines.append(f"- `{p}`: {imp:+.4f}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Target Memory Learnability Audit")
    parser.add_argument(
        "--output", default="research/target_memory_transfer/learnability_audit_v1.json"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("-j", "--workers", type=int, default=1)
    args = parser.parse_args()

    print(f"Running learnability audit with seed={args.seed}, workers={args.workers}")
    report = run_learnability_audit(seed=args.seed, max_workers=args.workers)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}")

    md_path = out_path.with_suffix(".md")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Summary: {md_path}")
    print()
    print(render_markdown(report))


if __name__ == "__main__":
    main()
