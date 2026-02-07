"""Mortality mixin for Fish entities.

Encapsulates death detection, cause attribution, and predator tracking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.config.fish import PREDATOR_ENCOUNTER_WINDOW
from core.constants import (DEATH_REASON_MIGRATION, DEATH_REASON_OLD_AGE,
                            DEATH_REASON_STARVATION)
from core.entities.base import EntityState

if TYPE_CHECKING:
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.state_machine import StateMachine
    from core.world import World

logger = logging.getLogger(__name__)


class MortalityMixin:
    """Mixin providing death detection and cause attribution for Fish entities.

    Expects the host class to have:
        _energy_component: EnergyComponent
        _lifecycle_component: LifecycleComponent
        _cached_is_dead: bool
        state: EntityStateMachine
        last_predator_encounter_age: int
        environment: World
        fish_id: int
    """

    _cached_is_dead: bool
    _lifecycle_component: LifecycleComponent
    state: StateMachine[EntityState]
    energy: float
    last_predator_encounter_age: int
    environment: World
    fish_id: int

    def is_dead(self) -> bool:
        """Check if fish should die or has migrated.

        Uses cached dead state when possible to avoid repeated checks.
        """
        if self._cached_is_dead:
            return True

        if self.state.state in (EntityState.DEAD, EntityState.REMOVED):
            self._cached_is_dead = True
            return True

        if self.energy <= 0:
            self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
            self._cached_is_dead = True
            return True

        if self._lifecycle_component.age >= self._lifecycle_component.max_age:
            self.state.transition(EntityState.DEAD, reason=DEATH_REASON_OLD_AGE)
            self._cached_is_dead = True
            return True

        return False

    def get_death_cause(self) -> str:
        """Determine the cause of death.

        Checks state history first for explicit causes, then infers from state.

        Returns:
            Cause of death ('starvation', 'old_age', 'predation', 'migration')
        """
        history = self.state.history
        if history:
            last_transition = history[-1]
            if last_transition.to_state in (EntityState.DEAD, EntityState.REMOVED):
                reason = last_transition.reason
                if "migration" in reason:
                    return "migration"
                if "starvation" in reason:
                    if (
                        self._lifecycle_component.age - self.last_predator_encounter_age
                        <= PREDATOR_ENCOUNTER_WINDOW
                    ):
                        return "predation"
                    return "starvation"
                if "old_age" in reason:
                    return "old_age"
                if "predation" in reason:
                    return "predation"

        if self.state.state == EntityState.REMOVED:
            return "migration"

        if self.energy <= 0:
            if (
                self._lifecycle_component.age - self.last_predator_encounter_age
                <= PREDATOR_ENCOUNTER_WINDOW
            ):
                return "predation"
            else:
                return "starvation"
        elif self._lifecycle_component.age >= self._lifecycle_component.max_age:
            return "old_age"

        # Debug unknown causes
        parts = []
        if self.state.state == EntityState.ACTIVE:
            parts.append("active")
        if self.state.state == EntityState.DEAD:
            parts.append("dead")
        if self.energy > 0:
            parts.append("pos_energy")
        if not history:
            parts.append("no_hist")
        else:
            parts.append(f"last_rsn_{history[-1].reason}")

        return f"unknown_{'_'.join(parts)}"

    def mark_predator_encounter(self, escaped: bool = False, damage_taken: float = 0.0) -> None:
        """Mark that this fish has encountered a predator.

        Used for death attribution - if the fish dies from energy depletion
        shortly after this encounter, it counts as predation.
        """
        self.last_predator_encounter_age = self._lifecycle_component.age

    def can_attempt_migration(self) -> bool:
        """Fish can migrate when hitting horizontal tank boundaries."""
        return True

    def _attempt_migration(self, direction: str) -> bool:
        """Attempt to migrate to a connected tank when hitting a boundary.

        Uses the MigrationCapable protocol to check if migration is supported.

        Args:
            direction: "left" or "right" - which boundary was hit

        Returns:
            True if migration successful, False if not supported or failed
        """
        from core.interfaces import MigrationCapable

        if not isinstance(self.environment, MigrationCapable):
            return False

        migration_handler = self.environment.migration_handler
        if migration_handler is None:
            return False

        world_id = self.environment.world_id
        if world_id is None:
            return False

        try:
            success = migration_handler.attempt_entity_migration(self, direction, world_id)
            if success:
                self.state.transition(EntityState.REMOVED, reason=DEATH_REASON_MIGRATION)
                logger.debug(f"Fish #{self.fish_id} successfully migrated {direction}")
            return success
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False
