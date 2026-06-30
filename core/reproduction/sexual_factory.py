"""Sexual reproduction helpers for fish reproduction paths."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.energy.energy_utils import apply_energy_delta
from core.util.stable_hash import stable_algorithm_id

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics.reproduction import ReproductionMutationContext
    from core.simulation import SimulationEngine


MutationContextProvider = Callable[["Fish", "Fish"], "ReproductionMutationContext"]


@dataclass(frozen=True)
class ProximityMatingConfig:
    """Local gates for standard proximity mating."""

    max_distance: float
    min_energy_ratio: float
    parent_energy_contribution: float
    mutation_rate: float
    mutation_strength: float


def run_proximity_mating_cycle(
    *,
    engine: SimulationEngine,
    fish_list: list[Fish],
    fish_count: int,
    required_credits: float,
    mutation_context_provider: MutationContextProvider,
) -> int:
    """Attempt deterministic proximity mating for eligible fish pairs."""
    from core.config.fish import (
        STANDARD_MATING_DISTANCE,
        STANDARD_MATING_MIN_ENERGY_RATIO,
        STANDARD_MATING_MUTATION_RATE,
        STANDARD_MATING_MUTATION_STRENGTH,
        STANDARD_MATING_PARENT_ENERGY_CONTRIBUTION,
    )

    if len(fish_list) < 2:
        return 0

    ecosystem = engine.ecosystem
    if ecosystem is not None and fish_count >= ecosystem.max_population:
        return 0

    config = ProximityMatingConfig(
        max_distance=STANDARD_MATING_DISTANCE,
        min_energy_ratio=STANDARD_MATING_MIN_ENERGY_RATIO,
        parent_energy_contribution=STANDARD_MATING_PARENT_ENERGY_CONTRIBUTION,
        mutation_rate=STANDARD_MATING_MUTATION_RATE,
        mutation_strength=STANDARD_MATING_MUTATION_STRENGTH,
    )
    spawned = 0
    used: set[int] = set()
    sorted_fish = sorted(fish_list, key=_fish_sort_key)

    for parent in sorted_fish:
        if parent.fish_id in used or not _can_try_standard_mating(parent, config):
            continue
        if ecosystem is not None and not ecosystem.can_reproduce(fish_count):
            break

        mate = _find_proximity_mate(parent, sorted_fish, used, config)
        if mate is None:
            continue
        if required_credits > 0 and (
            not parent._reproduction_component.has_repro_credits(required_credits)
            or not mate._reproduction_component.has_repro_credits(required_credits)
        ):
            continue

        mutation_context = mutation_context_provider(parent, mate)
        baby = create_standard_mating_offspring(parent, mate, engine, config, mutation_context)
        if baby is None:
            continue

        if engine.request_spawn(baby, reason="proximity_mating"):
            baby.register_birth()
            lifecycle_system = engine.lifecycle_system
            if lifecycle_system is not None:
                lifecycle_system.record_birth()
            if required_credits > 0:
                parent._reproduction_component.consume_repro_credits(required_credits)
                mate._reproduction_component.consume_repro_credits(required_credits)
            used.add(parent.fish_id)
            used.add(mate.fish_id)
            spawned += 1
            fish_count += 1

    return spawned


def create_standard_mating_offspring(
    parent: Fish,
    mate: Fish,
    engine: SimulationEngine,
    config: ProximityMatingConfig,
    mutation_context: ReproductionMutationContext,
) -> Fish | None:
    """Create a 50/50 proximity-mating offspring with local energy costs."""
    from core.config.fish import ENERGY_MAX_DEFAULT, FISH_BABY_SIZE, FISH_BASE_SPEED
    from core.entities import Fish
    from core.genetics import Genome

    if parent.environment is None:
        return None

    offspring_genome = Genome.from_parents(
        parent1=parent.genome,
        parent2=mate.genome,
        mutation_rate=config.mutation_rate,
        mutation_strength=config.mutation_strength,
        rng=engine.rng,
        mutation_context=mutation_context,
        parent1_dominant=parent.energy >= mate.energy,
    )

    _mutate_code_policies(parent, offspring_genome, engine)

    # Use standard size_modifier=1.0 for newborn energy calculation (Fair-Start)
    newborn_energy_target = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * 1.0

    parent_contrib = newborn_energy_target * config.parent_energy_contribution
    mate_contrib = newborn_energy_target * config.parent_energy_contribution
    if parent.energy < parent_contrib or mate.energy < mate_contrib:
        return None

    apply_energy_delta(parent, -parent_contrib, source="proximity_mating")
    apply_energy_delta(mate, -mate_contrib, source="proximity_mating")

    cooldown = parent._reproduction_component.REPRODUCTION_COOLDOWN
    parent._reproduction_component.reproduction_cooldown = max(
        parent._reproduction_component.reproduction_cooldown,
        cooldown,
    )
    mate._reproduction_component.reproduction_cooldown = max(
        mate._reproduction_component.reproduction_cooldown,
        cooldown,
    )

    baby_x, baby_y = _offspring_position(parent, mate, engine, jitter=30.0)
    baby = Fish(
        environment=parent.environment,
        movement_strategy=parent.movement_strategy.__class__(),
        species=parent.species,
        x=baby_x,
        y=baby_y,
        speed=FISH_BASE_SPEED,
        genome=offspring_genome,
        generation=max(parent.generation, mate.generation) + 1,
        ecosystem=parent.ecosystem,
        initial_energy=parent_contrib + mate_contrib,
        parent_id=parent.fish_id,
    )

    _record_successful_mating(parent)
    parent.visual_state.set_birth_effect(60)
    mate.visual_state.set_birth_effect(60)
    return baby


def create_post_poker_offspring(
    winner: Fish,
    mate: Fish,
    engine: SimulationEngine,
    mutation_context: ReproductionMutationContext,
) -> Fish | None:
    """Create a post-poker offspring while preserving legacy RNG behavior."""
    from core.config.fish import (
        ENERGY_MAX_DEFAULT,
        FISH_BABY_SIZE,
        FISH_BASE_SPEED,
        POST_POKER_CROSSOVER_WINNER_WEIGHT,
        POST_POKER_MUTATION_RATE,
        POST_POKER_MUTATION_STRENGTH,
        POST_POKER_PARENT_ENERGY_CONTRIBUTION,
        REPRODUCTION_COOLDOWN,
    )
    from core.entities import Fish
    from core.genetics import Genome, ReproductionParams

    if winner.environment is None:
        return None

    offspring_genome = Genome.from_parents_weighted_params(
        parent1=winner.genome,
        parent2=mate.genome,
        parent1_weight=POST_POKER_CROSSOVER_WINNER_WEIGHT,
        params=ReproductionParams(
            mutation_rate=POST_POKER_MUTATION_RATE,
            mutation_strength=POST_POKER_MUTATION_STRENGTH,
        ),
        rng=engine.rng,
        mutation_context=mutation_context,
    )

    _mutate_code_policies(winner, offspring_genome, engine)

    # Use standard size_modifier=1.0 for newborn energy calculation (Fair-Start)
    newborn_energy_target = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * 1.0

    winner_contrib = max(0.0, winner.energy * POST_POKER_PARENT_ENERGY_CONTRIBUTION)
    mate_contrib = max(0.0, mate.energy * POST_POKER_PARENT_ENERGY_CONTRIBUTION)
    total_contrib = winner_contrib + mate_contrib
    if total_contrib <= 0:
        return None

    if total_contrib > newborn_energy_target:
        scale = newborn_energy_target / total_contrib
        winner_contrib *= scale
        mate_contrib *= scale
        total_contrib = newborn_energy_target

    apply_energy_delta(winner, -winner_contrib, source="post_poker_reproduction")
    apply_energy_delta(mate, -mate_contrib, source="post_poker_reproduction")

    winner._reproduction_component.reproduction_cooldown = max(
        winner._reproduction_component.reproduction_cooldown,
        REPRODUCTION_COOLDOWN,
    )
    mate._reproduction_component.reproduction_cooldown = max(
        mate._reproduction_component.reproduction_cooldown,
        REPRODUCTION_COOLDOWN,
    )

    baby_x, baby_y = _offspring_position(winner, mate, engine, jitter=30.0)
    baby = Fish(
        environment=winner.environment,
        movement_strategy=winner.movement_strategy.__class__(),
        species=winner.species,
        x=baby_x,
        y=baby_y,
        speed=FISH_BASE_SPEED,
        genome=offspring_genome,
        generation=max(winner.generation, mate.generation) + 1,
        ecosystem=winner.ecosystem,
        initial_energy=total_contrib,
        parent_id=winner.fish_id,
    )

    _record_successful_mating(winner)
    winner.visual_state.set_birth_effect(60)
    mate.visual_state.set_birth_effect(60)

    # Determinism anchor: post-poker reproduction has always drawn one engine
    # RNG value here (it picked which parent's learned state the offspring
    # inherited). That inherited state has been removed, but dropping the draw
    # would reshuffle the shared seeded stream for every poker-on config and
    # trip the golden-replay/benchmark guards. Retain the draw so this removal
    # stays byte-identical; drop it via a coordinated re-record when this path
    # is next intentionally changed.
    engine.rng.random()

    return baby


def _can_try_standard_mating(fish: Fish, config: ProximityMatingConfig) -> bool:
    from core.entities.base import LifeStage

    if hasattr(fish, "is_dead") and fish.is_dead():
        return False
    if fish.life_stage != LifeStage.ADULT:
        return False
    if fish._reproduction_component.reproduction_cooldown > 0:
        return False
    return fish.energy >= fish.max_energy * config.min_energy_ratio


def _find_proximity_mate(
    parent: Fish,
    fish_list: list[Fish],
    used: set[int],
    config: ProximityMatingConfig,
) -> Fish | None:
    max_dist_sq = config.max_distance * config.max_distance
    candidates: list[tuple[float, float, int, Fish]] = []

    for mate in fish_list:
        if mate is parent or mate.fish_id in used:
            continue
        if mate.species != parent.species or not _can_try_standard_mating(mate, config):
            continue
        dist_sq = _distance_sq(parent, mate)
        if dist_sq <= max_dist_sq:
            attraction = parent.genome.calculate_mate_attraction(mate.genome)
            candidates.append((attraction, dist_sq, mate.fish_id, mate))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return candidates[0][3]


def _mutate_code_policies(parent: Fish, offspring_genome, engine: SimulationEngine) -> None:
    pool = getattr(parent.environment, "genome_code_pool", None)
    if pool is None:
        return

    from core.genetics.code_policy_traits import (
        mutate_code_policies,
        validate_code_policy_ids,
    )

    mutate_code_policies(offspring_genome.behavioral, pool, engine.rng)
    validate_code_policy_ids(offspring_genome.behavioral, pool, engine.rng)


def _record_successful_mating(parent: Fish) -> None:
    if parent.ecosystem is None:
        return
    composable = parent.genome.behavioral.behavior
    if composable is not None and composable.value is not None:
        behavior_id = composable.value.behavior_id
        algorithm_id = stable_algorithm_id(behavior_id)
        parent.ecosystem.record_reproduction(algorithm_id, is_asexual=False)
    parent.ecosystem.record_mating_attempt(True)


def _offspring_position(
    parent: Fish,
    mate: Fish,
    engine: SimulationEngine,
    *,
    jitter: float,
) -> tuple[float, float]:
    (min_x, min_y), (max_x, max_y) = parent.environment.get_bounds()
    mid_x = (parent.pos.x + mate.pos.x) * 0.5
    mid_y = (parent.pos.y + mate.pos.y) * 0.5
    baby_x = mid_x + engine.rng.uniform(-jitter, jitter)
    baby_y = mid_y + engine.rng.uniform(-jitter, jitter)
    baby_x = max(min_x, min(max_x - 50, baby_x))
    baby_y = max(min_y, min(max_y - 50, baby_y))
    return baby_x, baby_y


def _distance_sq(a: Fish, b: Fish) -> float:
    ax, ay = _center(a)
    bx, by = _center(b)
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def _center(fish: Fish) -> tuple[float, float]:
    return fish.pos.x + fish.width * 0.5, fish.pos.y + fish.height * 0.5


def _fish_sort_key(fish: Fish) -> int:
    return fish.fish_id
