"""TankWorld: A clean wrapper around the fish tank simulation.

This module provides a TankWorld class that encapsulates the entire simulation,
including configuration and random number generation, making it easy to:
- Run deterministic simulations with seeded RNG
- Override configuration parameters
- Interface with both headless and web backends
"""

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.config.food import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_SPAWN_RATE,
)
from core.config.ecosystem import (
    CRITICAL_POPULATION_THRESHOLD,
    MAX_POPULATION,
)
from core.config.display import (
    FRAME_RATE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)

logger = logging.getLogger(__name__)


@dataclass
class TankWorldConfig:
    """Configuration for TankWorld simulation.

    All parameters have defaults from constants.py but can be overridden.
    """

    # Screen dimensions
    screen_width: int = SCREEN_WIDTH
    screen_height: int = SCREEN_HEIGHT

    # Simulation parameters
    frame_rate: int = FRAME_RATE
    max_population: int = MAX_POPULATION
    critical_population_threshold: int = CRITICAL_POPULATION_THRESHOLD

    # Food spawning
    auto_food_spawn_rate: int = AUTO_FOOD_SPAWN_RATE
    auto_food_enabled: bool = AUTO_FOOD_ENABLED

    # Headless mode
    headless: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "frame_rate": self.frame_rate,
            "max_population": self.max_population,
            "critical_population_threshold": self.critical_population_threshold,
            "auto_food_spawn_rate": self.auto_food_spawn_rate,
            "auto_food_enabled": self.auto_food_enabled,
            "headless": self.headless,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TankWorldConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TankWorld:
    """Main simulation wrapper that encapsulates all global state.

    This class wraps the entire simulation and provides a clean interface
    for both headless and web backends. All configuration and randomness
    is managed through this class.

    Attributes:
        config: Simulation configuration
        rng: Random number generator for deterministic behavior
        engine: The underlying simulation engine
    """

    def __init__(
        self,
        config: Optional[TankWorldConfig] = None,
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
    ):
        """Initialize TankWorld.

        Args:
            config: Simulation configuration (uses defaults if None)
            rng: Random number generator instance (creates new if None)
            seed: Random seed (only used if rng is None)
        """
        # Store configuration
        self.config = config if config is not None else TankWorldConfig()

        # Setup RNG
        if rng is not None:
            self.rng = rng
        elif seed is not None:
            self.rng = random.Random(seed)
            logger.info(f"TankWorld initialized with seed: {seed}")
        else:
            self.rng = random.Random()

        # Import here to avoid circular dependencies
        from core.simulation_engine import SimulationEngine

        # Create the simulation engine
        # For now, we pass headless flag to engine
        # Later we can refactor engine to use config directly
        self.engine = SimulationEngine(headless=self.config.headless, rng=self.rng)

    def setup(self) -> None:
        """Setup the simulation.

        This initializes the environment, ecosystem, and creates initial entities.
        """
        self.engine.setup()

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

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics.

        Returns:
            Dictionary with simulation stats
        """
        return self.engine.get_stats()

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
