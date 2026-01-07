"""TankWorld: Legacy wrapper around the fish tank simulation.

DEPRECATED: This module is deprecated. Use core.worlds.WorldRegistry instead.

This module provides a TankWorld class that encapsulates the entire simulation,
including configuration and random number generation, making it easy to:
- Run deterministic simulations with seeded RNG
- Override configuration parameters
- Interface with both headless and web backends
"""

import warnings

warnings.warn(
    "core.tank_world / core.legacy.tank_world is deprecated. "
    "Use core.worlds.WorldRegistry.create_world('tank', ...) instead.",
    DeprecationWarning,
    stacklevel=2,
)

import logging
import random
from typing import Any, Dict, List, Optional

from core.config.simulation_config import SimulationConfig

logger = logging.getLogger(__name__)


class TankWorld:
    """Main simulation wrapper that encapsulates all global state.

    This class wraps the entire simulation and provides a clean interface
    for both headless and web backends. All configuration and randomness
    is managed through this class.

    Attributes:
        simulation_config: Simulation configuration
        rng: Random number generator for deterministic behavior
        engine: The underlying simulation engine
    """

    def __init__(
        self,
        simulation_config: Optional[SimulationConfig] = None,
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
        pack: Optional["SystemPack"] = None,
    ):
        """Initialize TankWorld.

        Args:
            simulation_config: Aggregate SimulationConfig (uses defaults if None)
            rng: Random number generator instance (creates new if None)
            seed: Random seed (only used if rng is None)
            pack: Optional custom SystemPack (defaults to TankPack)
        """
        # Store configuration
        self.simulation_config = simulation_config or SimulationConfig.production(headless=True)

        # Setup RNG
        if rng is not None:
            self.rng = rng
        elif seed is not None:
            self.rng = random.Random(seed)
            logger.info(f"TankWorld initialized with seed: {seed}")
        else:
            self.rng = random.Random()

        # Import here to avoid circular dependencies
        from core.simulation import SimulationEngine
        from core.worlds.tank.pack import TankPack

        # Create the simulation engine
        self.engine = SimulationEngine(config=self.simulation_config, rng=self.rng)
        self.pack = pack or TankPack(self.simulation_config)

    def setup(self) -> None:
        """Setup the simulation.

        This initializes the environment, ecosystem, and creates initial entities.
        """
        self.engine.setup(self.pack)

    def update(self) -> None:
        """Update the simulation by one frame."""
        self.engine.update()

    def pause(self) -> None:
        """Pause the simulation."""
        self.engine.paused = True

    def resume(self) -> None:
        """Resume the simulation."""
        self.engine.paused = False

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        # Clear all entities and reset counters
        self.engine.entities_list.clear()
        self.engine.frame_count = 0
        self.engine.paused = False

        # Re-setup the simulation
        self.setup()

    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state.

        Returns:
            Dictionary with current frame, entities, and stats
        """
        return {
            "frame": self.engine.frame_count,
            "paused": self.engine.paused,
            "entities": self.engine.entities_list,
            "stats": self.engine.get_stats(),
        }

    def get_stats(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation stats
        """
        return self.engine.get_stats(include_distributions)

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive statistics to JSON file.

        Args:
            filename: Output JSON file path
        """
        self.engine.export_stats_json(filename)

    def run_headless(
        self, max_frames: int = 10000, stats_interval: int = 300, export_json: Optional[str] = None
    ) -> None:
        """Run simulation in headless mode.

        Args:
            max_frames: Maximum number of frames to simulate
            stats_interval: Print stats every N frames
            export_json: Optional filename to export JSON stats
        """
        self.engine.run_headless(
            max_frames=max_frames, stats_interval=stats_interval, export_json=export_json
        )

    # Expose commonly used properties
    @property
    def frame_count(self) -> int:
        """Current frame count."""
        return self.engine.frame_count

    @frame_count.setter
    def frame_count(self, value: int):
        """Set the frame count."""
        self.engine.frame_count = value

    @property
    def paused(self) -> bool:
        """Whether simulation is paused."""
        return self.engine.paused

    @paused.setter
    def paused(self, value: bool):
        """Set pause state."""
        self.engine.paused = value

    @property
    def entities_list(self) -> List[Any]:
        """Get list of all entities."""
        return self.engine.entities_list

    @property
    def ecosystem(self):
        """Get ecosystem manager."""
        return self.engine.ecosystem

    @property
    def environment(self):
        """Get environment."""
        return self.engine.environment

    def get_recent_poker_events(self, max_age_frames: int = 180) -> List[Dict[str, Any]]:
        """Get recent poker events.

        Args:
            max_age_frames: Maximum age of events to return

        Returns:
            List of recent poker event dictionaries
        """
        return self.engine.get_recent_poker_events(max_age_frames)

    def add_entity(self, entity) -> None:
        """Add an entity to the simulation.

        Args:
            entity: Entity to add
        """
        self.engine.add_entity(entity)

    def remove_entity(self, entity) -> None:
        """Remove an entity from the simulation.

        Args:
            entity: Entity to remove
        """
        self.engine.remove_entity(entity)
