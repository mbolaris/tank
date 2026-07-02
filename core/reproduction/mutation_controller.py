"""Diversity feedback controller for reproduction-time mutation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from core.genetics.reproduction import (
    DIVERSITY_ESCALATION_FLOOR,
    DIVERSITY_RECOVERY_FLOOR,
    ReproductionMutationContext,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.config.simulation_config import EcosystemConfig


class DiversityMutationController:
    """Build mutation contexts from population diversity and lineage signals."""

    SAMPLE_INTERVAL_FRAMES = 500
    STALL_WINDOW_FRAMES = 10_000
    UNDERREPRESENTED_LINEAGE_SHARE = 0.15
    UNDERREPRESENTED_GENETIC_NICHE_SHARE = 0.20
    GENETIC_NICHE_RADIUS = 0.30

    def __init__(
        self,
        *,
        diversity_score_provider: Callable[[], float | None],
        fish_provider: Callable[[], list[Fish]],
    ) -> None:
        self._diversity_score_provider = diversity_score_provider
        self._fish_provider = fish_provider
        self._diversity_samples: list[tuple[int, float]] = []
        self._escalation_active = False

    def record_diversity_sample(self, frame: int) -> None:
        score = self._diversity_score_provider()
        if score is None:
            return
        if (
            self._diversity_samples
            and frame - self._diversity_samples[-1][0] < self.SAMPLE_INTERVAL_FRAMES
        ):
            return

        self._diversity_samples.append((frame, score))
        min_frame = frame - self.STALL_WINDOW_FRAMES
        while self._diversity_samples and self._diversity_samples[0][0] < min_frame:
            self._diversity_samples.pop(0)

    def context_for_parents(
        self,
        *parents: Fish,
        ecosystem_config: EcosystemConfig | None = None,
    ) -> ReproductionMutationContext:
        diversity_score = self._diversity_score_provider()
        diversity_slope = self._diversity_slope()
        diversity_declining = diversity_slope is not None and diversity_slope < 0.0

        if diversity_score is None or (
            self._escalation_active and diversity_score >= DIVERSITY_RECOVERY_FLOOR
        ):
            self._escalation_active = False
        elif (
            not self._escalation_active
            and diversity_score < DIVERSITY_ESCALATION_FLOOR
            and diversity_declining
        ):
            self._escalation_active = True

        panic_enabled = getattr(ecosystem_config, "panic_button_enabled", False)
        panic_k = getattr(ecosystem_config, "panic_button_k", 1.0)
        panic_target = getattr(ecosystem_config, "panic_button_target", 0.30)

        return ReproductionMutationContext(
            diversity_score=diversity_score,
            diversity_slope=diversity_slope,
            escalation_active=self._escalation_active,
            preserve_parent_lineage=self._preserve_underrepresented_lineage(parents),
            panic_button_enabled=panic_enabled,
            panic_button_k=panic_k,
            panic_button_target=panic_target,
        )

    def _diversity_slope(self) -> float | None:
        if len(self._diversity_samples) < 2:
            return None
        first_frame, first_score = self._diversity_samples[0]
        last_frame, last_score = self._diversity_samples[-1]
        frame_span = last_frame - first_frame
        if frame_span <= 0:
            return None
        return (last_score - first_score) / frame_span

    def _preserve_underrepresented_lineage(self, parents: tuple[Fish, ...]) -> bool:
        fish_list = self._fish_provider()
        if len(fish_list) < 4 or not parents:
            return False

        counts: dict[str, int] = {}
        for fish in fish_list:
            behavior_id = self._behavior_id_for(fish)
            if behavior_id is not None:
                counts[behavior_id] = counts.get(behavior_id, 0) + 1

        population = len(fish_list)
        if len(counts) > 1:
            for parent in parents:
                behavior_id = self._behavior_id_for(parent)
                if behavior_id is None:
                    continue
                if counts.get(behavior_id, 0) / population <= self.UNDERREPRESENTED_LINEAGE_SHARE:
                    return True
        return self._preserve_genetically_isolated_parent(parents, fish_list)

    def _preserve_genetically_isolated_parent(
        self,
        parents: tuple[Fish, ...],
        fish_list: list[Fish],
    ) -> bool:
        from core.genetics.diversity import genetic_distance

        population = len(fish_list)
        if population < 4:
            return False

        max_neighbors = max(1, int(population * self.UNDERREPRESENTED_GENETIC_NICHE_SHARE))
        for parent in parents:
            neighbor_count = 0
            for fish in fish_list:
                if genetic_distance(parent.genome, fish.genome) <= self.GENETIC_NICHE_RADIUS:
                    neighbor_count += 1
                    if neighbor_count > max_neighbors:
                        break
            if neighbor_count <= max_neighbors:
                return True
        return False

    @staticmethod
    def _behavior_id_for(fish: Fish) -> str | None:
        behavior = fish.genome.behavioral.behavior
        if behavior is None or behavior.value is None:
            return None
        return behavior.value.behavior_id
