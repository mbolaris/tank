"""Selection Quality calculation service for population metrics.

Provides bottleneck-conditioned selection quality analysis over history samples.
Used by backend metrics history and evolution analyzer tools.
"""

from __future__ import annotations

from typing import Any


TRAIT_DRIFT_SELECTION_PCT = 5.0  # |rel change| >= this => directional selection
POP_STABLE_MIN = 20.0  # stable population floor (fish)
POP_CV_UNSTABLE = 0.35  # coefficient of variation above this => boom/bust
MIN_SAMPLES_FOR_TREND = 3
_STABLE_POP_LOCAL_WINDOW = 20

TRAIT_BOUNDS: dict[str, tuple[float, float]] = {
    "pursuit_aggression": (0.0, 1.0),
    "prediction_skill": (0.0, 1.0),
    "hunting_stamina": (0.0, 1.0),
    "aggression": (0.0, 1.0),
    "speed": (0.5, 3.0),
    "size": (0.5, 3.0),
}


def _coefficient_of_variation(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    if mean == 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / n
    return float((var**0.5) / abs(mean))


def _is_directional_trend(series: list[float], min_consistency: float = 0.45) -> bool:
    """Return True if series exhibits directional trend consistency rather than random walk oscillation."""
    if len(series) < 2:
        return False
    net_delta = abs(series[-1] - series[0])
    if net_delta == 0:
        return False
    path_length = sum(abs(series[i + 1] - series[i]) for i in range(len(series) - 1))
    if path_length == 0:
        return False
    return (net_delta / path_length) >= min_consistency


def compute_trait_drift(samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-trait first->last drift across samples that carry trait means."""
    with_traits = [s for s in samples if isinstance(s.get("traits"), dict) and s["traits"]]
    drift: dict[str, dict[str, Any]] = {}
    if len(with_traits) < 2:
        return drift
    first, last = with_traits[0], with_traits[-1]
    keys = [k for k in first["traits"] if k in last["traits"]]
    for key in keys:
        series = [float(s["traits"][key]) for s in with_traits if key in s["traits"]]
        start = float(first["traits"][key])
        end = float(last["traits"][key])
        delta = end - start
        rel = (delta / start * 100.0) if start else 0.0
        is_directional = _is_directional_trend(series) if len(series) >= 3 else True
        drift[key] = {
            "start": round(start, 5),
            "end": round(end, 5),
            "delta": round(delta, 5),
            "pct": round(rel, 2),
            "selection": abs(rel) >= TRAIT_DRIFT_SELECTION_PCT and is_directional,
            "directional_consistency": is_directional,
        }
    return drift


def _local_cv(pops: list[float], center: int, window: int) -> float:
    half = window // 2
    start = max(0, center - half)
    end = min(len(pops), center + half + 1)
    return _coefficient_of_variation(pops[start:end])


def filter_stable_samples(
    samples: list[dict[str, Any]],
    pop_floor: float = POP_STABLE_MIN,
    local_window: int = _STABLE_POP_LOCAL_WINDOW,
    local_cv_ceiling: float = POP_CV_UNSTABLE,
) -> list[dict[str, Any]]:
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
    ids: set[int] = set()
    for s in samples:
        bid = s.get("boot_id")
        if isinstance(bid, int):
            ids.add(bid)
    return ids


def _range_normalized_drift(raw_drift: dict[str, dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, d in raw_drift.items():
        lo, hi = TRAIT_BOUNDS.get(key, (None, None))
        if lo is None or hi is None or hi == lo:
            continue
        norm = abs(d["delta"]) / (hi - lo)
        result[key] = round(min(norm, 1.0), 5)
    return result


def compute_selection_quality(
    all_samples: list[dict[str, Any]],
    raw_drift: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if raw_drift is None:
        raw_drift = compute_trait_drift(all_samples)

    boot_ids = sorted(_boot_ids(all_samples))
    epoch_mixed = len(boot_ids) > 1

    rn_drift = _range_normalized_drift(raw_drift)
    stable = filter_stable_samples(all_samples)
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

    cond_drift = compute_trait_drift(stable)
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
        "conditioned_selection_detected": cond_sel and confidence.startswith("high"),
    }
