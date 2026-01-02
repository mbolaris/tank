"""Feeding component for agent food consumption.

This component manages an agent's food consumption mechanics,
bite size calculations, and nutrition tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.entities.resources import Food


class FeedingComponent:
    """Food consumption and nutrition tracking for agents.

    This component encapsulates:
    - Bite size calculations based on agent size
    - Food consumption logic and partial eating
    - Nutrition event tracking

    The component is stateless, making it easy to compose into different agent types.
    """

    # Default bite size multiplier
    BITE_SIZE_MULTIPLIER: float = 20.0

    def __init__(self, bite_size_multiplier: float = 20.0) -> None:
        """Initialize feeding component.

        Args:
            bite_size_multiplier: Base multiplier for bite size calculation
        """
        self._bite_size_multiplier = bite_size_multiplier

    def calculate_bite_size(self, size: float) -> float:
        """Calculate how much food can be consumed in one bite.

        Args:
            size: Agent size multiplier (1.0 = normal adult size)

        Returns:
            Maximum amount of food that can be consumed in one bite
        """
        return self._bite_size_multiplier * size

    def calculate_effective_bite(
        self,
        size: float,
        current_energy: float,
        max_energy: float,
    ) -> float:
        """Calculate effective bite size considering capacity.

        Limits bite size to what the agent can actually hold.

        Args:
            size: Agent size multiplier
            current_energy: Current energy level
            max_energy: Maximum energy capacity

        Returns:
            Amount of food that can be consumed without waste
        """
        bite_size = self.calculate_bite_size(size)
        available_capacity = max_energy - current_energy
        return min(bite_size, available_capacity)

    def can_eat(self, current_energy: float, max_energy: float, threshold: float = 0.95) -> bool:
        """Check if agent has capacity to eat more.

        Args:
            current_energy: Current energy level
            max_energy: Maximum energy capacity
            threshold: Ratio above which agent is considered full

        Returns:
            True if agent can consume more food
        """
        if max_energy <= 0:
            return False
        return (current_energy / max_energy) < threshold

    def consume_food(
        self,
        food: Food,
        bite_size: float,
    ) -> float:
        """Take a bite from food and return potential energy gain.

        Args:
            food: The food entity to consume from
            bite_size: Maximum amount to consume

        Returns:
            Amount of energy potentially gained from this bite
        """
        return food.take_bite(bite_size)

    def get_food_type(self, food: Any) -> str:
        """Determine the type of food for tracking purposes.

        Args:
            food: The food entity

        Returns:
            Type string: "nectar", "live_food", or "falling_food"
        """
        # Import locally to avoid circular dependencies
        from core.entities.plant import PlantNectar
        from core.entities.resources import LiveFood

        if isinstance(food, PlantNectar):
            return "nectar"
        elif isinstance(food, LiveFood):
            return "live_food"
        else:
            return "falling_food"
