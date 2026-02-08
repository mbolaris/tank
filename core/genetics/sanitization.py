"""Genome sanitization for external/untrusted contributions.

Provides defense-in-depth sanitization for genome data arriving from external
sources (API endpoints, file imports, agent contributions). Ensures malformed,
adversarial, or out-of-range genome data cannot crash the simulation.

Usage:
    from core.genetics.sanitization import sanitize_genome_dict
    clean_data = sanitize_genome_dict(untrusted_data)
    genome = Genome.from_dict(clean_data, rng=rng)
"""

from __future__ import annotations

import math
import re
from typing import Any

MAX_STRING_LENGTH = 256
MAX_DICT_DEPTH = 5
MAX_DICT_KEYS = 100
MAX_PARAM_COUNT = 50
MAX_PREFERENCE_COUNT = 30

_SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.:/ ]+$")


def sanitize_float(
    value: Any, default: float = 0.0, min_val: float = -1e6, max_val: float = 1e6
) -> float:
    """Sanitize a value to a safe float. Handles None, NaN, Inf, strings, booleans."""
    if value is None or isinstance(value, bool):
        return default
    try:
        f = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return max(min_val, min(max_val, f))


def sanitize_int(value: Any, default: int = 0, min_val: int = -1000, max_val: int = 1000) -> int:
    """Sanitize a value to a safe integer."""
    if value is None or isinstance(value, bool):
        return default
    try:
        i = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(min_val, min(max_val, i))


def sanitize_string(value: Any, default: str = "", max_length: int = MAX_STRING_LENGTH) -> str:
    """Sanitize a value to a safe string. Rejects suspicious characters."""
    if not isinstance(value, str):
        return default
    s: str = value[:max_length]
    if not _SAFE_STRING_PATTERN.match(s):
        return default
    return s


def sanitize_dict(
    value: Any,
    max_keys: int = MAX_DICT_KEYS,
    max_depth: int = MAX_DICT_DEPTH,
    _current_depth: int = 0,
) -> dict[str, Any]:
    """Sanitize a dictionary value, preventing deeply nested bombs."""
    if not isinstance(value, dict) or _current_depth >= max_depth:
        return {}
    result: dict[str, Any] = {}
    for i, (k, v) in enumerate(value.items()):
        if i >= max_keys:
            break
        if not isinstance(k, str):
            continue
        safe_key = sanitize_string(k, default="")
        if not safe_key:
            continue
        if isinstance(v, dict):
            result[safe_key] = sanitize_dict(v, max_keys, max_depth, _current_depth + 1)
        elif isinstance(v, (list, tuple)):
            result[safe_key] = v[:max_keys]
        else:
            result[safe_key] = v
    return result


def sanitize_float_params(
    params: Any,
    min_val: float = -10.0,
    max_val: float = 10.0,
    max_count: int = MAX_PARAM_COUNT,
) -> dict[str, float] | None:
    """Sanitize a dictionary of float parameters (behavior params, policy params)."""
    if params is None or not isinstance(params, dict):
        return None
    result: dict[str, float] = {}
    for i, (k, v) in enumerate(params.items()):
        if i >= max_count:
            break
        safe_key = sanitize_string(str(k), default="")
        if not safe_key:
            continue
        result[safe_key] = sanitize_float(v, default=0.0, min_val=min_val, max_val=max_val)
    return result if result else None


def sanitize_mate_preferences(prefs: Any) -> dict[str, float]:
    """Sanitize mate preference dictionary. Clamps weights to [0, 1]."""
    if not isinstance(prefs, dict):
        return {}
    result: dict[str, float] = {}
    for i, (k, v) in enumerate(prefs.items()):
        if i >= MAX_PREFERENCE_COUNT:
            break
        safe_key = sanitize_string(str(k), default="")
        if not safe_key:
            continue
        if safe_key.startswith("prefer_"):
            result[safe_key] = sanitize_float(v, default=0.5, min_val=0.0, max_val=1.0)
        else:
            result[safe_key] = sanitize_float(v, default=0.5, min_val=0.0, max_val=5.0)
    return result


