"""PlantNectar entity - reproductive food produced by plants.

PlantNectar is a :class:`~core.entities.resources.Food` (not a Plant): it is a
consumable that stays attached to its source plant. When a fish consumes it,
the fish triggers plant reproduction at a nearby root spot using the carried
parent genome. It lives in its own module so ``plant.py`` stays focused on the
Plant entity itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.config.plants import PLANT_NECTAR_ENERGY
from core.entities.resources import Food

if TYPE_CHECKING:
    from core.entities.base import EntityUpdateResult
    from core.entities.plant import Plant
    from core.genetics import PlantGenome
    from core.world import World


class PlantNectar(Food):
    """Nectar produced by plants.

    When consumed by fish, triggers plant reproduction at a nearby root spot.

    Attributes:
        source_plant: The plant that produced this nectar
        parent_genome: Copy of parent plant's genome for inheritance
        energy: Energy value when consumed
    """

    NECTAR_ENERGY = PLANT_NECTAR_ENERGY
    NECTAR_SIZE = 15

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        source_plant: Plant,
        relative_y_offset_pct: float = 0.20,
        floral_visuals: dict | None = None,
    ) -> None:
        """Initialize plant nectar.

        Args:
            environment: The environment
            x: X position
            y: Y position
            source_plant: The plant that produced this
            relative_y_offset_pct: Vertical offset from top as percentage of height (0.0-1.0)
            floral_visuals: Dictionary of visual properties (hue, saturation, type, etc.)
        """
        super().__init__(
            environment,
            x,
            y,
            source_plant=source_plant,
            food_type="nectar",
            allow_stationary_types=True,
        )

        self.source_plant = source_plant
        self.relative_y_offset_pct = relative_y_offset_pct
        self.floral_visuals = floral_visuals or {}
        self.parent_genome = source_plant.genome  # Reference to parent genome
        # Override energy from Food init (which uses default 90.0 from constants)
        self.energy = self.NECTAR_ENERGY
        self.max_energy = self.NECTAR_ENERGY

        self.set_size(self.NECTAR_SIZE, self.NECTAR_SIZE)

    @property
    def snapshot_type(self) -> str:
        """Return entity type for snapshot serialization.

        Used by identity providers to determine type-specific ID offsets
        without requiring isinstance checks.
        """
        return "plant_nectar"

    def update_position(self) -> None:
        """Nectar stays attached to its source plant in the upper portion."""
        if self.source_plant is not None and not self.source_plant.is_dead():
            # relative_y_offset_pct is how far UP from base (0.65-0.95 = upper portion)
            # Calculate position from base going up
            base_y = self.source_plant.pos.y + self.source_plant.height
            self.pos.x = self.source_plant.pos.x + self.source_plant.width / 2 - self.width / 2
            self.pos.y = (
                base_y - self.source_plant.height * self.relative_y_offset_pct - self.height / 2
            )

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: float | None = None
    ) -> EntityUpdateResult:
        """Update nectar state."""
        from core.entities.base import EntityUpdateResult

        super().update(frame_count, time_modifier, time_of_day)
        self.update_position()
        if self.environment:
            self.environment.update_agent_position(self)
        return EntityUpdateResult()

    def get_energy_value(self) -> float:
        """Get energy provided when consumed.

        Returns:
            Energy value
        """
        return self.energy

    def is_consumed(self) -> bool:
        """Check if nectar has been consumed.

        Returns:
            True if fully consumed
        """
        return self.energy <= 0

    def take_bite(self, bite_size: float) -> float:
        """Take a bite from the nectar.

        Overrides Food.take_bite to trigger reproduction logic when fully consumed.
        """
        consumed = super().take_bite(bite_size)

        # If fully consumed (or close enough), trigger reproduction logic
        if self.energy <= 0.1:
            self.energy = 0
            # Logic for reproduction is handled by the consumer (Fish)
            pass

        return consumed

    def consume(self) -> PlantGenome:
        """Consume this nectar.

        Returns:
            The parent genome for reproduction
        """
        self.energy = 0
        return self.parent_genome

    def to_state_dict(self) -> dict:
        """Serialize for frontend.

        Returns:
            State dictionary
        """
        result = {
            "type": "plant_nectar",
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "energy": self.energy,
            "source_plant_id": self.source_plant.plant_id if self.source_plant else None,
        }

        # Add visual properties
        if self.floral_visuals:
            result.update(self.floral_visuals)

        # Add source plant position for sway synchronization
        if self.source_plant:
            result["source_plant_x"] = self.source_plant.pos.x + self.source_plant.width / 2
            result["source_plant_y"] = self.source_plant.pos.y + self.source_plant.height
        return result
