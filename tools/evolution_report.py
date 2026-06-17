#!/usr/bin/env python3
"""Evolution health report for a long-running Tank World simulation.

This is the tool an AI agent (or a human) runs to answer two questions about a
*running* simulation: "how well are the fish evolving?" and "what should we
change to improve it?". It is deliberately read-only and side-effect free with
respect to the simulation - it observes, scores, and recommends; it never edits
the world or the code.

It turns the scattered raw telemetry (the live metrics-history endpoint, a world
snapshot, an exported stats JSON, or a fresh probe run) into a single structured
report with:

  * health indicators across several axes (turnover, selection, foraging,
    diversity, population stability), graded against the thresholds documented
    in CLAUDE.md ("Healthy Ecosystem Indicators");
  * a trait-drift table (first -> last population mean) that distinguishes real
    directional selection from mere generational churn; and
  * ranked, knob-specific recommendations that point at the actual files and
    diagnostics to act on.

Data sources (pick one):

    # Attach to a running web-server simulation (the common case for long runs)
    python tools/evolution_report.py --url http://127.0.0.1:8000

    # Analyse an exported stats JSON (from main.py --export-stats)
    python tools/evolution_report.py --stats results.json

    # Analyse a metrics-history payload or a watch-journal (JSONL)
    python tools/evolution_report.py --history evolution_journal.jsonl

    # No server? Run a fresh, deterministic probe and report on it
    python tools/evolution_report.py --probe --frames 20000 --seed 42

    # Long runs: stream samples to an append-only journal so the multi-day
    # trend survives the in-memory history buffer wrapping (~1M frames).
    python tools/evolution_report.py --watch --interval 300 --journal evolution_journal.jsonl

Add --json (or --out FILE) to emit the structured report for an agent to parse.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# Thresholds (kept in sync with the "Healthy Ecosystem Indicators" table and the
# "Common Gotchas" notes in CLAUDE.md). Centralised so the verdict logic and the
# recommendations agree on what "healthy" means.
# ---------------------------------------------------------------------------
TRAIT_DRIFT_SELECTION_PCT = 5.0  # |rel change| >= this => directional selection
GEN_RATE_HEALTHY_PER_10K = 5.0  # generations per 10k frames
GEN_RATE_SLOW_PER_10K = 3.0
STARVATION_STRAINED = 0.80  # fraction of deaths that are starvation
STARVATION_BROKEN = 0.95
POP_STABLE_MIN = 20.0  # stable population floor (fish)
POP_CV_UNSTABLE = 0.35  # coefficient of variation above this => boom/bust
DIVERSITY_LOW = 0.30  # diversity_score below this => converging
MIN_SAMPLES_FOR_TREND = 3


# ---------------------------------------------------------------------------
# Field extraction (tolerant: the snapshot stats, the export JSON, and the
# probe metrics differ in shape and naming, so we try several known locations).
# ---------------------------------------------------------------------------
def _first_present(obj: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return None


def _unwrap_snapshot(obj: dict[str, Any]) -> dict[str, Any]:
    """Unwrap the snapshot API envelope if present.

    The live snapshot endpoint returns ``{"type": "update", "snapshot": {...}}``
    where the inner dict contains ``stats``, ``metrics_history``, ``entities``,
    etc.  Other data sources (exported stats, metrics-history payload) do not
    have this wrapper.  This helper transparently peels it so the extract
    helpers always see the inner dict.
    """
    inner = obj.get("snapshot")
    if isinstance(inner, dict) and (
        "stats" in inner or "metrics_history" in inner or "entities" in inner
    ):
        return inner
    return obj


def extract_history_samples(payload: Any) -> list[dict[str, Any]]:
    """Pull the ordered list of metric samples out of any supported container."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [s for s in payload if isinstance(s, dict)]
    if isinstance(payload, dict):
        # Unwrap the snapshot API envelope if present.
        payload = _unwrap_snapshot(payload)
        # Metrics-history payload, or a full snapshot embedding one.
        if isinstance(payload.get("samples"), list):
            return [s for s in payload["samples"] if isinstance(s, dict)]
        mh = payload.get("metrics_history")
        if isinstance(mh, dict) and isinstance(mh.get("samples"), list):
            return [s for s in mh["samples"] if isinstance(s, dict)]
    return []


