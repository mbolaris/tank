"""Pure computational and data analysis functions for evolution health report.

This file holds data extraction, history analysis, bottleneck filtering,
selection quality scoring, and health assessment logic.
"""

from typing import Any


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
# Sliding window width (in samples) for local CV when filtering stable windows
_STABLE_POP_LOCAL_WINDOW = 20

# Known [min, max] bounds for the tracked behavioral traits.
TRAIT_BOUNDS: dict[str, tuple[float, float]] = {
    "pursuit_aggression": (0.0, 1.0),
    "prediction_skill": (0.0, 1.0),
    "hunting_stamina": (0.0, 1.0),
    "aggression": (0.0, 1.0),
    "speed": (0.5, 3.0),
    "size": (0.5, 3.0),
}


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------
def _first_present(obj: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return None


def _unwrap_snapshot(obj: dict[str, Any]) -> dict[str, Any]:
    """Unwrap the snapshot API envelope if present."""
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
        payload = _unwrap_snapshot(payload)
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
    obj = _unwrap_snapshot(obj)
    if isinstance(obj.get("stats"), dict):
        stats: dict[str, Any] = obj["stats"]
        return stats
    return dict(obj)


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
        "population",
        "fish_count",
        "mean_population",
        "avg_pop",
        "final_population",
        "final_fish_count",
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
    return float((var**0.5) / abs(mean))


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
    result["selection_quality"] = _selection_quality(samples, result["trait_drift"])
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


def _local_cv(pops: list[float], center: int, window: int) -> float:
    """Coefficient of variation of the *window* samples around *center*."""
    half = window // 2
    start = max(0, center - half)
    end = min(len(pops), center + half + 1)
    return _coefficient_of_variation(pops[start:end])


def _stable_samples(
    samples: list[dict[str, Any]],
    pop_floor: float = POP_STABLE_MIN,
    local_window: int = _STABLE_POP_LOCAL_WINDOW,
    local_cv_ceiling: float = POP_CV_UNSTABLE,
) -> list[dict[str, Any]]:
    """Return only samples that appear to come from a stable population window."""
    pops = [float(s.get("population", 0)) for s in samples]
    result: list[dict[str, Any]] = []
    for i, s in enumerate(samples):
        pop = float(s.get("population", 0))
        if pop < pop_floor:
            continue
        if _local_cv(pops, i, local_window) >= local_cv_ceiling:
            continue
        result.append(s)
    return result


def _boot_ids(samples: list[dict[str, Any]]) -> set[int]:
    """Unique boot_ids present in the sample set; skips samples without one."""
    ids: set[int] = set()
    for s in samples:
        bid = s.get("boot_id")
        if isinstance(bid, int):
            ids.add(bid)
    return ids


def _range_normalized_drift(
    raw_drift: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Return per-trait |delta| / trait_range, clipped to [0, 1]."""
    result: dict[str, float] = {}
    for key, d in raw_drift.items():
        lo, hi = TRAIT_BOUNDS.get(key, (None, None))
        if lo is None or hi is None or hi == lo:
            continue
        norm = abs(d["delta"]) / (hi - lo)
        result[key] = round(min(norm, 1.0), 5)
    return result


def _selection_quality(
    all_samples: list[dict[str, Any]],
    raw_drift: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Bottleneck-Conditioned Selection Ruler."""
    boot_ids = sorted(_boot_ids(all_samples))
    epoch_mixed = len(boot_ids) > 1

    rn_drift = _range_normalized_drift(raw_drift)
    stable = _stable_samples(all_samples)
    stable_count = len(stable)

    if stable_count < MIN_SAMPLES_FOR_TREND:
        confidence = "epoch_confounded" if epoch_mixed else "insufficient_stable_samples"
        return {
            "confidence": confidence,
            "stable_sample_count": stable_count,
            "boot_ids_in_window": boot_ids,
            "epoch_mixed": epoch_mixed,
            "conditioned_drift": {},
            "range_normalized_drift": rn_drift,
            "conditioned_selection_detected": False,
        }

    cond_drift = _trait_drift(stable)
    cond_sel = any(d["selection"] for d in cond_drift.values())
    raw_sel = any(d["selection"] for d in raw_drift.values())

    if epoch_mixed:
        confidence = "epoch_confounded"
    elif raw_sel and not cond_sel:
        confidence = "bottleneck_confounded"
    else:
        confidence = "high_confidence_selection" if cond_sel else "high_confidence_no_selection"

    return {
        "confidence": confidence,
        "stable_sample_count": stable_count,
        "boot_ids_in_window": boot_ids,
        "epoch_mixed": epoch_mixed,
        "conditioned_drift": cond_drift,
        "range_normalized_drift": rn_drift,
        "conditioned_selection_detected": cond_sel,
    }


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

    # Selection axis.
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
            axes["foraging"] = "broken"
            findings.append(
                f"Starvation is {starv*100:.0f}% of deaths (>= {STARVATION_BROKEN*100:.0f}%): "
                "food-seeking is likely broken."
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


def build_report(
    samples: list[dict[str, Any]], stats: dict[str, Any], source: str
) -> dict[str, Any]:
    hist = analyze_history(samples)
    inst = analyze_stats(stats)
    assessment = assess(hist, inst)
    # The recommendations list will be filled in evolution_report.py
    # or by importing tools.evolution_report_display
    from tools.evolution_report_display import recommend

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
