"""Formatting and recommendations display functions for evolution health report.

This file holds recommendations mapping and human-readable string formatting.
"""

from typing import Any

from tools.evolution_report_analyzer import (
    GEN_RATE_HEALTHY_PER_10K,
    STARVATION_STRAINED,
)


def recommend(
    assessment: dict[str, Any], hist: dict[str, Any], inst: dict[str, Any]
) -> list[dict[str, Any]]:
    """Map findings to ranked, knob-specific actions referencing real files."""
    axes = assessment["axes"]
    recs: list[dict[str, Any]] = []

    def add(priority: str, finding: str, action: str, validate: str) -> None:
        recs.append(
            {"priority": priority, "finding": finding, "action": action, "validate": validate}
        )

    if axes.get("population") == "extinct":
        add(
            "high",
            "The population went extinct.",
            "Check the energy economy and emergency-spawn floor in "
            "core/reproduction_service.py and core/config/fish.py; confirm food supply "
            "(core/config/food.py, main.py --auto-food-spawn-rate).",
            "python scripts/analyze_population.py",
        )

    if axes.get("foraging") in {"broken", "strained"}:
        add(
            "high" if axes["foraging"] == "broken" else "medium",
            "Most deaths are starvation; fish are not foraging effectively.",
            "First rule out ball pursuit pre-empting food seeking (core/movement_strategy.py: "
            "ball priority 2 runs before composable food pursuit priority 4, and the ball exists "
            "even when soccer is off). Then review food detection/spawn in core/config/food.py and "
            "the food-seeking sub-behavior in core/algorithms/composable/actions.py.",
            "python scripts/diagnose_food_seeking.py",
        )

    if axes.get("turnover") in {"stalled", "slow"}:
        add(
            "high" if axes["turnover"] == "stalled" else "medium",
            "Generation turnover is below the healthy >5 per 10k frames.",
            "Reproduction is funded by energy banked ABOVE max_energy, so energy sinks (ball play, "
            "poker) suppress births. Audit max_energy and reproduction thresholds in "
            "core/config/fish.py and the spend logic in core/reproduction_service.py.",
            "python scripts/analyze_energy.py",
        )

    if axes.get("selection") == "drift_only":
        add(
            "medium",
            "Generations turn over but mean traits are not under directional selection.",
            "Confirm it is genuine (not single-window noise) over a longer horizon, then if traits "
            "are truly flat, selection pressure is too weak: review mutation bounds in "
            "core/algorithms/composable/definitions.py and whether fitness meaningfully "
            "differentiates the tracked traits.",
            "python scripts/diagnose_evolution.py --frames 20000 --seed 42",
        )

    if axes.get("diversity") == "converging":
        add(
            "medium",
            "Genetic diversity is low and falling.",
            "Review mutation rate/strength and HGT probability bounds "
            "(core/algorithms/composable/definitions.py, core/genetics/) and mate preferences; "
            "premature convergence freezes evolution.",
            "python main.py --headless --max-frames 30000 --export-stats results.json --seed 42",
        )

    if axes.get("population") == "unstable":
        add(
            "medium",
            "Population swings between boom and bust.",
            "Smooth the energy economy and emergency-spawn behaviour "
            "(core/reproduction_service.py, core/config/fish.py); large swings perturb the "
            "single-seed trajectory and the ecosystem_health benchmark.",
            "python scripts/analyze_population.py",
        )

    if not hist.get("sufficient"):
        add(
            "low",
            f"Only {hist.get('n_samples', 0)} history sample(s); trends are not yet reliable.",
            "Let the simulation run longer, or stream a journal so the multi-day trend survives "
            "the in-memory buffer wrap: "
            "python tools/evolution_report.py --watch --interval 300 --journal evolution_journal.jsonl",
            "re-run this report once more samples have accrued",
        )

    if not recs:
        add(
            "low",
            "No problems detected on the measured axes.",
            "Evolution looks healthy. To push further, raise selection pressure or enrich the "
            "niche and compare on the ecosystem_health benchmark.",
            "python tools/run_bench.py benchmarks/tank/ecosystem_health_10k.py --seed 42",
        )

    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order.get(r["priority"], 3))
    return recs


