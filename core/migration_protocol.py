"""Migration protocol for entity transfers between environments.

This protocol defines the interface for migration functionality without
coupling core to backend implementation details.
"""

from typing import Protocol, Optional, Any


class MigrationHandler(Protocol):
    """Protocol for handling entity migrations between tanks.

    This allows core entities to request migration without depending on
    backend implementation details.
    """

    def attempt_entity_migration(
        self, entity: Any, direction: str, source_tank_id: str
    ) -> bool:
        """Attempt to migrate an entity to a connected tank.

        Args:
            entity: The entity attempting to migrate
            direction: "left" or "right" - which boundary was hit
            source_tank_id: ID of the source tank

        Returns:
            True if migration successful, False otherwise
        """
        ...
