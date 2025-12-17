"""Validation helpers for genetic data structures.

These functions are intended for debugging and safety checks, not hot-path logic.
They help catch subtle bugs (out-of-range traits, wrong types) close to the source.
"""

from __future__ import annotations

import math
from typing import List

from core.genetics.trait import GeneticTrait, TraitSpec


def validate_traits_from_specs(specs: List[TraitSpec], traits: object, *, path: str) -> List[str]:
    """Validate a trait container against TraitSpec definitions.

    Returns a list of human-readable issues; empty means valid.
    """
    issues: List[str] = []
    for spec in specs:
        if not hasattr(traits, spec.name):
            issues.append(f"{path}.{spec.name}: missing attribute")
            continue

        trait = getattr(traits, spec.name)
        if not isinstance(trait, GeneticTrait):
            issues.append(f"{path}.{spec.name}: expected GeneticTrait, got {type(trait).__name__}")
            continue

        # Meta bounds (broad, persistence-safe)
        if not math.isfinite(float(trait.mutation_rate)):
            issues.append(f"{path}.{spec.name}.mutation_rate: not finite ({trait.mutation_rate})")
        if trait.mutation_rate < 0.0:
            issues.append(f"{path}.{spec.name}.mutation_rate: {trait.mutation_rate} < 0.0")
        if not math.isfinite(float(trait.mutation_strength)):
            issues.append(
                f"{path}.{spec.name}.mutation_strength: not finite ({trait.mutation_strength})"
            )
        if trait.mutation_strength < 0.0:
            issues.append(f"{path}.{spec.name}.mutation_strength: {trait.mutation_strength} < 0.0")
        if not math.isfinite(float(trait.hgt_probability)):
            issues.append(
                f"{path}.{spec.name}.hgt_probability: not finite ({trait.hgt_probability})"
            )
        if not (0.0 <= trait.hgt_probability <= 1.0):
            issues.append(f"{path}.{spec.name}.hgt_probability: {trait.hgt_probability} not in [0, 1]")

        # Value bounds
        if spec.discrete:
            if not isinstance(trait.value, int):
                issues.append(f"{path}.{spec.name}.value: expected int, got {type(trait.value).__name__}")
                continue
            if trait.value < int(spec.min_val) or trait.value > int(spec.max_val):
                issues.append(
                    f"{path}.{spec.name}.value: {trait.value} not in [{int(spec.min_val)}, {int(spec.max_val)}]"
                )
        else:
            if not isinstance(trait.value, (int, float)):
                issues.append(
                    f"{path}.{spec.name}.value: expected float, got {type(trait.value).__name__}"
                )
                continue
            val = float(trait.value)
            if not math.isfinite(val):
                issues.append(f"{path}.{spec.name}.value: not finite ({trait.value})")
                continue
            if val < spec.min_val or val > spec.max_val:
                issues.append(
                    f"{path}.{spec.name}.value: {val} not in [{spec.min_val}, {spec.max_val}]"
                )

    return issues
