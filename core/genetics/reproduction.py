"""Value objects for reproduction/inheritance APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from core.evolution.mutation import calculate_adaptive_mutation_rate


@dataclass(frozen=True)
class ReproductionParams:
    """Inputs that control mutation for a reproduction event."""

    mutation_rate: float = 0.1
    mutation_strength: float = 0.1
    population_stress: float = 0.0

    def adaptive_mutation(self) -> Tuple[float, float]:
        """Return (adaptive_rate, adaptive_strength) after stress adjustment."""
        return calculate_adaptive_mutation_rate(
            self.mutation_rate, self.mutation_strength, self.population_stress
        )

