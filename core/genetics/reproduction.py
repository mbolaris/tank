"""Value objects for reproduction/inheritance APIs."""

from __future__ import annotations

from dataclasses import dataclass

from core.evolution.mutation import calculate_adaptive_mutation_rate

DIVERSITY_ESCALATION_FLOOR = 0.20
DIVERSITY_DANGER_FLOOR = 0.12
DIVERSITY_RECOVERY_FLOOR = 0.25
DEFAULT_SUB_BEHAVIOR_SWITCH_RATE = 0.08
DANGER_SUB_BEHAVIOR_SWITCH_RATE = 0.16


@dataclass(frozen=True)
class ReproductionMutationContext:
    """Population-level signals used to adapt mutation for one reproduction event.

    A low diversity score alone is not enough to increase mutation. Proposal #25
    requires a stall signal too, plus a guard that avoids randomizing a surviving
    underrepresented lineage.
    """

    diversity_score: float | None = None
    diversity_slope: float | None = None
    trait_drift_stalled: bool = False
    quality_gain_stalled: bool = False
    escalation_active: bool = False
    preserve_parent_lineage: bool = False

    @classmethod
    def from_score(cls, diversity_score: float | None) -> ReproductionMutationContext:
        return cls(diversity_score=diversity_score)

    @property
    def diversity_declining(self) -> bool:
        return self.diversity_slope is not None and self.diversity_slope < 0.0

    @property
    def has_stall_signal(self) -> bool:
        return self.diversity_declining or self.trait_drift_stalled or self.quality_gain_stalled

    @property
    def should_escalate(self) -> bool:
        if self.preserve_parent_lineage or self.diversity_score is None:
            return False
        return self.escalation_active or (
            self.diversity_score < DIVERSITY_ESCALATION_FLOOR and self.has_stall_signal
        )

    def mutation_multiplier(self) -> float:
        if not self.should_escalate or self.diversity_score is None:
            return 1.0
        if self.diversity_score < DIVERSITY_DANGER_FLOOR:
            return 3.0

        span = DIVERSITY_ESCALATION_FLOOR - DIVERSITY_DANGER_FLOOR
        if span <= 0:
            return 1.0
        t = (DIVERSITY_ESCALATION_FLOOR - self.diversity_score) / span
        return 1.0 + max(0.0, min(1.0, t))

    def sub_behavior_switch_rate(
        self, base_rate: float = DEFAULT_SUB_BEHAVIOR_SWITCH_RATE
    ) -> float:
        if not self.should_escalate or self.diversity_score is None:
            return base_rate
        if self.diversity_score < DIVERSITY_DANGER_FLOOR:
            return DANGER_SUB_BEHAVIOR_SWITCH_RATE
        return base_rate


@dataclass(frozen=True)
class ReproductionParams:
    """Inputs that control mutation for a reproduction event.

    TUNED FOR FASTER EVOLUTION: Increased defaults to accelerate adaptation.
    """

    mutation_rate: float = 0.15  # Increased from 0.1 for faster evolution
    mutation_strength: float = 0.15  # Increased from 0.1 for larger mutations

    def adaptive_mutation(
        self,
        mutation_context: ReproductionMutationContext | float | None = None,
    ) -> tuple[float, float]:
        """Return (adaptive_rate, adaptive_strength) after clamping."""
        context: ReproductionMutationContext | None
        if isinstance(mutation_context, (int, float)):
            context = ReproductionMutationContext.from_score(float(mutation_context))
        else:
            context = mutation_context

        rate = self.mutation_rate
        strength = self.mutation_strength
        if context is not None:
            factor = context.mutation_multiplier()
            rate *= factor
            strength *= factor
        return calculate_adaptive_mutation_rate(rate, strength)