def sanitize_genome_dict(data: Any) -> dict[str, Any]:
    """Sanitize an entire genome dictionary from an untrusted source.

    Main entry point for external genome data. Replaces invalid values with safe
    defaults rather than raising exceptions. Output is safe for Genome.from_dict().
    """
    if not isinstance(data, dict):
        return {}
    result = sanitize_dict(data, max_keys=200, max_depth=5)
    if "physical" in result and isinstance(result["physical"], dict):
        result["physical"] = _sanitize_physical_traits(result["physical"])
    if "behavioral" in result and isinstance(result["behavioral"], dict):
        result["behavioral"] = _sanitize_behavioral_traits(result["behavioral"])
    if "trait_meta" in result and isinstance(result["trait_meta"], dict):
        result["trait_meta"] = _sanitize_trait_meta(result["trait_meta"])
    if "schema_version" in result:
        result["schema_version"] = sanitize_int(
            result["schema_version"], default=2, min_val=1, max_val=100
        )
    return result


def _sanitize_trait_from_spec(data: dict[str, Any], spec: Any) -> Any:
    """Sanitize a single trait value using its TraitSpec."""
    mid = (spec.min_val + spec.max_val) / 2
    if spec.discrete:
        return sanitize_int(
            data[spec.name], default=int(mid), min_val=int(spec.min_val), max_val=int(spec.max_val)
        )
    return sanitize_float(data[spec.name], default=mid, min_val=spec.min_val, max_val=spec.max_val)


