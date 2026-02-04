"""Reproduction mixin for Fish entities.

Encapsulates reproduction eligibility, offspring creation, and mating logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.config.fish import ENERGY_MAX_DEFAULT, FISH_BASE_SPEED
from core.entities.base import LifeStage
from core.telemetry.events import ReproductionEvent

if TYPE_CHECKING:
    from core.entities.fish import Fish

logger = logging.getLogger(__name__)


class ReproductionMixin:
    """Mixin providing reproduction behavior for Fish entities.

    Expects the host class to have:
        _reproduction_component: ReproductionComponent
        _lifecycle_component: LifecycleComponent
        _energy_component: EnergyComponent
        _skill_game_component: SkillGameComponent
        genome: Genome
        environment: World
        ecosystem: EcosystemManager
        fish_id: int
        generation: int
        species: str
        movement_strategy: MovementStrategy
        energy: float
        max_energy: float
        visual_state: FishVisualState
        _emit_event: Callable
    """

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce (delegates to ReproductionComponent)."""
        return self._reproduction_component.can_reproduce(
            self._lifecycle_component.life_stage,
            self.energy,
            self.max_energy,
        )

    def try_mate(self, other: "Fish") -> bool:
        """Attempt to mate with another fish.

        Standard mating is disabled; fish only reproduce sexually after poker games.
        """
        return False

    def update_reproduction(self) -> "Fish | None":
        """Update reproduction state and potentially create offspring.

        Updates cooldown timer and checks if conditions are met for instant
        asexual reproduction (overflow energy banked + eligible).

        Returns:
            Newborn fish if reproduction occurred, None otherwise
        """
        from core.reproduction_service import ReproductionService

        self._reproduction_component.update_cooldown()
        return ReproductionService.maybe_create_banked_offspring(self)

    def _create_asexual_offspring(self) -> "Fish | None":
        """Create an offspring through asexual reproduction.

        Called when conditions are met for instant asexual reproduction.

        Returns:
            The newly created baby fish, or None if creation failed
        """
        from core.entities.fish import Fish
        from core.util.rng import require_rng

        rng = require_rng(self.environment, "Fish._create_asexual_offspring")

        # Get available policies for mutation
        available_policies = self.environment.list_policy_component_ids("movement_policy")
        if not available_policies:
            available_policies = None

        # Generate offspring genome (also sets cooldown)
        (
            offspring_genome,
            _unused_fraction,
        ) = self._reproduction_component.trigger_asexual_reproduction(
            self.genome, rng=rng, available_policies=available_policies
        )

        # Calculate baby's max energy capacity
        from core.config.fish import FISH_BABY_SIZE

        baby_max_energy = (
            ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * offspring_genome.physical.size_modifier.value
        )

        # Use banked overflow energy first, then draw from parent
        bank_used = self._reproduction_component.consume_overflow_energy_bank(baby_max_energy)
        remaining_needed = baby_max_energy - bank_used
        parent_transfer = min(self.energy, remaining_needed)

        self.energy -= parent_transfer
        baby_initial_energy = bank_used + parent_transfer

        # Create offspring near parent
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        offset_x = rng.uniform(-30, 30)
        offset_y = rng.uniform(-30, 30)
        baby_x = max(min_x, min(max_x - 50, self.pos.x + offset_x))
        baby_y = max(min_y, min(max_y - 50, self.pos.y + offset_y))

        baby = Fish(
            environment=self.environment,
            movement_strategy=self.movement_strategy.__class__(),
            species=self.species,
            x=baby_x,
            y=baby_y,
            speed=FISH_BASE_SPEED,
            genome=offspring_genome,
            generation=self.generation + 1,
            ecosystem=self.ecosystem,
            initial_energy=baby_initial_energy,
            parent_id=self.fish_id,
        )

        # Record reproduction stats
        composable = self.genome.behavioral.behavior
        if composable is not None and composable.value is not None:
            behavior_id = composable.value.behavior_id
            algorithm_id = hash(behavior_id) % 1000
            self._emit_event(ReproductionEvent(algorithm_id, is_asexual=True))

        # Inherit skill game strategies from parent with mutation
        baby._skill_game_component.inherit_from_parent(
            self._skill_game_component,
            mutation_rate=0.1,
            rng=rng,
        )

        # Set visual birth effect timer
        self.visual_state.set_birth_effect(60)

        return baby
