"""Visual/rendering component for plants.

This module provides the PlantVisualComponent class which handles
size calculations and rendering-related state for plants.
"""

from typing import TYPE_CHECKING, Any, Optional
from collections.abc import Callable

from core.config.plants import (
    PLANT_BASE_HEIGHT,
    PLANT_BASE_WIDTH,
    PLANT_MAX_SIZE,
    PLANT_MIN_SIZE,
    PLANT_NECTAR_ENERGY,
)

if TYPE_CHECKING:
    from core.genetics import PlantGenome


class PlantVisualComponent:
    """Manages plant visual state and size calculations.

    This component encapsulates visual/rendering logic for a plant, including:
    - Size multiplier based on energy
    - L-system iteration count for fractal detail
    - State serialization for frontend

    Attributes:
        _cached_iterations: Cached iteration count to prevent flickering.
    """

    __slots__ = (
        "_cached_iterations",
        "_get_energy",
        "_get_genome",
        "_get_max_energy",
        "_get_nectar_cooldown",
    )

    def __init__(
        self,
        get_energy: Callable[[], float],
        get_max_energy: Callable[[], float],
        get_genome: Callable[[], "PlantGenome"],
        get_nectar_cooldown: Callable[[], int],
    ) -> None:
        """Initialize the visual component.

        Args:
            get_energy: Callback to get current energy.
            get_max_energy: Callback to get maximum energy.
            get_genome: Callback to get the plant's genome.
            get_nectar_cooldown: Callback to get nectar cooldown.
        """
        self._cached_iterations = 1
        self._get_energy = get_energy
        self._get_max_energy = get_max_energy
        self._get_genome = get_genome
        self._get_nectar_cooldown = get_nectar_cooldown

    def get_size_multiplier(self) -> float:
        """Get current size multiplier for rendering.

        Returns:
            Size multiplier (PLANT_MIN_SIZE to PLANT_MAX_SIZE).
        """
        energy_ratio = self._get_energy() / self._get_max_energy()
        return PLANT_MIN_SIZE + ((PLANT_MAX_SIZE - PLANT_MIN_SIZE) * energy_ratio)

    def calculate_size(self) -> tuple[float, float]:
        """Calculate the plant's width and height based on energy.

        Returns:
            Tuple of (width, height).
        """
        size_multiplier = self.get_size_multiplier()
        return (
            PLANT_BASE_WIDTH * size_multiplier,
            PLANT_BASE_HEIGHT * size_multiplier,
        )

    def get_fractal_iterations(self) -> int:
        """Get number of L-system iterations based on size.

        Larger plants have more detailed fractals.
        Uses hysteresis to prevent flickering between iteration levels.

        Returns:
            Number of iterations (1-3).
        """
        size = self.get_size_multiplier()

        # Determine target iterations based on size
        target_iterations = 1
        if size >= 1.0:
            target_iterations = 3
        elif size >= 0.6:
            target_iterations = 2

        # Apply hysteresis
        if target_iterations > self._cached_iterations:
            # Upgrade requires being past the threshold to prevent rapid switching
            if (target_iterations == 2 and size > 0.65) or (target_iterations == 3 and size > 1.05):
                self._cached_iterations = target_iterations
        elif target_iterations < self._cached_iterations:
            # Downgrade is immediate to reflect energy loss
            self._cached_iterations = target_iterations

        return self._cached_iterations

    def is_nectar_ready(self) -> bool:
        """Check if plant is ready to produce nectar (for display).

        Returns:
            True if nectar can be produced.
        """
        energy = self._get_energy()
        max_energy = self._get_max_energy()
        nectar_cooldown = self._get_nectar_cooldown()

        return (
            nectar_cooldown == 0 and energy >= PLANT_NECTAR_ENERGY and energy / max_energy >= 0.90
        )

    def to_state_dict(
        self,
        plant_id: int,
        pos_x: float,
        pos_y: float,
        width: float,
        height: float,
        age: int,
        poker_effect_state: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Serialize plant state for frontend rendering.

        Args:
            plant_id: Plant's unique ID.
            pos_x: X position.
            pos_y: Y position.
            width: Current width.
            height: Current height.
            age: Plant age in frames.
            poker_effect_state: Current poker effect state.

        Returns:
            Dictionary with plant state.
        """
        return {
            "type": "plant",
            "id": plant_id,
            "x": pos_x,
            "y": pos_y,
            "width": width,
            "height": height,
            "energy": self._get_energy(),
            "max_energy": self._get_max_energy(),
            "size_multiplier": self.get_size_multiplier(),
            "iterations": self.get_fractal_iterations(),
            "genome": self._get_genome().to_dict(),
            "age": age,
            "nectar_ready": self.is_nectar_ready(),
            "poker_effect_state": poker_effect_state,
        }
