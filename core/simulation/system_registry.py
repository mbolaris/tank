"""System registration and management.

This module manages simulation systems - their registration, lifecycle,
and debugging. Extracted from SimulationEngine to follow SRP.

Design Decisions:
-----------------
1. Systems are registered in a specific order which determines execution order.
   The order is controlled by the caller at registration time.

2. Systems can be enabled/disabled at runtime without removal.

3. Debug info is aggregated from all systems for observability.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.systems.base import BaseSystem

logger = logging.getLogger(__name__)


class SystemRegistry:
    """Registers and manages simulation systems.

    Systems are the workhorses of the simulation - they contain the logic
    that operates on entities each frame. This registry:
    - Maintains systems in execution order
    - Provides runtime enable/disable
    - Aggregates debug information

    Attributes:
        systems: List of registered systems in execution order

    Example:
        registry = SystemRegistry()
        registry.register(collision_system)
        registry.register(reproduction_system)

        for system in registry.get_all():
            system.update(frame)

        registry.set_enabled("Collision", False)  # Disable collisions
    """

    def __init__(self) -> None:
        """Initialize an empty system registry."""
        self._systems: List["BaseSystem"] = []

    def register(self, system: "BaseSystem") -> None:
        """Register a system for execution.

        Systems are executed in registration order.

        Args:
            system: The system to register
        """
        self._systems.append(system)
        logger.debug(f"Registered system: {system.name}")

    def unregister(self, system: "BaseSystem") -> bool:
        """Remove a system from the registry.

        Args:
            system: The system to remove

        Returns:
            True if system was found and removed, False otherwise
        """
        if system in self._systems:
            self._systems.remove(system)
            logger.debug(f"Unregistered system: {system.name}")
            return True
        return False

    def get(self, name: str) -> Optional["BaseSystem"]:
        """Get a system by name.

        Args:
            name: The name of the system to retrieve

        Returns:
            The system if found, None otherwise
        """
        for system in self._systems:
            if system.name == name:
                return system
        return None

    def get_all(self) -> List["BaseSystem"]:
        """Get all registered systems in execution order.

        Returns:
            List of registered systems (copy to prevent mutation)
        """
        return self._systems.copy()

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a system by name.

        Args:
            name: The name of the system
            enabled: Whether the system should be enabled

        Returns:
            True if system was found and updated, False otherwise
        """
        system = self.get(name)
        if system is not None:
            system.enabled = enabled
            logger.debug(f"System {name} enabled={enabled}")
            return True
        return False

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information from all registered systems.

        Returns:
            Dictionary mapping system names to their debug info
        """
        return {
            system.name: system.get_debug_info()
            for system in self._systems
        }

    def __len__(self) -> int:
        """Get the number of registered systems."""
        return len(self._systems)

    def __iter__(self):
        """Iterate over systems in execution order."""
        return iter(self._systems)

    def __repr__(self) -> str:
        system_names = [s.name for s in self._systems]
        return f"SystemRegistry(systems={system_names})"
