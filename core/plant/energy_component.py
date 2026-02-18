"""Energy management component for plants.

This module provides the PlantEnergyComponent class which handles all energy-related
functionality for plants, including photosynthesis, compound growth, and overflow routing.
"""

import logging
from typing import TYPE_CHECKING, Optional
from collections.abc import Callable

from core.config.plants import (
    PLANT_DAWN_DUSK_MODIFIER,
    PLANT_DAY_MODIFIER,
    PLANT_ENERGY_GAIN_MULTIPLIER,
    PLANT_MIN_ENERGY_GAIN,
    PLANT_NIGHT_MODIFIER,
)

if TYPE_CHECKING:
    from core.genetics import PlantGenome
    from core.root_spots import RootSpot
    from core.world import World

logger = logging.getLogger(__name__)


class PlantEnergyComponent:
    """Manages plant energy collection, photosynthesis, and overflow routing.

    This component encapsulates all energy-related logic for a plant, including:
    - Passive energy collection (photosynthesis)
    - Compound growth based on current energy
    - Time-of-day modifiers for energy collection
    - Neighbor competition effects
    - Overflow energy routing to food drops

    Attributes:
        energy: Current energy level.
        max_energy: Maximum energy capacity.
    """

    __slots__ = ("_genome", "_get_environment", "_get_root_spot", "energy", "max_energy")

    def __init__(
        self,
        genome: "PlantGenome",
        initial_energy: float,
        max_energy: float,
        get_root_spot: Callable[[], Optional["RootSpot"]],
        get_environment: Callable[[], "World"],
    ) -> None:
        """Initialize the energy component.

        Args:
            genome: The plant's genetic information (for base_energy_rate).
            initial_energy: Starting energy level.
            max_energy: Maximum energy capacity.
            get_root_spot: Callback to get the plant's root spot.
            get_environment: Callback to get the environment.
        """
        self.energy = initial_energy
        self.max_energy = max_energy
        self._genome = genome
        self._get_root_spot = get_root_spot
        self._get_environment = get_environment

    def collect_energy(self, time_of_day: Optional[float] = None) -> float:
        """Collect passive energy through photosynthesis.

        Energy collection rate increases with current energy (compound growth).
        Photosynthesis rate varies with time of day:
        - Day (0.35-0.65): Full rate
        - Dawn/Dusk: 70% rate
        - Night: 30% rate

        Args:
            time_of_day: Normalized time of day (0.0-1.0), None defaults to full power.

        Returns:
            The amount of energy collected.
        """
        # Base rate from genome
        base_rate = self._genome.base_energy_rate

        # Compound growth factor with seedling boost
        energy_ratio = self.energy / self.max_energy if self.max_energy > 0 else 0

        if energy_ratio < 0.3:
            # Seedling boost: inverse relationship - smaller plants grow faster
            # At 0% energy: 3.0x, at 30% energy: 1.5x (smooth transition to standard)
            seedling_boost = 3.0 - (energy_ratio / 0.3) * 1.5
            growth_factor = seedling_boost
        else:
            # Standard compound growth for established plants (1.0-1.5x)
            growth_factor = 1.0 + (energy_ratio**0.5) * 0.5

        # Calculate photosynthesis modifier based on time of day
        photosynthesis_modifier = self._get_photosynthesis_modifier(time_of_day)

        energy_gain = base_rate * growth_factor * photosynthesis_modifier
        energy_gain *= PLANT_ENERGY_GAIN_MULTIPLIER

        # Reduce energy production if neighboring root slots are occupied
        reduction_factor = self._get_neighbor_reduction_factor()
        energy_gain *= reduction_factor

        # Cosmic Fern variants have a small energy collection bonus
        if getattr(self._genome, "type", "lsystem") == "cosmic_fern":
            energy_gain *= 1.1

        # Apply minimum energy gain floor
        min_energy_gain = self._get_min_energy_gain()
        energy_gain = max(energy_gain, min_energy_gain)

        self.energy = min(self.max_energy, self.energy + energy_gain)
        return energy_gain

    def _get_photosynthesis_modifier(self, time_of_day: Optional[float]) -> float:
        """Get the photosynthesis modifier based on time of day.

        Args:
            time_of_day: Normalized time of day (0.0-1.0).

        Returns:
            Modifier value (0.3-1.0).
        """
        if time_of_day is None:
            return PLANT_DAY_MODIFIER
        elif 0.35 <= time_of_day <= 0.65:
            # Full daylight (middle 30% of the day)
            return PLANT_DAY_MODIFIER
        elif 0.25 <= time_of_day < 0.35 or 0.65 < time_of_day <= 0.75:
            # Dawn (0.25-0.35) or Dusk (0.65-0.75)
            return PLANT_DAWN_DUSK_MODIFIER
        else:
            # Night (before 0.25 or after 0.75)
            return PLANT_NIGHT_MODIFIER

    def _get_neighbor_reduction_factor(self) -> float:
        """Calculate energy reduction due to neighboring plants.

        If both adjacent slots are full -> -50%, if one is full -> -25%.

        Returns:
            Reduction factor (0.5-1.0).
        """
        root_spot = self._get_root_spot()
        if root_spot is None:
            return 1.0

        manager = getattr(root_spot, "manager", None)
        if manager is None:
            return 1.0

        left_spot = manager.get_spot_by_id(root_spot.spot_id - 1)
        right_spot = manager.get_spot_by_id(root_spot.spot_id + 1)

        occupied_count = 0
        if left_spot is not None and left_spot.occupied:
            occupied_count += 1
        if right_spot is not None and right_spot.occupied:
            occupied_count += 1

        if occupied_count == 2:
            return 0.5
        elif occupied_count == 1:
            return 0.75
        return 1.0

    def _get_min_energy_gain(self) -> float:
        """Get the minimum energy gain from runtime config or default.

        Returns:
            Minimum energy gain per frame.
        """
        env = self._get_environment()
        config = getattr(env, "simulation_config", None)
        if config is not None:
            plant_config = getattr(config, "plant", None)
            if plant_config is not None:
                return getattr(plant_config, "plant_energy_input_rate", PLANT_MIN_ENERGY_GAIN)
        return PLANT_MIN_ENERGY_GAIN

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Adjust plant energy and return the actual delta.

        Positive amounts clamp to max_energy; overflow is routed.
        Negative amounts clamp at 0.

        Args:
            amount: Energy to add (positive) or remove (negative).
            source: Source of the energy change (for tracking).

        Returns:
            The actual delta applied to the plant's internal energy store.
        """
        if amount == 0:
            return 0.0

        before = self.energy

        if amount > 0:
            target = before + amount
            if target > self.max_energy:
                self.energy = self.max_energy
                # Note: Overflow routing handled by caller (Plant class)
            else:
                self.energy = target
        else:
            actual_loss = min(before, -amount)
            self.energy = before - actual_loss

        return self.energy - before

    def lose_energy(self, amount: float) -> float:
        """Lose energy (from poker loss or being eaten).

        Args:
            amount: Energy to lose.

        Returns:
            Actual amount lost.
        """
        actual_loss = min(self.energy, amount)
        self.energy -= actual_loss
        return actual_loss

    def gain_energy(self, amount: float) -> tuple[float, float]:
        """Gain energy and return both gained amount and overflow.

        Args:
            amount: Energy to gain.

        Returns:
            Tuple of (amount gained to internal store, overflow amount).
        """
        if amount <= 0:
            return 0.0, 0.0

        new_energy = self.energy + amount
        overflow = 0.0

        if new_energy > self.max_energy:
            overflow = new_energy - self.max_energy
            self.energy = self.max_energy
        else:
            self.energy = new_energy

        return amount - overflow, overflow

    def get_energy_ratio(self) -> float:
        """Get current energy as a ratio of maximum energy.

        Returns:
            Energy ratio between 0.0 (empty) and 1.0 (full).
        """
        return self.energy / self.max_energy if self.max_energy > 0 else 0.0