def format_human(report: dict[str, Any]) -> str:
    lines: list[str] = []
    hist = report["history"]
    inst = report["current"]
    lines.append("=" * 78)
    lines.append("TANK WORLD - EVOLUTION HEALTH REPORT")
    lines.append("=" * 78)
    lines.append(f"source : {report['source']}")
    lines.append(f"verdict: {report['verdict'].upper()}")
    if hist.get("frame_last") is not None:
        lines.append(
            f"window : frame {hist.get('frame_first')} -> {hist.get('frame_last')} "
            f"({hist.get('n_samples')} samples)"
        )

    lines.append("")
    lines.append("AXES")
    lines.append("-" * 78)
    if report["axes"]:
        for axis, grade in report["axes"].items():
            lines.append(f"  {axis:>12}: {grade}")
    else:
        lines.append("  (not enough data to grade any axis)")

    lines.append("")
    lines.append("KEY METRICS")
    lines.append("-" * 78)
    gen_rate = hist.get("generation_rate_per_10k")
    lines.append(f"  max generation        : {inst.get('max_generation', '?')}")
    lines.append(
        f"  generation rate /10k  : {gen_rate if gen_rate is not None else '?'} "
        f"(healthy > {GEN_RATE_HEALTHY_PER_10K})"
    )
    lines.append(
        f"  population            : "
        f"{inst.get('population', hist.get('population_last', '?'))} "
        f"(mean {hist.get('population_mean', '?')}, CV {hist.get('population_cv', '?')})"
    )
    starv = inst.get("starvation_fraction")
    lines.append(
        f"  starvation fraction   : {round(starv, 3) if isinstance(starv, float) else '?'} "
        f"(healthy < {STARVATION_STRAINED})"
    )
    lines.append(
        f"  diversity score       : {inst.get('diversity_score', hist.get('diversity_last', '?'))} "
        f"(unique algorithms {inst.get('unique_algorithms', '?')})"
    )

    drift = hist.get("trait_drift") or {}
    lines.append("")
    lines.append("TRAIT DRIFT (population mean, first -> last)")
    lines.append("-" * 78)
    if drift:
        for trait, d in drift.items():
            mark = "  <- selection" if d["selection"] else ""
            lines.append(
                f"  {trait:>18}: {d['start']:8.4f} -> {d['end']:8.4f} "
                f"({d['delta']:+.4f}, {d['pct']:+6.1f}%){mark}"
            )
    else:
        lines.append("  (no trait-mean history available - need >=2 samples with traits)")

    sq = hist.get("selection_quality") or {}
    if sq:
        lines.append("")
        lines.append("SELECTION QUALITY (Proposal #27 bottleneck-conditioned ruler)")
        lines.append("-" * 78)
        conf = sq.get("confidence", "?")
        epoch_mixed = sq.get("epoch_mixed", False)
        boot_ids = sq.get("boot_ids_in_window", [])
        stable_n = sq.get("stable_sample_count", "?")
        lines.append(f"  confidence            : {conf}")
        lines.append(
            f"  epoch mixed           : {epoch_mixed}"
            + (f" (boot_ids={boot_ids})" if boot_ids else " (no boot_id tags in samples)")
        )
        lines.append(f"  stable samples used   : {stable_n}")
        rn = sq.get("range_normalized_drift") or {}
        if rn:
            lines.append(
                "  range-norm |drift|    : "
                + ", ".join(f"{k}={v:.3f}" for k, v in sorted(rn.items()))
            )
        cond = sq.get("conditioned_drift") or {}
        if cond:
            lines.append("  conditioned drift (pop-filtered):")
            for trait, d in cond.items():
                mark = "  <- selection" if d["selection"] else ""
                lines.append(
                    f"    {trait:>18}: {d['start']:8.4f} -> {d['end']:8.4f} "
                    f"({d['delta']:+.4f}, {d['pct']:+6.1f}%){mark}"
                )
        elif sq.get("stable_sample_count", 0) < 3:
            lines.append("  conditioned drift     : (insufficient stable samples)")

    lines.append("")
    lines.append("FINDINGS")
    lines.append("-" * 78)
    if report["findings"]:
        for f in report["findings"]:
            lines.append(f"  - {f}")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("RECOMMENDATIONS (ranked)")
    lines.append("-" * 78)
    for i, rec in enumerate(report["recommendations"], 1):
        lines.append(f"  {i}. [{rec['priority'].upper()}] {rec['finding']}")
        lines.append(f"     action  : {rec['action']}")
        lines.append(f"     validate: {rec['validate']}")
    lines.append("=" * 78)
    return "\n".join(lines)