def _sanitize_physical_traits(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize physical trait values against their specs."""
    from core.genetics.physical import PHYSICAL_TRAIT_SPECS

    result: dict[str, Any] = {}
    for spec in PHYSICAL_TRAIT_SPECS:
        if spec.name in data:
            result[spec.name] = _sanitize_trait_from_spec(data, spec)
    return result


def _sanitize_behavioral_traits(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize behavioral trait values."""
    from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS

    result: dict[str, Any] = {}
    for spec in BEHAVIORAL_TRAIT_SPECS:
        if spec.name in data:
            result[spec.name] = _sanitize_trait_from_spec(data, spec)
    if "behavior" in data:
        result["behavior"] = (
            _sanitize_composable_behavior(data["behavior"])
            if isinstance(data["behavior"], dict)
            else None
        )
    if "poker_strategy" in data:
        result["poker_strategy"] = (
            sanitize_dict(data["poker_strategy"])
            if isinstance(data["poker_strategy"], dict)
            else None
        )
    if "mate_preferences" in data:
        result["mate_preferences"] = sanitize_mate_preferences(data.get("mate_preferences"))
    for kind in ("movement_policy", "poker_policy", "soccer_policy"):
        id_key = f"{kind}_id"
        params_key = f"{kind}_params"
        if id_key in data:
            result[id_key] = sanitize_string(data[id_key], default="") or None
        if params_key in data:
            result[params_key] = sanitize_float_params(data[params_key])
    return result


def _sanitize_composable_behavior(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a composable behavior dictionary."""
    from core.algorithms.composable.definitions import (
        SUB_BEHAVIOR_PARAMS,
        FoodApproach,
        PokerEngagement,
        SocialMode,
        ThreatResponse,
    )

    result: dict[str, Any] = {"type": "ComposableBehavior"}
    result["threat_response"] = sanitize_int(
        data.get("threat_response", 0), default=0, min_val=0, max_val=len(ThreatResponse) - 1
    )
    result["food_approach"] = sanitize_int(
        data.get("food_approach", 0), default=0, min_val=0, max_val=len(FoodApproach) - 1
    )
    result["social_mode"] = sanitize_int(
        data.get("social_mode", 0), default=0, min_val=0, max_val=len(SocialMode) - 1
    )
    result["poker_engagement"] = sanitize_int(
        data.get("poker_engagement", 1), default=1, min_val=0, max_val=len(PokerEngagement) - 1
    )
    raw_params = data.get("parameters", {})
    if isinstance(raw_params, dict):
        clean_params: dict[str, float] = {}
        for key, (low, high) in SUB_BEHAVIOR_PARAMS.items():
            if key in raw_params:
                clean_params[key] = sanitize_float(
                    raw_params[key], default=(low + high) / 2, min_val=low, max_val=high
                )
            else:
                clean_params[key] = (low + high) / 2
        result["parameters"] = clean_params
    else:
        result["parameters"] = {}
    return result


def _sanitize_trait_meta(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize trait metadata (mutation_rate, mutation_strength, hgt_probability)."""
    from core.genetics.trait import (
        META_MUTATION_RATE_MAX,
        META_MUTATION_RATE_MIN,
        META_MUTATION_STRENGTH_MAX,
        META_MUTATION_STRENGTH_MIN,
    )

    result: dict[str, Any] = {}
    for trait_name, meta in data.items():
        if not isinstance(trait_name, str) or not isinstance(meta, dict):
            continue
        safe_meta: dict[str, float] = {}
        if "mutation_rate" in meta:
            safe_meta["mutation_rate"] = sanitize_float(
                meta["mutation_rate"],
                default=1.0,
                min_val=META_MUTATION_RATE_MIN,
                max_val=META_MUTATION_RATE_MAX,
            )
        if "mutation_strength" in meta:
            safe_meta["mutation_strength"] = sanitize_float(
                meta["mutation_strength"],
                default=1.0,
                min_val=META_MUTATION_STRENGTH_MIN,
                max_val=META_MUTATION_STRENGTH_MAX,
            )
        if "hgt_probability" in meta:
            safe_meta["hgt_probability"] = sanitize_float(
                meta["hgt_probability"], default=0.1, min_val=0.0, max_val=1.0
            )
        if safe_meta:
            result[trait_name] = safe_meta
    return result


def validate_external_genome(data: Any) -> dict[str, Any]:
    """Validate and report on an external genome contribution.

    Unlike sanitize_genome_dict which silently fixes problems, this reports
    issues so contributing agents can learn from their mistakes.
    """
    issues: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "valid": False,
            "issues": [f"Expected dict, got {type(data).__name__}"],
            "warnings": [],
            "sanitized": {},
        }

    if "physical" not in data:
        warnings.append("Missing 'physical' section - defaults will be used")
    if "behavioral" not in data:
        warnings.append("Missing 'behavioral' section - defaults will be used")

    if isinstance(data.get("physical"), dict):
        _validate_trait_values(data["physical"], "physical", issues, warnings)
    if isinstance(data.get("behavioral"), dict):
        _validate_trait_values(data["behavioral"], "behavioral", issues, warnings)

    for key in data:
        if key not in ("physical", "behavioral", "trait_meta", "schema_version", "type"):
            warnings.append(f"Unknown top-level field '{key}' will be ignored")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "sanitized": sanitize_genome_dict(data),
    }


def _validate_trait_values(
    data: dict[str, Any], section: str, issues: list[str], warnings: list[str]
) -> None:
    """Check trait values for common problems."""
    for key, value in data.items():
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                issues.append(f"{section}.{key}: NaN/Inf value")
            elif abs(value) > 1e6:
                warnings.append(f"{section}.{key}: Extremely large value ({value})")
        elif isinstance(value, str):
            if len(value) > MAX_STRING_LENGTH:
                warnings.append(f"{section}.{key}: String truncated (len={len(value)})")
            if not _SAFE_STRING_PATTERN.match(value[:MAX_STRING_LENGTH]):
                issues.append(f"{section}.{key}: Contains disallowed characters")
        elif isinstance(value, dict):
            if len(value) > MAX_DICT_KEYS:
                warnings.append(f"{section}.{key}: Dict truncated ({len(value)} keys)")
