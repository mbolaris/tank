"""Migration component for plants.

This module provides the PlantMigrationComponent class which handles
plant migration between connected tanks.
"""

import logging
from typing import TYPE_CHECKING, Callable, Optional

from core.state_machine import EntityState

if TYPE_CHECKING:
    from core.root_spots import RootSpot
    from core.world import World

logger = logging.getLogger(__name__)


class PlantMigrationComponent:
    """Manages plant migration between connected tanks.

    This component encapsulates migration logic, including:
    - Migration timer management
    - Edge position detection
    - Migration probability calculation
    - Delegation to migration handler

    Attributes:
        migration_timer: Frames until next migration check.
        migration_check_interval: Frames between migration checks.
    """

    __slots__ = (
        "migration_timer",
        "migration_check_interval",
        "_get_root_spot",
        "_get_environment",
        "_transition_state",
        "_plant_id",
    )

    def __init__(
        self,
        plant_id: int,
        get_root_spot: Callable[[], Optional["RootSpot"]],
        get_environment: Callable[[], "World"],
        transition_state: Callable[[EntityState, str], None],
        rng,
    ) -> None:
        """Initialize the migration component.

        Args:
            plant_id: The plant's unique identifier.
            get_root_spot: Callback to get the plant's root spot.
            get_environment: Callback to get the environment.
            transition_state: Callback to transition entity state.
            rng: Random number generator for deterministic behavior.
        """
        self.migration_check_interval = 300  # Check every 5 seconds at 60fps
        # Add random offset to prevent synchronized migrations
        if rng is None:
            raise RuntimeError("rng is required for deterministic plant initialization")
        self.migration_timer = rng.randint(0, self.migration_check_interval)
        self._get_root_spot = get_root_spot
        self._get_environment = get_environment
        self._transition_state = transition_state
        self._plant_id = plant_id

    def update(self) -> bool:
        """Update migration timer and check for migration.

        Returns:
            True if migration was attempted (success or failure).
        """
        self.migration_timer += 1
        if self.migration_timer >= self.migration_check_interval:
            self.migration_timer = 0
            return self._check_migration()
        return False

    def _check_migration(self) -> bool:
        """Check if plant should attempt migration based on root spot position.

        Returns:
            True if migration was attempted.
        """
        root_spot = self._get_root_spot()
        if root_spot is None:
            return False

        # Determine if this plant is in an edge position
        # Edge positions are the first 2 or last 2 spots out of 25
        total_spots = len(root_spot.manager.spots) if hasattr(root_spot, "manager") else 25
        edge_threshold = 2  # Consider first 2 and last 2 spots as "edge"

        spot_id = root_spot.spot_id
        direction = None

        if spot_id < edge_threshold:
            # Leftmost positions - can migrate left
            direction = "left"
        elif spot_id >= total_spots - edge_threshold:
            # Rightmost positions - can migrate right
            direction = "right"

        if direction is not None:
            # Attempt migration with a probability (20% per check)
            env = self._get_environment()
            rng = getattr(env, "rng", None)
            if rng is None:
                raise RuntimeError("environment.rng is required for deterministic migration")
            if rng.random() < 0.20:
                return self._attempt_migration(direction)

        return False

    def _attempt_migration(self, direction: str) -> bool:
        """Attempt to migrate to a connected tank.

        Uses dependency injection pattern - delegates to environment's migration
        handler if available. This keeps core entities decoupled from backend.

        Args:
            direction: "left" or "right" - which edge this plant is on.

        Returns:
            True if migration successful, False otherwise.
        """
        env = self._get_environment()
        migration_handler = getattr(env, "migration_handler", None)
        if migration_handler is None:
            return False

        world_id = getattr(env, "world_id", None)
        if world_id is None:
            return False

        # We need a reference to the Plant entity for migration
        # The migration handler expects the full entity
        # This is handled by the Plant class which calls this component
        return False  # Return False here; actual migration handled by Plant

    def execute_migration(self, plant, direction: str) -> bool:
        """Execute migration for the given plant entity.

        This method is called by the Plant class with a reference to itself.

        Args:
            plant: The Plant entity to migrate.
            direction: "left" or "right".

        Returns:
            True if migration successful.
        """
        env = self._get_environment()
        migration_handler = getattr(env, "migration_handler", None)
        if migration_handler is None:
            return False

        world_id = getattr(env, "world_id", None)
        if world_id is None:
            return False

        try:
            success = migration_handler.attempt_entity_migration(plant, direction, world_id)

            if success:
                # Mark this plant for removal from source tank
                self._transition_state(EntityState.REMOVED, "migration")
                logger.debug(f"Plant #{self._plant_id} successfully migrated {direction}")

            return success

        except Exception as e:
            logger.error(f"Plant migration failed: {e}", exc_info=True)
            return False
