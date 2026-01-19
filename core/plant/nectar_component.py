"""Nectar production component for plants.

This module provides the PlantNectarComponent class which handles nectar
production logic for plant reproduction.
"""

import logging
from typing import TYPE_CHECKING, Callable, Optional

from core.config.plants import (
    PLANT_NECTAR_COOLDOWN,
    PLANT_NECTAR_ENERGY,
)

if TYPE_CHECKING:
    from core.genetics import PlantGenome
    from core.world import World

logger = logging.getLogger(__name__)


class PlantNectarComponent:
    """Manages plant nectar production for reproduction.

    This component encapsulates nectar production logic, including:
    - Cooldown management
    - Energy threshold checks
    - Nectar spawn position calculation
    - Floral visual configuration

    Attributes:
        nectar_cooldown: Frames until can produce nectar again.
        nectar_produced: Count of nectar produced.
    """

    __slots__ = (
        "nectar_cooldown",
        "nectar_produced",
        "_get_energy_ratio",
        "_get_energy",
        "_get_genome",
        "_get_environment",
        "_get_plant_pos",
        "_get_plant_size",
        "_lose_energy",
    )

    def __init__(
        self,
        get_energy_ratio: Callable[[], float],
        get_energy: Callable[[], float],
        get_genome: Callable[[], "PlantGenome"],
        get_environment: Callable[[], "World"],
        get_plant_pos: Callable[[], tuple[float, float]],
        get_plant_size: Callable[[], tuple[float, float]],
        lose_energy: Callable[[float, str], float],
    ) -> None:
        """Initialize the nectar component.

        Args:
            get_energy_ratio: Callback to get current energy ratio.
            get_energy: Callback to get current energy.
            get_genome: Callback to get the plant's genome.
            get_environment: Callback to get the environment.
            get_plant_pos: Callback to get plant position (x, y).
            get_plant_size: Callback to get plant size (width, height).
            lose_energy: Callback to deduct energy with source tracking.
        """
        self.nectar_cooldown = PLANT_NECTAR_COOLDOWN // 2  # Start partially ready
        self.nectar_produced = 0
        self._get_energy_ratio = get_energy_ratio
        self._get_energy = get_energy
        self._get_genome = get_genome
        self._get_environment = get_environment
        self._get_plant_pos = get_plant_pos
        self._get_plant_size = get_plant_size
        self._lose_energy = lose_energy

    def update(self) -> None:
        """Update cooldown timer."""
        if self.nectar_cooldown > 0:
            self.nectar_cooldown -= 1

    def can_produce_nectar(self) -> bool:
        """Check if plant can produce nectar.

        Returns:
            True if all conditions for nectar production are met.
        """
        # Must be able to afford nectar
        if self._get_energy() < PLANT_NECTAR_ENERGY:
            return False

        # Must be at 90% energy to look "full grown" when producing
        if self._get_energy_ratio() < 0.90:
            return False

        # Check cooldown
        if self.nectar_cooldown > 0:
            return False

        return True

    def try_produce_nectar(self, time_of_day: Optional[float]) -> Optional["PlantNectar"]:
        """Try to produce nectar if conditions are met.

        Args:
            time_of_day: Normalized time of day.

        Returns:
            PlantNectar if produced, None otherwise.
        """
        if not self.can_produce_nectar():
            return None

        # Import here to avoid circular imports
        from core.entities.plant import PlantNectar

        # Produce nectar
        self.nectar_cooldown = PLANT_NECTAR_COOLDOWN
        self.nectar_produced += 1
        self._lose_energy(PLANT_NECTAR_ENERGY, "nectar")

        # Calculate spawn position
        nectar_x, nectar_y, relative_y_offset_pct = self._calculate_nectar_position()

        # Get floral visuals
        floral_visuals = self._get_floral_visuals()

        env = self._get_environment()
        genome = self._get_genome()

        # Create nectar - we need a reference to the Plant, not the component
        # This requires the caller to pass the plant instance
        # For now, return the data needed to create nectar externally
        return _NectarCreationData(
            environment=env,
            x=nectar_x,
            y=nectar_y,
            relative_y_offset_pct=relative_y_offset_pct,
            floral_visuals=floral_visuals,
            parent_genome=genome,
        )

    def _calculate_nectar_position(self) -> tuple[float, float, float]:
        """Calculate nectar spawn position.

        Returns:
            Tuple of (x, y, relative_y_offset_pct).
        """
        pos_x, pos_y = self._get_plant_pos()
        width, height = self._get_plant_size()

        env = self._get_environment()
        rng = getattr(env, "rng", None)
        if rng is None:
            raise RuntimeError("environment.rng is required for deterministic nectar production")

        # Random position in top 15% of the visual tree
        top_offset_pct = rng.uniform(0.02, 0.15)

        nectar_x = pos_x + width / 2
        nectar_y = pos_y + height * top_offset_pct

        # Store as distance from base for update_position compatibility
        base_y = pos_y + height
        relative_y_offset_pct = (base_y - nectar_y) / height

        return nectar_x, nectar_y, relative_y_offset_pct

    def _get_floral_visuals(self) -> dict:
        """Get floral visual configuration based on strategy type.

        Returns:
            Dictionary of visual properties.
        """
        genome = self._get_genome()
        floral_visuals = {}

        if genome.strategy_type:
            try:
                from core.plants.plant_strategy_types import (
                    PlantStrategyType,
                    get_strategy_visual_config,
                )

                strategy_type = PlantStrategyType(genome.strategy_type)
                config = get_strategy_visual_config(strategy_type)

                # Calculate average hue from range for consistent look
                hue = (config.color_hue_range[0] + config.color_hue_range[1]) / 2
                sat = (config.color_saturation_range[0] + config.color_saturation_range[1]) / 2

                floral_visuals = {
                    "floral_type": config.floral_type,
                    "floral_petals": config.floral_petals,
                    "floral_layers": config.floral_layers,
                    "floral_spin": config.floral_spin,
                    "floral_hue": hue,
                    "floral_saturation": sat,
                }
            except Exception:
                pass

        # If no strategy specific visuals, use genome colors
        if not floral_visuals:
            floral_visuals = {
                "floral_type": "vortex",  # Default
                "floral_hue": genome.color_hue,
                "floral_saturation": genome.color_saturation,
                "floral_petals": 5,
                "floral_layers": 3,
                "floral_spin": 1.0,
            }

        return floral_visuals


class _NectarCreationData:
    """Data class for nectar creation (internal use).

    This is returned by try_produce_nectar so the Plant class can
    create the actual PlantNectar with a reference to itself.
    """

    __slots__ = (
        "environment",
        "x",
        "y",
        "relative_y_offset_pct",
        "floral_visuals",
        "parent_genome",
    )

    def __init__(
        self,
        environment,
        x: float,
        y: float,
        relative_y_offset_pct: float,
        floral_visuals: dict,
        parent_genome,
    ):
        self.environment = environment
        self.x = x
        self.y = y
        self.relative_y_offset_pct = relative_y_offset_pct
        self.floral_visuals = floral_visuals
        self.parent_genome = parent_genome
