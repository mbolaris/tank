"""Value objects for reproduction/inheritance APIs."""

from __future__ import annotations

from dataclasses import dataclass

from core.evolution.mutation import calculate_adaptive_mutation_rate


@dataclass(frozen=True)
class ReproductionParams:
    """Inputs that control mutation for a reproduction event.

    TUNED FOR FASTER EVOLUTION: Increased defaults to accelerate adaptation.
    """

    mutation_rate: float = 0.15  # Increased from 0.1 for faster evolution
    mutation_strength: float = 0.15  # Increased from 0.1 for larger mutations

    def adaptive_mutation(self) -> tuple[float, float]:
        """Return (adaptive_rate, adaptive_strength) after clamping."""
        return calculate_adaptive_mutation_rate(self.mutation_rate, self.mutation_strength)
