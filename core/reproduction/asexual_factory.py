"""Asexual offspring creation helpers for fish reproduction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from core.energy.energy_utils import apply_energy_delta
from core.util.stable_hash import stable_algorithm_id

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics.reproduction import ReproductionMutationContext


def _diversity_score_for(fish: Fish) -> float | None:
    ecosystem = getattr(fish, "ecosystem", None)
    diversity_stats = getattr(ecosystem, "genetic_diversity_stats", None)
    get_diversity_score = getattr(diversity_stats, "get_diversity_score", None)
    if callable(get_diversity_score):
        score = get_diversity_score()
        if score is None:
            return None
        return float(score)
    return None


def maybe_create_banked_offspring(
    fish: Fish,
    mutation_context: ReproductionMutationContext | None = None,
) -> Fish | None:
    """Attempt a bank-funded asexual reproduction for a single fish."""
    from core.config.fish import ENERGY_MAX_DEFAULT, FISH_BABY_SIZE
    from core.entities.base import LifeStage

    bank = fish._reproduction_component.overflow_energy_bank
    baby_energy_needed = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE

    if (
        fish._reproduction_component.reproduction_cooldown <= 0
        and fish.life_stage == LifeStage.ADULT
        and bank >= baby_energy_needed
    ):
        return create_asexual_offspring(fish, mutation_context=mutation_context)

    return None


def create_asexual_offspring(
    fish: Fish,
    mutation_context: ReproductionMutationContext | None = None,
) -> Fish | None:
    """Create an offspring from a parent fish through asexual reproduction."""
    from core.config.fish import ENERGY_MAX_DEFAULT, FISH_BABY_SIZE, FISH_BASE_SPEED
    from core.entities.fish import Fish
    from core.genetics.reproduction import ReproductionMutationContext
    from core.telemetry.events import ReproductionEvent
    from core.util.rng import require_rng

    rng = require_rng(fish.environment, "ReproductionService.create_asexual_offspring")

    if mutation_context is None:
        mutation_context = ReproductionMutationContext.from_score(_diversity_score_for(fish))

    (
        offspring_genome,
        _unused_fraction,
    ) = fish._reproduction_component.trigger_asexual_reproduction(
        fish.genome,
        rng=rng,
        mutation_context=mutation_context,
    )

    pool = getattr(fish.environment, "genome_code_pool", None)
    if pool is not None:
        from core.genetics.code_policy_traits import (
            mutate_code_policies,
            validate_code_policy_ids,
        )

        mutate_code_policies(offspring_genome.behavioral, pool, rng)
        validate_code_policy_ids(offspring_genome.behavioral, pool, rng)

    # Use standard size_modifier=1.0 for newborn energy calculation (Fair-Start)
    newborn_energy_target = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * 1.0

    bank_used = fish._reproduction_component.consume_overflow_energy_bank(newborn_energy_target)
    remaining_needed = newborn_energy_target - bank_used
    parent_transfer = min(fish.energy, remaining_needed)
    apply_energy_delta(fish, -parent_transfer, source="asexual_reproduction")
    baby_initial_energy = bank_used + parent_transfer

    (min_x, min_y), (max_x, max_y) = fish.environment.get_bounds()
    offset_x = rng.uniform(-30, 30)
    offset_y = rng.uniform(-30, 30)
    baby_x = max(min_x, min(max_x - 50, fish.pos.x + offset_x))
    baby_y = max(min_y, min(max_y - 50, fish.pos.y + offset_y))

    baby = Fish(
        environment=fish.environment,
        movement_strategy=fish.movement_strategy.__class__(),
        species=fish.species,
        x=baby_x,
        y=baby_y,
        speed=FISH_BASE_SPEED,
        genome=offspring_genome,
        generation=fish.generation + 1,
        ecosystem=fish.ecosystem,
        initial_energy=baby_initial_energy,
        parent_id=fish.fish_id,
    )
    cast(Any, baby).protected_niche_birth = mutation_context.preserve_parent_lineage

    composable = fish.genome.behavioral.behavior
    if composable is not None and composable.value is not None:
        behavior_id = composable.value.behavior_id
        algorithm_id = stable_algorithm_id(behavior_id)
        fish._emit_event(ReproductionEvent(algorithm_id, is_asexual=True))

    fish.visual_state.set_birth_effect(60)
    return baby