def extract_stats(obj: Any) -> dict[str, Any]:
    """Pull the instantaneous stats block out of any supported container."""
    if not isinstance(obj, dict):
        return {}
    # Unwrap the snapshot API envelope if present.
    obj = _unwrap_snapshot(obj)
    # A full snapshot nests the curated stats under "stats".
    if isinstance(obj.get("stats"), dict):
        return obj["stats"]
    # An exported get_current_metrics() dict is already the stats block.
    return obj


def _diversity_block(stats: dict[str, Any]) -> dict[str, Any]:
    block = stats.get("diversity_stats")
    return block if isinstance(block, dict) else {}


def starvation_fraction(stats: dict[str, Any]) -> float | None:
    """Fraction of deaths attributable to starvation, or None if unknown."""
    rate = _first_present(stats, "starvation_rate")
    if isinstance(rate, (int, float)):
        return float(rate)
    causes = stats.get("death_causes")
    if isinstance(causes, dict) and causes:
        total = sum(v for v in causes.values() if isinstance(v, (int, float)))
        starved = causes.get("starvation", 0) or causes.get("starved", 0)
        if total > 0 and isinstance(starved, (int, float)):
            return float(starved) / float(total)
    return None


def population_value(stats: dict[str, Any]) -> float | None:
    val = _first_present(
        stats,
        "fish_count",
        "final_fish_count",
        "population",
        "mean_population",
        "avg_pop",
        "final_population",
    )
    return float(val) if isinstance(val, (int, float)) else None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def _coefficient_of_variation(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    if mean == 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / n
    return (var**0.5) / abs(mean)


def analyze_history(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Time-series signals: trait drift, turnover, diversity trend, stability."""
    result: dict[str, Any] = {
        "n_samples": len(samples),
        "sufficient": len(samples) >= MIN_SAMPLES_FOR_TREND,
    }
    if not samples:
        return result

    first, last = samples[0], samples[-1]
    result["frame_first"] = first.get("frame")
    result["frame_last"] = last.get("frame")
    result["frames_covered"] = (last.get("frame", 0) or 0) - (first.get("frame", 0) or 0)

    # Generation turnover.
    gen_first = first.get("max_generation", 0) or 0
    gen_last = last.get("max_generation", 0) or 0
    result["generation_first"] = gen_first
    result["generation_last"] = gen_last
    result["generations_advanced"] = gen_last - gen_first
    frames = result["frames_covered"] or 0
    result["generation_rate_per_10k"] = (
        round((gen_last - gen_first) / (frames / 10000.0), 3) if frames > 0 else None
    )

    # Population stability across the window.
    pops = [
        float(s["population"]) for s in samples if isinstance(s.get("population"), (int, float))
    ]
    if pops:
        result["population_mean"] = round(sum(pops) / len(pops), 2)
        result["population_min"] = min(pops)
        result["population_max"] = max(pops)
        result["population_cv"] = round(_coefficient_of_variation(pops), 3)
        result["population_last"] = pops[-1]

    # Diversity trend.
    div = [
        float(s["diversity_score"])
        for s in samples
        if isinstance(s.get("diversity_score"), (int, float))
    ]
    if div:
        result["diversity_first"] = div[0]
        result["diversity_last"] = div[-1]
        result["diversity_delta"] = round(div[-1] - div[0], 4)

    # Birth/death deltas over the window.
    if isinstance(first.get("births_total"), (int, float)) and isinstance(
        last.get("births_total"), (int, float)
    ):
        result["births_in_window"] = last["births_total"] - first["births_total"]
    if isinstance(first.get("deaths_total"), (int, float)) and isinstance(
        last.get("deaths_total"), (int, float)
    ):
        result["deaths_in_window"] = last["deaths_total"] - first["deaths_total"]

    # Trait drift (first -> last population mean), the selection-vs-churn signal.
    result["trait_drift"] = _trait_drift(samples)
    result["selection_detected"] = any(d["selection"] for d in result["trait_drift"].values())
    return result


def _trait_drift(samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-trait first->last drift across samples that carry trait means."""
    with_traits = [s for s in samples if isinstance(s.get("traits"), dict) and s["traits"]]
    drift: dict[str, dict[str, Any]] = {}
    if len(with_traits) < 2:
        return drift
    first, last = with_traits[0], with_traits[-1]
    keys = [k for k in first["traits"] if k in last["traits"]]
    for key in keys:
        start = float(first["traits"][key])
        end = float(last["traits"][key])
        delta = end - start
        rel = (delta / start * 100.0) if start else 0.0
        drift[key] = {
            "start": round(start, 5),
            "end": round(end, 5),
            "delta": round(delta, 5),
            "pct": round(rel, 2),
            "selection": abs(rel) >= TRAIT_DRIFT_SELECTION_PCT,
        }
    return drift


def analyze_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Instantaneous signals from the current stats block."""
    result: dict[str, Any] = {}
    if not stats:
        return result
    div = _diversity_block(stats)
    result["max_generation"] = _first_present(stats, "max_generation", "current_generation")
    result["population"] = population_value(stats)
    result["starvation_fraction"] = starvation_fraction(stats)
    result["diversity_score"] = _first_present(stats, "diversity_score") or div.get(
        "diversity_score"
    )
    result["unique_algorithms"] = div.get("unique_algorithms")
    result["unique_species"] = div.get("unique_species")

    repro = stats.get("reproduction_stats")
    if isinstance(repro, dict):
        attempts = repro.get("total_mating_attempts") or 0
        offspring = repro.get("total_offspring") or 0
        result["reproduction_offspring"] = offspring
        result["reproduction_attempts"] = attempts
        if attempts:
            result["reproduction_success_pct"] = round(100.0 * offspring / attempts, 1)
    return result


def reconcile_history_with_current(hist: dict[str, Any], inst: dict[str, Any]) -> None:
    """Drop ambiguous history population stats when current stats prove a field mismatch.

    Older live history samples may store a legacy ``population`` counter that is
    not the current living fish count. When the current snapshot carries an
    explicit fish count and differs by an order of magnitude from the history
    tail, keep turnover/trait history but avoid displaying bogus population
    mean/CV.
    """
    current_pop = inst.get("population")
    history_pop = hist.get("population_last")
    if not isinstance(current_pop, (int, float)) or not isinstance(history_pop, (int, float)):
        return
    if current_pop <= 0 or history_pop <= 0:
        return
    ratio = max(current_pop, history_pop) / min(current_pop, history_pop)
    if ratio < 10.0:
        return

    hist["population_history_ambiguous"] = True
    for key in (
        "population_mean",
        "population_min",
        "population_max",
        "population_cv",
        "population_last",
    ):
        hist.pop(key, None)


# ---------------------------------------------------------------------------
# Verdict + recommendations
# ---------------------------------------------------------------------------
def assess(hist: dict[str, Any], inst: dict[str, Any]) -> dict[str, Any]:
    """Grade each axis and roll up to an overall verdict + findings."""
    axes: dict[str, str] = {}
    findings: list[str] = []

    # Population axis.
    pop = inst.get("population")
    if pop is None:
        pop = hist.get("population_last")
    pop_cv = hist.get("population_cv")
    if pop is not None and pop <= 0:
        axes["population"] = "extinct"
        findings.append("Population has collapsed to zero (extinction).")
    elif pop is not None and pop < POP_STABLE_MIN:
        axes["population"] = "fragile"
        findings.append(f"Population is low ({pop:.0f} < {POP_STABLE_MIN:.0f} stable floor).")
    elif isinstance(pop_cv, (int, float)) and pop_cv >= POP_CV_UNSTABLE:
        axes["population"] = "unstable"
        findings.append(f"Population is boom/bust (CV={pop_cv:.2f} >= {POP_CV_UNSTABLE}).")
    elif pop is not None:
        axes["population"] = "stable"

    # Turnover axis.
    rate = hist.get("generation_rate_per_10k")
    if isinstance(rate, (int, float)):
        if rate < GEN_RATE_SLOW_PER_10K:
            axes["turnover"] = "stalled"
            findings.append(
                f"Generation turnover is slow ({rate:.1f} < {GEN_RATE_SLOW_PER_10K} per 10k frames)."
            )
        elif rate < GEN_RATE_HEALTHY_PER_10K:
            axes["turnover"] = "slow"
            findings.append(f"Generation turnover is moderate ({rate:.1f} per 10k frames).")
        else:
            axes["turnover"] = "healthy"

    # Selection axis (the heart of "are they actually evolving").
    drift = hist.get("trait_drift") or {}
    if drift:
        if hist.get("selection_detected"):
            axes["selection"] = "active"
        else:
            axes["selection"] = "drift_only"
            findings.append(
                "Generational churn without directional selection: no tracked trait "
                f"drifted >= {TRAIT_DRIFT_SELECTION_PCT:.0f}% (drift-dominated or near a "
                "fitness optimum)."
            )
    elif hist.get("sufficient"):
        findings.append("No trait-mean data in history (older schema); cannot judge selection.")

    # Foraging axis.
    starv = inst.get("starvation_fraction")
    if isinstance(starv, (int, float)):
        if starv >= STARVATION_BROKEN:
            if axes.get("population") == "stable" and axes.get("turnover") == "healthy":
                axes["foraging"] = "strained"
                findings.append(
                    f"Starvation is {starv*100:.0f}% of deaths, but population and turnover "
                    "are stable: food economy is tight, not necessarily broken."
                )
            else:
                axes["foraging"] = "broken"
                findings.append(
                    f"Starvation is {starv*100:.0f}% of deaths "
                    f"(>= {STARVATION_BROKEN*100:.0f}%): food-seeking is likely broken."
                )
        elif starv >= STARVATION_STRAINED:
            axes["foraging"] = "strained"
            findings.append(f"Starvation is {starv*100:.0f}% of deaths (food economy is tight).")
        else:
            axes["foraging"] = "ok"

    # Diversity axis.
    div_score = inst.get("diversity_score")
    if div_score is None:
        div_score = hist.get("diversity_last")
    div_delta = hist.get("diversity_delta")
    uniq = inst.get("unique_algorithms")
    if isinstance(div_score, (int, float)):
        declining = isinstance(div_delta, (int, float)) and div_delta < 0
        if div_score < DIVERSITY_LOW and declining:
            axes["diversity"] = "converging"
            findings.append(
                f"Genetic diversity is low and falling (score={div_score:.2f}, "
                f"unique_algorithms={uniq}): risk of premature convergence."
            )
        else:
            axes["diversity"] = "ok"

    verdict = _roll_up(axes, hist)
    return {"verdict": verdict, "axes": axes, "findings": findings}


def _roll_up(axes: dict[str, str], hist: dict[str, Any]) -> str:
    if not hist.get("sufficient") and not axes:
        return "insufficient_data"
    if axes.get("population") == "extinct":
        return "collapsing"
    bad = {
        "fragile",
        "unstable",
        "stalled",
        "broken",
        "converging",
    }
    if any(v in bad for v in axes.values()):
        # Distinguish a foraging/population crisis from an evolution-quality stall.
        if axes.get("foraging") == "broken" or axes.get("population") in {"fragile", "unstable"}:
            return "struggling"
        return "stalled"
    if (
        axes.get("selection") == "drift_only"
        or axes.get("turnover") == "slow"
        or axes.get("foraging") == "strained"
    ):
        return "treading_water"
    if not hist.get("sufficient"):
        return "insufficient_data"
    return "healthy"


def recommend(assessment: dict[str, Any], hist: dict[str, Any], inst: dict[str, Any]) -> list[dict]:
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


def build_report(
    samples: list[dict[str, Any]], stats: dict[str, Any], source: str
) -> dict[str, Any]:
    hist = analyze_history(samples)
    inst = analyze_stats(stats)
    reconcile_history_with_current(hist, inst)
    assessment = assess(hist, inst)
    recs = recommend(assessment, hist, inst)
    return {
        "source": source,
        "verdict": assessment["verdict"],
        "axes": assessment["axes"],
        "findings": assessment["findings"],
        "history": hist,
        "current": inst,
        "recommendations": recs,
    }


# ---------------------------------------------------------------------------
# Human-readable rendering
# ---------------------------------------------------------------------------
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
    if hist.get("population_history_ambiguous"):
        lines.append("                          history population ignored: legacy field mismatch")
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


# ---------------------------------------------------------------------------
# IO: live server, files, probe, watch
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: float = 10.0) -> Any:
    # Trusted, user-supplied local/LAN URL pointing at their own simulation server.
    with urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def resolve_world_id(base_url: str, world_id: str | None) -> str:
    if world_id:
        return world_id
    data = _http_get_json(f"{base_url}/api/worlds/default/id")
    return data["world_id"]


def fetch_live(base_url: str, world_id: str | None) -> tuple[list[dict], dict, str]:
    """Fetch samples + current stats from a running server.

    Prefers the snapshot endpoint (stats + metrics_history in one call); falls
    back to the metrics-history endpoint alone.
    """
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    snapshot_stats: dict[str, Any] = {}
    try:
        snap = _http_get_json(f"{base_url}/api/worlds/{wid}/snapshot")
        samples = extract_history_samples(snap)
        stats = extract_stats(snap)
        if samples:
            return samples, stats, f"live:{base_url} world={wid} (snapshot)"
        snapshot_stats = stats
    except Exception:
        pass
    try:
        payload = _http_get_json(f"{base_url}/api/world/{wid}/metrics/history")
        source = "snapshot+metrics/history" if snapshot_stats else "metrics/history"
        return (
            extract_history_samples(payload),
            snapshot_stats,
            f"live:{base_url} world={wid} ({source})",
        )
    except Exception:
        if snapshot_stats:
            return [], snapshot_stats, f"live:{base_url} world={wid} (snapshot)"
        raise


def load_history_file(path: str) -> list[dict]:
    """Load a metrics-history payload (JSON) or a watch-journal (JSONL)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        payload = json.loads(text)
        return extract_history_samples(payload)
    except json.JSONDecodeError:
        samples: list[dict] = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                samples.append(json.loads(line))
        return samples


def run_probe(frames: int, seed: int, interval: int) -> tuple[list[dict], dict, str]:
    """Run a fresh, deterministic headless sim, sampling trait means as we go."""
    import os

    sys.path.insert(0, os.getcwd())
    from core.entities import Fish
    from core.services.stats.trait_trends import compute_trait_means
    from core.worlds import WorldRegistry

    config = {
        "headless": True,
        "screen_width": 2000,
        "screen_height": 2000,
        "max_population": 60,
        "soccer_enabled": False,
        "plants_enabled": False,
        "poker_activity_enabled": False,
        "auto_food_spawn_rate": 9,
    }
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    samples: list[dict] = []
    for i in range(frames):
        world.step()
        if (i + 1) % interval == 0:
            stats = world.get_stats(include_distributions=False)
            living = [e for e in world.entities_list if isinstance(e, Fish) and not e.is_dead()]
            div = stats.get("diversity_stats", {})
            samples.append(
                {
                    "frame": i + 1,
                    "max_generation": stats.get("max_generation", 0),
                    "population": stats.get("fish_count", 0),
                    "births_total": stats.get("total_births", stats.get("births", 0)),
                    "deaths_total": stats.get("total_deaths", stats.get("deaths", 0)),
                    "diversity_score": div.get("diversity_score", 0.0),
                    "traits": compute_trait_means(living),
                }
            )
    final = world.get_current_metrics(include_distributions=True)
    return samples, extract_stats(final), f"probe frames={frames} seed={seed} interval={interval}"


def _new_samples_since(last_frame: int, samples: list[dict]) -> list[dict]:
    """Samples strictly newer than last_frame (for incremental journaling)."""
    return [s for s in samples if isinstance(s.get("frame"), int) and s["frame"] > last_frame]


def watch(base_url: str, world_id: str | None, interval: float, journal: str | None) -> None:
    """Poll the running server and stream new samples to an append-only journal.

    Runs until interrupted. This is how multi-day trends survive the in-memory
    history buffer (which wraps after max_samples) - the journal is unbounded.
    """
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    last_frame = -1
    print(
        f"[watch] world={wid} interval={interval}s journal={journal or '(none)'} - Ctrl-C to stop",
        flush=True,
    )
    while True:
        try:
            payload = _http_get_json(f"{base_url}/api/world/{wid}/metrics/history")
            samples = extract_history_samples(payload)
            fresh = _new_samples_since(last_frame, samples)
            if fresh:
                last_frame = fresh[-1]["frame"]
                if journal:
                    with open(journal, "a", encoding="utf-8") as jf:
                        for s in fresh:
                            jf.write(json.dumps(s) + "\n")
                latest = fresh[-1]
                drift = _trait_drift(samples)
                top = ""
                if drift:
                    key = max(drift, key=lambda k: abs(drift[k]["pct"]))
                    top = f" topdrift={key}{drift[key]['pct']:+.1f}%"
                print(
                    f"[watch] frame={latest.get('frame')} gen={latest.get('max_generation')} "
                    f"pop={latest.get('population')} div={latest.get('diversity_score')}{top}",
                    flush=True,
                )
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # transient server hiccups should not kill the watch
            print(f"[watch] poll failed: {exc}", flush=True)
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[watch] stopped.", flush=True)
            return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--url", help="Base URL of a running simulation (e.g. http://127.0.0.1:8000)")
    src.add_argument("--stats", help="Path to an exported stats JSON (main.py --export-stats)")
    src.add_argument(
        "--history", help="Path to a metrics-history payload (JSON) or journal (JSONL)"
    )
    src.add_argument("--probe", action="store_true", help="Run a fresh headless probe simulation")
    parser.add_argument("--world", help="World id (defaults to the server's default world)")
    parser.add_argument("--frames", type=int, default=20000, help="Probe length in frames")
    parser.add_argument("--seed", type=int, default=42, help="Probe seed")
    parser.add_argument("--interval", type=int, default=1000, help="Probe sampling interval frames")
    parser.add_argument(
        "--watch", action="store_true", help="Stream samples to a journal (long runs)"
    )
    parser.add_argument("--watch-interval", type=float, default=300.0, help="Watch poll seconds")
    parser.add_argument("--journal", help="Append-only JSONL journal path for --watch")
    parser.add_argument("--json", action="store_true", help="Emit the structured report as JSON")
    parser.add_argument("--out", help="Write the structured report JSON to this file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.watch:
        base = args.url or "http://127.0.0.1:8000"
        try:
            watch(base, args.world, args.watch_interval, args.journal)
        except KeyboardInterrupt:
            print("\n[watch] stopped.", flush=True)
        return 0

    try:
        if args.stats:
            with open(args.stats, encoding="utf-8") as f:
                blob = json.load(f)
            samples = extract_history_samples(blob)
            stats = extract_stats(blob)
            source = f"stats:{args.stats}"
        elif args.history:
            samples = load_history_file(args.history)
            stats = {}
            source = f"history:{args.history}"
        elif args.probe:
            samples, stats, source = run_probe(args.frames, args.seed, args.interval)
        else:
            base = args.url or "http://127.0.0.1:8000"
            samples, stats, source = fetch_live(base, args.world)
    except Exception as exc:
        print(f"error: could not load simulation data: {exc}", file=sys.stderr)
        if not (args.stats or args.history or args.probe):
            print(
                "hint: is the simulation running? start it with `python main.py`, or analyse an "
                "export with --stats / run a fresh probe with --probe.",
                file=sys.stderr,
            )
        return 2

    report = build_report(samples, stats, source)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
