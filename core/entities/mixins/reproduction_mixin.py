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
    from core.fish.skill_game_component import SkillGameComponent
    from core.genetics import Genome
    from core.math_utils import Vector2
    from core.movement_strategy import MovementStrategy
    from core.world import World

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

    _reproduction_component: ReproductionComponent
    _lifecycle_component: LifecycleComponent
    _skill_game_component: SkillGameComponent
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
        """Attempt to mate with another fish.

        Standard mating is disabled; fish only reproduce sexually after poker games.
        """
        return False

    def update_reproduction(self) -> Fish | None:
        """Update reproduction state and potentially create offspring.

        Updates cooldown timer and checks if conditions are met for instant
        asexual reproduction (overflow energy banked + eligible).

        Returns:
            Newborn fish if reproduction occurred, None otherwise
        """
        from core.reproduction_service import ReproductionService

        self._reproduction_component.update_cooldown()
        return ReproductionService.maybe_create_banked_offspring(cast("Fish", self))

    def _create_asexual_offspring(self) -> Fish | None:
        """Create an offspring through asexual reproduction.

        Called when conditions are met for instant asexual reproduction.

        Returns:
            The newly created baby fish, or None if creation failed
        """
        from core.reproduction_service import ReproductionService
        from typing import cast

        return ReproductionService.create_asexual_offspring(cast("Fish", self))
