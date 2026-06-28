"""Reproduction mixin for Fish entities.

Encapsulates reproduction eligibility, offspring creation, and mating logic.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.agents.components.reproduction_component import ReproductionComponent
    from core.ecosystem import EcosystemManager
    from core.entities.fish import Fish
    from core.entities.visual_state import FishVisualState
    from core.genetics import Genome
    from core.math_utils import Vector2
    from core.movement_strategy import MovementStrategy
    from core.world import World

logger = logging.getLogger(__name__)


class ReproductionMixin:
    """Fish-only reproduction *policy* layered over ``ReproductionComponent``.

    Holds offspring creation (via ``ReproductionService``) and the
    protocol-facing API; the component owns reproduction state (credits,
    cooldown) and the eligibility rule this delegates to. Not a reusable
    mixin. See ADR-013.

    Expects the host class to have:
        _reproduction_component: ReproductionComponent
        _lifecycle_component: LifecycleComponent
        _energy_component: EnergyComponent
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

    _reproduction_component: ReproductionComponent
    _lifecycle_component: LifecycleComponent
    _emit_event: Callable[[object], None]
    genome: Genome
    environment: World
    ecosystem: EcosystemManager | None
    fish_id: int
    generation: int
    species: str
    movement_strategy: MovementStrategy
    energy: float
    pos: Vector2
    visual_state: FishVisualState

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce (delegates to ReproductionComponent)."""
        return self._reproduction_component.can_reproduce(
            self._lifecycle_component.life_stage,
            self.energy,
            self.max_energy,  # type: ignore[attr-defined]  # provided by EnergyManagementMixin
        )

    def try_mate(self, other: Fish) -> bool:
        """Return whether this fish can standard-mate with another fish.

        Offspring creation is centralized in ReproductionService; this method
        preserves the protocol-facing eligibility check.
        """
        from core.config.fish import STANDARD_MATING_DISTANCE, STANDARD_MATING_MIN_ENERGY_RATIO
        from core.entities.base import LifeStage

        if other is self or other.species != self.species:
            return False
        if hasattr(self, "is_dead") and self.is_dead():
            return False
        if hasattr(other, "is_dead") and other.is_dead():
            return False
        if self.life_stage != LifeStage.ADULT or other.life_stage != LifeStage.ADULT:
            return False
        if (
            self._reproduction_component.reproduction_cooldown > 0
            or other._reproduction_component.reproduction_cooldown > 0
        ):
            return False
        if self.energy < self.max_energy * STANDARD_MATING_MIN_ENERGY_RATIO:
            return False
        if other.energy < other.max_energy * STANDARD_MATING_MIN_ENERGY_RATIO:
            return False

        dx = (self.pos.x + self.width * 0.5) - (other.pos.x + other.width * 0.5)
        dy = (self.pos.y + self.height * 0.5) - (other.pos.y + other.height * 0.5)
        return dx * dx + dy * dy <= STANDARD_MATING_DISTANCE * STANDARD_MATING_DISTANCE

    def update_reproduction(self) -> Fish | None:
        """Update reproduction state and potentially create offspring.

        Updates cooldown timer and checks if conditions are met for instant
        asexual reproduction (overflow energy banked + eligible).

        Returns:
            Newborn fish if reproduction occurred, None otherwise
        """
        from core.reproduction.reproduction_service import ReproductionService

        self._reproduction_component.update_cooldown()
        return ReproductionService.maybe_create_banked_offspring(cast("Fish", self))

    def _create_asexual_offspring(self, mutation_context=None) -> Fish | None:
        """Create an offspring through asexual reproduction.

        Called when conditions are met for instant asexual reproduction.

        Returns:
            The newly created baby fish, or None if creation failed
        """
        from typing import cast

        from core.reproduction.reproduction_service import ReproductionService

        return ReproductionService.create_asexual_offspring(
            cast("Fish", self), mutation_context=mutation_context
        )
