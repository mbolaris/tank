"""Tank registry for managing multiple tank simulations.

This module provides the TankRegistry class which manages multiple
SimulationManager instances for Tank World Net. It supports creating,
listing, accessing, and removing tanks.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.simulation_manager import SimulationManager, TankInfo

logger = logging.getLogger(__name__)


@dataclass
class CreateTankRequest:
    """Request to create a new tank."""

    name: str
    description: str = ""
    seed: Optional[int] = None
    owner: Optional[str] = None
    is_public: bool = True
    allow_transfers: bool = False


class TankRegistry:
    """Registry for managing multiple tank simulations.

    This class provides a centralized way to manage multiple SimulationManager
    instances. Each tank is identified by a unique tank_id and can be accessed,
    listed, or removed through this registry.

    The registry supports:
    - Creating new tanks with custom configurations
    - Listing all tanks (optionally filtered by public visibility)
    - Accessing individual tanks by ID
    - Removing tanks and cleaning up their resources
    - Getting a default tank for backwards compatibility
    """

    def __init__(self, create_default: bool = True):
        """Initialize the tank registry.

        Args:
            create_default: If True, creates a default "Local Tank" on init
        """
        self._tanks: Dict[str, SimulationManager] = {}
        self._default_tank_id: Optional[str] = None
        self._lock = asyncio.Lock()

        if create_default:
            default_tank = self.create_tank(
                name="Local Tank",
                description="A local fish tank simulation",
            )
            self._default_tank_id = default_tank.tank_id
            logger.info(
                "TankRegistry initialized with default tank: %s",
                self._default_tank_id,
            )
        else:
            logger.info("TankRegistry initialized (no default tank)")

    @property
    def tank_count(self) -> int:
        """Get the number of tanks in the registry."""
        return len(self._tanks)

    @property
    def default_tank_id(self) -> Optional[str]:
        """Get the default tank ID."""
        return self._default_tank_id

    @property
    def default_tank(self) -> Optional[SimulationManager]:
        """Get the default tank manager."""
        if self._default_tank_id:
            return self._tanks.get(self._default_tank_id)
        return None

    def create_tank(
        self,
        name: str,
        description: str = "",
        seed: Optional[int] = None,
        owner: Optional[str] = None,
        is_public: bool = True,
        allow_transfers: bool = False,
    ) -> SimulationManager:
        """Create a new tank and add it to the registry.

        Args:
            name: Human-readable name for the tank
            description: Description of the tank
            seed: Optional random seed for deterministic behavior
            owner: Optional owner identifier
            is_public: Whether the tank is publicly visible
            allow_transfers: Whether to allow entity transfers

        Returns:
            The newly created SimulationManager
        """
        manager = SimulationManager(
            tank_name=name,
            tank_description=description,
            seed=seed,
        )

        # Update tank info with additional fields
        manager.tank_info.owner = owner
        manager.tank_info.is_public = is_public
        manager.tank_info.allow_transfers = allow_transfers

        self._tanks[manager.tank_id] = manager

        logger.info(
            "Created tank: id=%s, name=%s, owner=%s, public=%s",
            manager.tank_id,
            name,
            owner,
            is_public,
        )

        return manager

    def get_tank(self, tank_id: str) -> Optional[SimulationManager]:
        """Get a tank by its ID.

        Args:
            tank_id: The unique tank identifier

        Returns:
            The SimulationManager if found, None otherwise
        """
        return self._tanks.get(tank_id)

    def get_tank_or_default(self, tank_id: Optional[str] = None) -> Optional[SimulationManager]:
        """Get a tank by ID, or return the default tank.

        Args:
            tank_id: Optional tank ID. If None or not found, returns default.

        Returns:
            The SimulationManager for the specified or default tank
        """
        if tank_id:
            tank = self._tanks.get(tank_id)
            if tank:
                return tank
        return self.default_tank

    def list_tanks(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """List all tanks in the registry.

        Args:
            include_private: If True, include non-public tanks

        Returns:
            List of tank status dictionaries
        """
        tanks = []
        for manager in self._tanks.values():
            if include_private or manager.tank_info.is_public:
                tanks.append(manager.get_status())
        return tanks

    def list_tank_ids(self) -> List[str]:
        """Get a list of all tank IDs.

        Returns:
            List of tank IDs
        """
        return list(self._tanks.keys())

    def remove_tank(self, tank_id: str) -> bool:
        """Remove a tank from the registry and clean up resources.

        Args:
            tank_id: The tank ID to remove

        Returns:
            True if the tank was removed, False if not found
        """
        manager = self._tanks.pop(tank_id, None)
        if manager is None:
            logger.warning("Attempted to remove non-existent tank: %s", tank_id)
            return False

        # Stop the simulation if running
        if manager.running:
            manager.stop()

        # Clear the default tank reference if needed
        if self._default_tank_id == tank_id:
            self._default_tank_id = None
            # Set a new default if other tanks exist
            if self._tanks:
                self._default_tank_id = next(iter(self._tanks.keys()))
                logger.info("New default tank: %s", self._default_tank_id)

        logger.info("Removed tank: %s", tank_id)
        return True

    def start_all(self, start_paused: bool = False) -> None:
        """Start all tanks in the registry.

        Args:
            start_paused: Whether to start tanks in paused state
        """
        for manager in self._tanks.values():
            if not manager.running:
                manager.start(start_paused=start_paused)

    def stop_all(self) -> None:
        """Stop all tanks in the registry."""
        for manager in self._tanks.values():
            if manager.running:
                manager.stop()

    def __contains__(self, tank_id: str) -> bool:
        """Check if a tank ID exists in the registry."""
        return tank_id in self._tanks

    def __len__(self) -> int:
        """Get the number of tanks."""
        return len(self._tanks)

    def __iter__(self):
        """Iterate over tank managers."""
        return iter(self._tanks.values())
