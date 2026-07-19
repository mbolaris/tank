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
    from core.config.simulation_config import EcosystemConfig
    from core.entities import Fish


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
        # Per-population memoization for lineage-preservation checks. Both the
        # behavior counts and per-parent isolation results are pure functions
        # of fish list membership and genomes: genomes never mutate in place
        # after creation, and the (cached) fish list object changes identity
        # whenever membership changes (spawns/removals rebuild it - see
        # CacheManager). So the cache is safe to reuse across frames and
        # across handler calls within the same frame; _behavior_counts_for's
        # identity check is the only invalidation this needs.
        self._cached_fish_list: list[Fish] | None = None
        self._cached_behavior_counts: dict[str, int] = {}
        # Keyed by id(parent); the stored parent reference keeps the object
        # alive so ids cannot be recycled while an entry exists.
        self._cached_isolation: dict[int, tuple[Fish, bool]] = {}

    def record_diversity_sample(self, frame: int) -> None:
        """Advance the diversity trend window and the escalation latch.

        Runs once per frame, unconditionally - this is deliberately the only
        place the escalation hysteresis latch (see ``_update_escalation_state``)
        transitions. ``context_for_parents`` only *reads* the latch, so it can
        be called lazily (e.g. only for fish that reach an actual reproduction
        attempt) without changing how often the latch itself advances.
        """
        score = self._diversity_score_provider()
        if score is not None and not (
            self._diversity_samples
            and frame - self._diversity_samples[-1][0] < self.SAMPLE_INTERVAL_FRAMES
        ):
            self._diversity_samples.append((frame, score))
            min_frame = frame - self.STALL_WINDOW_FRAMES
            while self._diversity_samples and self._diversity_samples[0][0] < min_frame:
                self._diversity_samples.pop(0)

        # Slope must be read after the append above so the latch reacts to
        # this frame's sample the same way a same-frame context_for_parents
        # call always has.
        self._update_escalation_state(score, self._diversity_slope())

    def _update_escalation_state(
        self, diversity_score: float | None, diversity_slope: float | None
    ) -> None:
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

    def context_for_parents(
        self,
        *parents: Fish,
        ecosystem_config: EcosystemConfig | None = None,
    ) -> ReproductionMutationContext:
        """Build a mutation context for one reproduction attempt.

        Reads the escalation latch that ``record_diversity_sample`` already
        advanced for this frame; safe to call lazily, only for fish that reach
        an actual reproduction attempt, without perturbing trajectories.
        """
        diversity_score = self._diversity_score_provider()
        diversity_slope = self._diversity_slope()

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

    def _behavior_counts_for(self, fish_list: list[Fish]) -> dict[str, int]:
        if fish_list is not self._cached_fish_list:
            counts: dict[str, int] = {}
            for fish in fish_list:
                behavior_id = self._behavior_id_for(fish)
                if behavior_id is not None:
                    counts[behavior_id] = counts.get(behavior_id, 0) + 1
            self._cached_fish_list = fish_list
            self._cached_behavior_counts = counts
            self._cached_isolation = {}
        return self._cached_behavior_counts

    def _preserve_underrepresented_lineage(self, parents: tuple[Fish, ...]) -> bool:
        fish_list = self._fish_provider()
        if len(fish_list) < 4 or not parents:
            return False

        counts = self._behavior_counts_for(fish_list)

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
        population = len(fish_list)
        if population < 4:
            return False

        max_neighbors = max(1, int(population * self.UNDERREPRESENTED_GENETIC_NICHE_SHARE))
        for parent in parents:
            cached = self._cached_isolation.get(id(parent))
            if cached is None or cached[0] is not parent:
                isolated = self._is_genetically_isolated(parent, fish_list, max_neighbors)
                self._cached_isolation[id(parent)] = (parent, isolated)
            else:
                isolated = cached[1]
            if isolated:
                return True
        return False

    def _is_genetically_isolated(
        self,
        parent: Fish,
        fish_list: list[Fish],
        max_neighbors: int,
    ) -> bool:
        from core.genetics.diversity import genetic_distance

        neighbor_count = 0
        for fish in fish_list:
            if genetic_distance(parent.genome, fish.genome) <= self.GENETIC_NICHE_RADIUS:
                neighbor_count += 1
                if neighbor_count > max_neighbors:
                    return False
        return True

    @staticmethod
    def _behavior_id_for(fish: Fish) -> str | None:
        behavior = fish.genome.behavioral.behavior
        if behavior is None or behavior.value is None:
            return None
        return behavior.value.behavior_id
